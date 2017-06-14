from kb.kb_support_library import get_cube_dimensions, check_dimension_value_in_cube, get_default_dimension
import re
import json
import requests
import datetime
from config import SETTINGS


class Solr:
    def __init__(self, core):
        self.core = core

    def get_data(self, user_request):
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
        """Метод для работы с Solr

        Принимает на вход обработанный запрос пользователя и множественны/единичный ожидаемый ответ
        Возвращает документ (так как rows=1) в виде JSON-объекта"""

        request = 'http://localhost:8983/solr/{}/select/?q={}&rows={}&wt=json&fl=*,score'
        json_response = requests.get(request.format(self.core, user_request, 20)).text
        docs = json.loads(json_response)
        return docs

    @staticmethod
    def _parse_solr_response(solr_docs):
        """Парсер набора документов

        Принимает на вход JSON-объект.
        Возвращает MDX"""
        mdx_template = 'SELECT {{[MEASURES].[{}]}} ON COLUMNS FROM [{}.DB] WHERE ({})'
        cube_by_search = []
        territory = None
        year = None
        dim_list = []
        measure_list = []

        solr_docs = solr_docs['response']['docs']

        for doc in solr_docs:
            if doc['type'][0] == 'dimension':
                if '{}_{}'.format(doc['name'][0], doc['cube'][0]) in dim_list:
                    continue
                else:
                    dim_list.append('{}_{}'.format(doc['name'][0], doc['cube'][0]))
                    dim_list.append(doc)
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
                cube_by_search.append(doc['cube'][0])
            elif doc['type'][0] == 'measure':
                measure_list.append(doc)

        # Очистка от ненужных элементов
        dim_list = list(filter(lambda elem: type(elem) is not str, dim_list))

        if year:
            dim_list = [item for item in dim_list if 'Years' in get_cube_dimensions(item['cube'][0])]

        if territory:
            dim_list = [item for item in dim_list if 'Territories' in get_cube_dimensions(item['cube'][0])]
        # TODO: доработать определение куба
        reference_cube = dim_list[0]['cube'][0]

        # Максимальная группа измерений от куба лучшего элемента
        dim_list = [doc for doc in dim_list if doc['cube'][0] == reference_cube]

        dim_tmp, dim_str = "[{}].[{}]", []
        for doc in dim_list:
            dim_str.append(dim_tmp.format(doc['name'][0], doc['fvalue'][0]))

        reference_cube_dimensions = get_cube_dimensions(reference_cube)

        # TODO: подправить на капс
        if 'Years' in reference_cube_dimensions:
            if year:
                dim_str.append(dim_tmp.format('YEARS', year))
            else:
                dim_str.append(dim_tmp.format('YEARS', datetime.datetime.now().year))

        # TODO: подправить на капс
        if 'Territories' in reference_cube_dimensions and territory:
            dim_str.append(dim_tmp.format('TERRITORIES', territory[reference_cube][0]))
            dim_str.append(dim_tmp.format('BGLEVELS', '09-3'))

        measure = get_default_dimension(reference_cube)
        if measure_list:
            measure_list = [item for item in measure_list if item['cube'][0] == reference_cube]
            if measure_list:
                measure = measure_list[0]['formal'][0]

        mdx_filled_template = mdx_template.format(measure, reference_cube, ','.join(dim_str))
        return mdx_filled_template

    @staticmethod
    def get_minfin_docs(user_request):
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
