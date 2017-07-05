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
from kb.kb_support_library import get_connected_value_to_given_value
from kb.kb_support_library import get_default_cube_measure
from config import SETTINGS


class Solr:
    """
    Класс для взимодействия с поисковой системой Apache Solr
    """

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

        request = 'http://{}:8983/solr/{}/select'.format(
            SETTINGS.SOLR_HOST,
            self.core
        )
        params = {'q': user_request, 'rows': 20, 'wt': 'json', 'fl': '*,score'}
        docs = requests.get(request, params=params).json()
        return docs

    @staticmethod
    def _parse_solr_response(solr_docs, solr_result):
        """
        Разбивает найденные документы по переменным

        :param solr_docs: JSON-объект с найденными документами
        :param solr_result: объект класса DrSolrResult()
        :return:
        """

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
        final_dimension_list = []
        cube_above_territory_priority = False

        # Фильтрация по году
        if year:
            dimensions = [item for item in dimensions if 'Years' in get_cube_dimensions(item['cube'])]
            final_dimension_list.append(year)

        # Определение куба
        try:
            reference_cube = cubes[0]['cube']
            reference_cube_score = cubes[0]['score']
        except IndexError:
            # Если куб не найден (что очень мало вероятно)
            return solr_cube_result

        # Доопределение куба
        if dimensions:
            # Замена куба на другой, если score найденного куба меньше score верхнего документа
            if (reference_cube != dimensions[0]['cube']
                and reference_cube_score < dimensions[0]['score']
                ):
                reference_cube = dimensions[0][0]['cube']
                reference_cube_score = dimensions[0][0]['score']
            # Если найденный куб и куб верхнего документа совпадают,
            # а также score документа выше, то приоритет куба выше территории
            if (reference_cube == dimensions[0]['cube']
                and reference_cube_score < dimensions[0]['score']
                ):
                cube_above_territory_priority = True

        if cube_above_territory_priority:
            # Приоритет куба над территорией
            if territory:
                if 'Territories' not in get_cube_dimensions(reference_cube):
                    territory = None
        else:
            # Приоритет территории над кубом
            if territory:
                dimensions = [item for item in dimensions if 'Territories' in get_cube_dimensions(item['cube'])]
                final_dimension_list.append({
                    'name': territory['name'],
                    'cube': reference_cube,
                    'fvalue': territory[reference_cube],
                    'score': territory['score']
                })

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

        # если какие-то измерения (кроме территории, года) были найдены:
        if dimensions:
            # Это часть позволила улучшить алгоритм с 5/39 до 11/39
            # Берем все элементы из первой череды измерений для выбранного куба
            for dim in dimensions[0]:
                if dim['cube'] == reference_cube:
                    final_dimension_list.append(dim)

        if final_dimension_list:
            mdx_request = Solr._build_mdx_request(
                final_dimension_list,
                measures,
                reference_cube
            )
            print(mdx_request)
            solr_cube_result.mdx_query = mdx_request
            solr_cube_result.cube_score = reference_cube_score
            Solr._calculate_score_for_cube_questions(
                final_dimension_list,
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
    def _calculate_score_for_cube_questions(dimensions, measures, year, territory, solr_result):
        """Подсчет различных видов score для запроса по кубу"""
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

    @staticmethod
    def _build_mdx_request(dimensions, measures, cube):
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

        # список измерения для куба
        all_cube_dimensions = get_cube_dimensions(cube)

        dim_tmp, dim_str_value = "[{}].[{}]", []

        for doc in dimensions:
            # добавление значений измерений в строку
            dim_str_value.append(dim_tmp.format(doc['name'], doc['fvalue']))

            # удаление из списка измерений использованное
            all_cube_dimensions.remove(doc['name'])

            # обработка связанных значений
            connected_value = get_connected_value_to_given_value(doc['fvalue'])

            # Если у значения есть связанное значение
            if connected_value:
                dim_str_value.append(dim_tmp.format(
                    connected_value['dimension'],
                    connected_value['fvalue']))

                # удаление из списка измерений использованное
                all_cube_dimensions.remove(connected_value['dimension'])

        # обработка дефолтных значений для измерейни
        for ref_dim in all_cube_dimensions:
            default_value = get_default_value_for_dimension(cube, ref_dim)
            if default_value:
                dim_str_value.append(dim_tmp.format(
                    default_value['dimension'],
                    default_value['fvalue']))

        measure = get_default_cube_measure(cube)

        # Если Solr нашел какие-нибудь меры
        if measures:
            # Фильтрация мер по принадлежности к выбранному кубу
            measures = [item for item in measures if item['cube'] == cube]
            if measures:
                measure = measures[0]['formal']

        return mdx_template.format(measure, cube, ','.join(dim_str_value))


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
