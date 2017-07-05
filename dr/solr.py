#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Взаимодействие с Solr
"""

import datetime
import json

import requests
import numpy as np

from kb.kb_support_library import get_cube_dimensions
from kb.kb_support_library import get_default_value_for_dimension
from kb.kb_support_library import get_default_dimension
from config import SETTINGS


class Solr:
    def __init__(self, core):
        self.core = core

    def get_data(self, user_request):
        """API метод для класса Solr

        :param user_request: нормализованный запрос пользователя
        :return: объект класса DrSolrResult()"""

        solr_result = DrSolrResult()

        try:
            docs = self._send_request_to_solr(user_request)

            if docs['response']['numFound']:
                Solr._parse_solr_response(docs, solr_result)
                solr_result.status = True
                return solr_result
            else:
                raise Exception('Datatron не нашел ответа на Ваш вопрос')
        except Exception as err:
            print('Solr: ' + str(err))
            solr_result.error = str(err)
            return solr_result

    def _send_request_to_solr(self, user_request):
        """Метод для отправки запроса к Solr

        :param user_request: запрос пользователя
        :return: ответ от Solr в формате JSON
        """

        request = 'http://{}:8983/solr/{}/select'.format(SETTINGS.SOLR_HOST, self.core)
        params = {'q': user_request, 'rows': 20, 'wt': 'json', 'fl': '*,score'}
        docs = requests.get(request, params=params).json()
        return docs

    @staticmethod
    def _parse_solr_response(solr_docs, solr_result):
        """Парсер набора документов

        Принимает на вход JSON-объект.
        Возвращает MDX"""

        minfin_docs = []
        cubes = []
        territory = None
        year = None
        dimensions = []
        measures = []

        solr_docs = solr_docs['response']['docs']

        for doc in solr_docs:
            if doc['type'] == 'dimension':
                dimensions.append(doc)
            elif doc['type'] == 'year_dimension':
                year_value = int(doc['fvalue'])
                # managing two number years
                if year_value < 2007:
                    if year_value < 10:
                        year_value = '0' + str(year_value)
                    year_value = datetime.datetime.strptime(str(year_value), '%y').year
                doc['fvalue'] = year_value
                year = doc
            elif doc['type'] == 'territory_dimension':
                territory = doc
            elif doc['type'] == 'cube':
                cubes.append(doc)
            elif doc['type'] == 'measure':
                measures.append(doc)
            elif doc['type'] == 'minfin':
                minfin_docs.append(doc)

        solr_result.cube_documents = Solr._process_cube_question(
            year,
            territory,
            dimensions,
            cubes,
            measures
        )
        if minfin_docs:
            solr_result.minfin_documents = Solr._process_minfin_question(minfin_docs)

        if solr_result.cube_documents.status:
            solr_result.docs_found += 1

        if solr_result.minfin_documents.status:
            solr_result.docs_found += 1

        return solr_result

    @staticmethod
    def _process_cube_question(year, territory, dimensions, cubes, measures):
        solr_cube_result = DrSolrCubeResult()

        if year:
            dimensions = [item for item in dimensions if 'Years' in get_cube_dimensions(item['cube'])]

        if territory:
            dimensions = [item for item in dimensions if 'Territories' in get_cube_dimensions(item['cube'])]

        # Построение иерархического списка измерений
        tmp_dimensions, idx = [], 0
        while dimensions:
            tmp_dimensions.append([])
            for doc in list(dimensions):
                # TODO: реализовать для смотри также
                if '{}_{}'.format(doc['name'], doc['cube']) in tmp_dimensions[idx]:
                    continue
                else:
                    tmp_dimensions[idx].append('{}_{}'.format(
                        doc['name'],
                        doc['cube']
                    ))
                    tmp_dimensions[idx].append(doc)
                    dimensions.remove(doc)
            idx += 1

        # Очистка от ненужных элементов
        dimensions = [list(filter(lambda elem: not isinstance(elem, str), level)) for level in tmp_dimensions]

        try:
            reference_cube = cubes[0]['cube']
            reference_cube_score = cubes[0]['score']
        except IndexError:
            return solr_cube_result

        final_dimensions = []
        # если какие-то измерения (кроме территории, года) были найдены:
        if dimensions:
            # TODO: доработать определение куба
            # Замена куба на другой, если score найденного меньше score верхнего документа
            if (
                            reference_cube != dimensions[0][0]['cube']
                    and cubes[0]['score'] < dimensions[0][0]['score']
            ):
                reference_cube = dimensions[0][0]['cube']
                reference_cube_score = dimensions[0][0]['score']

            # Максимальная группа измерений от куба лучшего элемента
            # dimensions = [doc for doc in dimensions if doc['cube'][0] == reference_cube]

            # Это часть позволила улучшить алгоритм с 5/39 до 11/39
            # Берем все элементы из первой череды измерений для выбранного куба
            for dim in dimensions[0]:
                if dim['cube'] == reference_cube:
                    final_dimensions.append(dim)

        if final_dimensions:
            mdx_request = Solr._build_mdx_request(
                final_dimensions,
                measures,
                reference_cube,
                year,
                territory
            )
            print(mdx_request)
            solr_cube_result.mdx_query = mdx_request
            solr_cube_result.cube_score = reference_cube_score
            Solr._calculate_score_for_cube_questions(
                final_dimensions,
                measures,
                year,
                territory,
                solr_cube_result
            )
            solr_cube_result.sum_score += solr_cube_result.cube_score
            solr_cube_result.status = True
        return solr_cube_result

    @staticmethod
    def _process_minfin_question(minfin_documents):
        """Работа с документами для вопросов Минфина

        :param minfin_documents: документы министерства финансов
        :return: объект класса DrSolrMinfinResult()
        """

        solr_minfin_result = DrSolrMinfinResult()
        best_document = minfin_documents[0]
        solr_minfin_result.score = best_document['score']
        solr_minfin_result.status = True
        solr_minfin_result.number = best_document['number']
        solr_minfin_result.question = best_document['question']
        solr_minfin_result.short_answer = best_document['short_answer']

        try:
            solr_minfin_result.full_answer = best_document['full_answer']
        except KeyError:
            pass

        try:
            solr_minfin_result.link_name = best_document['link_name']
            solr_minfin_result.link = best_document['link']
        except KeyError:
            pass

        try:
            solr_minfin_result.picture_caption = best_document['picture_caption']
            solr_minfin_result.picture = best_document['picture']
        except KeyError:
            pass

        try:
            solr_minfin_result.document_caption = best_document['document_caption']
            solr_minfin_result.document = best_document['document']
        except KeyError:
            pass

        return solr_minfin_result

    @staticmethod
    def _build_mdx_request(dimensions, measures, cube, year, territory):
        """Формирование MDX-запроса, на основе найденных документов

        :param dimensions: список документов измерений
        :param measures: список документов мер
        :param cube: имя правильного куба
        :param year: год
        :param territory: территория
        :return: MDX-запрос
        """

        # шаблон MDX-запроса
        mdx_template = 'SELECT {{[MEASURES].[{}]}} ON COLUMNS FROM [{}.DB] WHERE ({})'

        dim_tmp, dim_str_value = "[{}].[{}]", []

        for doc in dimensions:
            dim_str_value.append(dim_tmp.format(doc['name'], doc['fvalue']))

        reference_cube_dimensions = get_cube_dimensions(cube)

        # TODO: подправить на капс
        if 'Years' in reference_cube_dimensions:
            if year:
                year_fvalue = year['fvalue']
            else:
                year_fvalue = get_default_value_for_dimension(cube, 'Years')
            dim_str_value.append(dim_tmp.format('YEARS', year_fvalue))

        # TODO: подправить на капс
        if 'Territories' in reference_cube_dimensions and territory:
            dim_str_value.append(dim_tmp.format('TERRITORIES', territory[cube]))
            dim_str_value.append(dim_tmp.format('BGLEVELS', '09-3'))
        elif 'Territories' in reference_cube_dimensions:
            dim_str_value.append(dim_tmp.format(
                'BGLEVELS',
                get_default_value_for_dimension(cube, 'BGLevels')
            ))
        else:
            pass  # ToDo: тут должно что-то быть или нет?

        measure = get_default_dimension(cube)
        if measures:
            measures = [item for item in measures if item['cube'] == cube]
            if measures:
                measure = measures[0]['formal']

        return mdx_template.format(measure, cube, ','.join(dim_str_value))

    @staticmethod
    def _update_connected_values():
        pass

    @staticmethod
    def _calculate_score_for_cube_questions(dimensions, measures, year, territory, solr_result):
        scores = []

        # ToDo: Проверка, что ['score'] существует и к нему можно обратиться (2!)
        for dim in dimensions:
            scores.append(dim['score'])

        for measure in measures:
            scores.append(measure['score'])

        if year:
            scores.append(year['score'])

        if territory:
            scores.append(territory['score'])

        solr_result.avg_score = np.mean(scores)
        solr_result.min_score = min(scores)
        solr_result.max_score = max(scores)
        solr_result.sum_score = sum(scores)


class DrSolrCubeResult:
    def __init__(self):
        self.status = False
        self.type = 'cube'
        self.cube_score = 0
        self.avg_score = 0
        self.max_score = 0
        self.min_score = 0
        self.sum_score = 0
        self.mdx_query = None
        self.response = None
        self.message = None


class DrSolrMinfinResult:
    def __init__(self):
        self.status = False
        self.type = 'minfin'
        self.score = 0
        self.number = 0
        self.question = ''
        self.short_answer = ''
        self.full_answer = None
        self.link_name = None
        self.link = None
        self.picture_caption = None
        self.picture = None
        self.document_caption = None
        self.document = None
        self.message = None


class DrSolrResult:
    def __init__(self):
        self.status = False
        self.message = ''
        self.error = ''
        self.docs_found = 0
        self.cube_documents = DrSolrCubeResult()
        self.minfin_documents = DrSolrMinfinResult()

    def toJSON(self):
        return json.dumps(self, default=lambda obj: obj.__dict__, sort_keys=True, indent=4)
