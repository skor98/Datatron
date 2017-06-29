from kb.kb_support_library import get_cube_dimensions, get_default_value_for_dimension, get_default_dimension
import json
import requests
import datetime
from config import SETTINGS
import numpy as np


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
        except Exception as e:
            print('Solr: ' + str(e))
            solr_result.error = str(e)
            return solr_result

    def _send_request_to_solr(self, user_request):
        """Метод для отправки запроса к Solr

        :param user_request: запрос пользователя
        :return: ответ от Solr в формате JSON
        """

        request = 'http://localhost:8983/solr/{}/select/?q={}&rows={}&wt=json&fl=*,score'
        json_response = requests.get(request.format(self.core, user_request, 20)).text
        docs = json.loads(json_response)
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
            if doc['type'][0] == 'dimension':
                dimensions.append(doc)
            elif doc['type'][0] == 'year_dimension':
                year_value = int(doc['fvalue'][0])
                # managing two number years
                if year_value < 2007:
                    if year_value < 10:
                        year_value = '0' + str(year)
                    year_value = datetime.datetime.strptime(str(year_value), '%y').year
                doc['fvalue'][0] = year_value
                year = doc
            elif doc['type'][0] == 'territory_dimension':
                territory = doc
            elif doc['type'][0] == 'cube':
                cubes.append(doc)
            elif doc['type'][0] == 'measure':
                measures.append(doc)
            elif doc['type'][0] == 'minfin':
                minfin_docs.append(doc)

        solr_result.cube_documents = Solr._process_cube_question(year, territory, dimensions, cubes, measures)
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
            dimensions = [item for item in dimensions if 'Years' in get_cube_dimensions(item['cube'][0])]

        if territory:
            dimensions = [item for item in dimensions if 'Territories' in get_cube_dimensions(item['cube'][0])]

        # Построение иерархического списка измерений
        tmp_dimensions, idx = [], 0
        while dimensions:
            tmp_dimensions.append([])
            for doc in list(dimensions):
                # TODO: реализовать для смотри также
                if '{}_{}'.format(doc['name'][0], doc['cube'][0]) in tmp_dimensions[idx]:
                    continue
                else:
                    tmp_dimensions[idx].append('{}_{}'.format(doc['name'][0], doc['cube'][0]))
                    tmp_dimensions[idx].append(doc)
                    dimensions.remove(doc)
            idx += 1

        dimensions = tmp_dimensions
        # Очистка от ненужных элементов
        dimensions = [list(filter(lambda elem: type(elem) is not str, level)) for level in dimensions]

        test1_dimensions = []
        try:
            reference_cube = cubes[0]['cube'][0]
            reference_cube_score = cubes[0]['score']
        except IndexError:
            return solr_cube_result

        # если какие-то измерения (кроме территории, года) были найдены:
        if dimensions:
            # TODO: доработать определение куба
            # Замена куба на другой, если score найденного меньше score верхнего документа
            if reference_cube != dimensions[0][0]['cube'][0] and cubes[0]['score'] < dimensions[0][0]['score']:
                reference_cube = dimensions[0][0]['cube'][0]
                reference_cube_score = dimensions[0][0]['score']

            # Максимальная группа измерений от куба лучшего элемента
            # dimensions = [doc for doc in dimensions if doc['cube'][0] == reference_cube]

            if dimensions[0][0]['cube'][0] == reference_cube:
                test1_dimensions = [dimensions[0][0]]  # первое измерение из верхнего списка измерений

            # Это часть позволила улучшить алгоритм с 5/39 до 11/39
            # Берем все элементы из первой череды измерений для выбранного куба
            try:
                for dim in dimensions[0][1:]:
                    if dim['cube'][0] == reference_cube:
                        test1_dimensions.append(dim)
            except Exception as e:
                print('{}: {}'.format(__name__, str(e)))

        if len(test1_dimensions):
            mdx_request = Solr._build_mdx_request(test1_dimensions, measures, reference_cube, year, territory)
            print(mdx_request)
            solr_cube_result.mdx_query = mdx_request
            solr_cube_result.cube_score = reference_cube_score
            Solr._calculate_score_for_cube_questions(test1_dimensions, measures, year, territory, solr_cube_result)
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
        solr_minfin_result.number = best_document['number'][0]
        solr_minfin_result.question = best_document['question'][0]
        solr_minfin_result.short_answer = best_document['short_answer'][0]
        try:
            solr_minfin_result.full_answer = best_document['full_answer'][0]
        except KeyError:
            pass

        try:
            if len(best_document['link_name']) > 1:
                solr_minfin_result.link_name = best_document['link_name']
                solr_minfin_result.link = best_document['link']
            else:
                solr_minfin_result.link_name = best_document['link_name'][0]
                solr_minfin_result.link = best_document['link'][0]

        except KeyError:
            pass

        try:
            if len(best_document['picture_caption']) > 1:
                solr_minfin_result.picture_caption = best_document['picture_caption']
                solr_minfin_result.picture = best_document['picture']
            else:
                solr_minfin_result.picture_caption = best_document['picture_caption'][0]
                solr_minfin_result.picture = best_document['picture'][0]

        except KeyError:
            pass

        try:
            if len(best_document['document']) > 1:
                solr_minfin_result.document_caption = best_document['document_caption']
                solr_minfin_result.document = best_document['document']
            else:
                solr_minfin_result.document_caption = best_document['document_caption'][0]
                solr_minfin_result.document = best_document['document'][0]
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

        dim_tmp, dim_str = "[{}].[{}]", []
        for doc in dimensions:
            dim_str.append(dim_tmp.format(doc['name'][0], doc['fvalue'][0]))

        reference_cube_dimensions = get_cube_dimensions(cube)

        # TODO: подправить на капс
        if 'Years' in reference_cube_dimensions:
            if year:
                dim_str.append(dim_tmp.format('YEARS', year['fvalue'][0]))
            else:
                dim_str.append(dim_tmp.format('YEARS', get_default_value_for_dimension(cube, 'Years')))

        # TODO: подправить на капс
        if 'Territories' in reference_cube_dimensions and territory:
            dim_str.append(dim_tmp.format('TERRITORIES', territory[cube][0]))
            dim_str.append(dim_tmp.format('BGLEVELS', '09-3'))
        elif 'Territories' in reference_cube_dimensions:
            dim_str.append(dim_tmp.format('BGLEVELS', get_default_value_for_dimension(cube, 'BGLevels')))

        measure = get_default_dimension(cube)
        if measures:
            measures = [item for item in measures if item['cube'][0] == cube]
            if measures:
                measure = measures[0]['formal'][0]

        return mdx_template.format(measure, cube, ','.join(dim_str))

    @staticmethod
    def _calculate_score_for_cube_questions(dimensions, measures, year, territory, solr_result):
        scores = []

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
