from kb.kb_support_library import get_cube_dimensions, get_default_value_for_dimension, get_default_dimension
import json
import requests
import datetime
from config import SETTINGS


class Solr:
    def __init__(self, core):
        self.core = core

    def get_data(self, user_request):
        """API метод для класса Solr

        :param user_request: нормализованный запрос пользователя
        :return: объект класса DrSolrResult()
        """
        try:
            docs = self._send_request_to_solr(user_request)

            if docs['response']['numFound']:
                mdx_query = self._parse_solr_response(docs)
                return DrSolrResult(True, mdx_query=mdx_query)
            else:
                raise Exception('Документы не найдены')
        except Exception as e:
            print('Solr: ' + str(e))
            return DrSolrResult(error=str(e))

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
    def _parse_solr_response(solr_docs):
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
                year = int(doc['fvalue'][0])
                # managing two number years
                if year < 2007:
                    if year < 10:
                        year = '0' + str(year)
                    year = datetime.datetime.strptime(str(year), '%y').year
            elif doc['type'][0] == 'territory_dimension':
                territory = doc
            elif doc['type'][0] == 'cube':
                cubes.append(doc)
            elif doc['type'][0] == 'measure':
                measures.append(doc)
            elif doc['type'][0] == 'minfin':
                minfin_docs.append(doc)

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
        reference_cube = cubes[0]['cube'][0]
        # если какие-то измерения (кроме территории, года) были найдены:
        if dimensions:
            # TODO: доработать определение куба
            if reference_cube != dimensions[0][0]['cube'][0] and cubes[0]['score'] < dimensions[0][0]['score']:
                reference_cube = dimensions[0][0]['cube'][0]

            # Максимальная группа измерений от куба лучшего элемента
            # dimensions = [doc for doc in dimensions if doc['cube'][0] == reference_cube]

            if dimensions[0][0]['cube'][0] == reference_cube:
                test1_dimensions = [dimensions[0][0]]  # первое измерение из верхнего списка измерений

        mdx_request = Solr._build_mdx_request(test1_dimensions, measures, reference_cube, year, territory)
        print(mdx_request)

        return mdx_request

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
                dim_str.append(dim_tmp.format('YEARS', year))
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
    def get_minfin_docs(user_request):
        """Работа с документами для вопросов Минфина

        :param user_request: запрос со стороны пользователя к Минфин вопросам
        :return: объект класса DrSolrMinfinResult()
        """
        req_str = 'http://localhost:8983/solr/{}/select/?q={}&wt=json'
        solr_response = requests.get(req_str.format(SETTINGS.SOLR_MINFIN_CORE, user_request))
        docs = json.loads(solr_response.text)

        res = DrSolrMinfinResult()

        if docs['response']['numFound']:
            res.status = True
            best_document = docs['response']['docs'][0]
            res.question = best_document['question'][0]
            res.short_answer = best_document['short_answer'][0]
            try:
                res.full_answer = best_document['full_answer'][0]
            except KeyError:
                pass

            try:
                res.link_name = best_document['link_name'][0]
                res.link = best_document['link'][0]
            except KeyError:
                pass

            try:
                res.picture = best_document['picture'][0]
            except KeyError:
                pass

            try:
                res.document = best_document['document'][0]
            except KeyError:
                pass

        return res


class DrSolrResult:
    def __init__(self, status=False, id_query=0, mdx_query='', error=''):
        self.status = status
        self.id_query = id_query
        self.mdx_query = mdx_query
        self.error = error


class DrSolrMinfinResult:
    def __init__(self, status=False):
        self.status = status
        self.question = ''
        self.short_answer = ''
        self.full_answer = None
        self.link_name = None
        self.link = None
        self.picture = None
        self.document = None
