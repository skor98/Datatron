import requests
from constants import ERROR_IN_MDX_REQUEST, ERROR_NO_DOCS_FOUND, ERROR_NULL_DATA_FOR_SUCH_REQUEST
from kb.kb_support_library import get_full_values_for_dimensions, get_full_value_for_measure, get_representation_format
from text_preprocessing import TextPreprocessing
import json
import logging
from dr.solr import Solr
from dr.cntk import CNTK
import uuid
from config import SETTINGS


# Module, which is responsible for getting required from user data
class DataRetrieving:
    @staticmethod
    def get_data(user_request, request_id, formatted=True):
        """основной API метод для модуля

        :param user_request: запрос от пользователя
        :param request_id: идентификатор запроса
        :return: объект класса M2Result()
        """

        solr = Solr(SETTINGS.SOLR_MAIN_CORE)
        tp = TextPreprocessing(request_id)

        normalized_user_request = tp.normalization(user_request)

        solr_result = solr.get_data(normalized_user_request)
        if solr_result.status:
            if solr_result.cube_documents.status:
                DataRetrieving._format_cube_answer(solr_result.cube_documents, user_request, request_id, formatted)
        else:
            solr_result.message = ERROR_NO_DOCS_FOUND
            logging_str = 'ID-запроса: {}\tМодуль: {}\tОтвет Solr: {}'
            logging.warning(logging_str.format(request_id, __name__, solr_result.error))

        return solr_result

    @staticmethod
    def _format_cube_answer(solr_cube_result, user_request, request_id, formatted=True):
        api_response, cube = DataRetrieving._send_request_to_server(solr_cube_result.mdx_query)
        api_response = api_response.text
        feedback = DataRetrieving._form_feedback(solr_cube_result.mdx_query, cube, user_request)

        value = None

        # Обработка случая, когда MDX-запрос некорректен
        if 'Доступ закрыт!' in api_response:
            solr_cube_result.status = False
            solr_cube_result.message = "Доступ закрыт"
            solr_cube_result.response = api_response
            value = api_response
        elif '"success":false' in api_response:
            solr_cube_result.status = False
            solr_cube_result.message = ERROR_IN_MDX_REQUEST
            solr_cube_result.response = api_response
            value = api_response
        # Обработка случая, когда данных нет
        elif not json.loads(api_response)["cells"][0][0]["value"]:
            solr_cube_result.status = False
            solr_cube_result.message = ERROR_NULL_DATA_FOR_SUCH_REQUEST
            solr_cube_result.response = None
        # В остальных случаях
        else:
            # TODO: доработать форматирование для штук
            value = float(json.loads(api_response)["cells"][0][0]["value"])

            if formatted:
                value_format = get_representation_format(solr_cube_result.mdx_query)
                # Если формат для меры - 0, что означает число
                if not value_format:
                    formatted_value = DataRetrieving._format_numerical(value)
                    solr_cube_result.response = formatted_value
                # Если формат для меры - 1, что означает процент
                elif value_format == 1:
                    formatted_value = '{}%'.format(round(value*100, 3))
                    solr_cube_result.response = formatted_value
            else:
                solr_cube_result.response = int(str(value).split('.')[0])

            # Формирование фидбэка
            solr_cube_result.message = feedback

        logging_str = 'ID-запроса: {}\tМодуль: {}\tОтвет Solr: {}\tMDX-запрос: {}\tЧисло: {}'

        feedback_verbal = feedback['verbal']
        verbal = '0. {}'.format(feedback_verbal['measure']) + ' '
        verbal += ' '.join([str(idx + 1) + '. ' + i for idx, i in enumerate(feedback_verbal['dims'])])

        logging.info(logging_str.format(request_id, __name__, verbal, solr_cube_result.mdx_query, value))

    @staticmethod
    def get_minfin_data(user_request):
        """Дополнительный API метод для модуля для работы с Минфин-запросами.
        В дальнейшем будет убран, так как поиск всех документов должен
        происходить через единый интерфейс

        :param user_request: запрос к Минфин-документам от пользователя
        :return: объект класса DrSolrMinfinResult()
        """
        tp = TextPreprocessing(uuid.uuid4())
        return Solr.get_minfin_docs(tp.normalization(user_request))

    @staticmethod
    def _send_request_to_server(mdx_query):
        """Отправка запроса к серверу

        :param mdx_query: MDX-запрос
        :return: объект класса request.model.Response, название куба
        """

        # Парсинг строки MDX-запроса для выделения из нее названия куба
        query_by_elements = mdx_query.split(' ')
        from_element = query_by_elements[query_by_elements.index('FROM') + 1]
        cube = from_element[1:len(from_element) - 4]

        # Подготовка POST-данных и запрос к серверу
        d = {'dataMartCode': cube, 'mdxQuery': mdx_query}
        api_response = requests.post('http://conf.prod.fm.epbs.ru/mdxexpert/CellsetByMdx', d)

        return api_response, cube

    @staticmethod
    def _form_feedback(mdx_query, cube, user_request):
        """Формирование обратной связи

        :param mdx_query: MDX-запрос
        :param cube: название куба
        :param user_request: запрос пользователя
        :return: словарь
        """

        # Разбиваем MDX-запрос на две части
        left_part, right_part = mdx_query.split('(')

        # Вытаскиваем меру из левой части
        measure_value = left_part.split('}')[0].split('.')[1][1:-1]

        # Собираем название измерения и его значение из второй
        dims_vals = []
        for item in right_part[:-1].split(','):
            item = item.split('.')
            dims_vals.append({'dim': item[0][1:-1], 'val': item[1][1:-1]})

        # Полные вербальные отражения значений измерений и меры
        full_verbal_dimensions_value = get_full_values_for_dimensions([i['val'] for i in dims_vals])
        full_verbal_measure_value = get_full_value_for_measure(measure_value, cube)

        # фидбек в удобном виде для конвертации в JSON-объект
        feedback = {'formal': {'cube': cube, 'measure': measure_value, 'dims': dims_vals},
                    'verbal': {'measure': full_verbal_measure_value, 'dims': full_verbal_dimensions_value},
                    'user_request': user_request}

        return feedback

    @staticmethod
    def _format_numerical(number):
        """Перевод числа в млн, млрд и трл вид. Например, 123 123 123 -> 123 млн

        :param number: число для форматирования
        :return: отфоратированное число в виде строки
        """
        str_num = str(number)

        # Если число через точку
        if '.' in str_num:
            str_num = str_num.split('.')[0]
        num_len = len(str_num)

        if '-' in str_num:
            num_len -= 1

        if num_len < 6:
            return str_num
        elif 6 < num_len <= 9:
            return '{},{} {}'.format(str_num[:-6], str_num[-6], 'млн')
        elif 9 < num_len <= 12:
            return '{},{} {}'.format(str_num[:-9], str_num[-9], 'млрд')
        else:
            return '{},{} {}'.format(str_num[:-12], str_num[-12], 'трлн')