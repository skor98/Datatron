#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import logging

import requests

from config import SETTINGS
from constants import ERROR_GENERAL, ERROR_NO_DOCS_FOUND, ERROR_NULL_DATA_FOR_SUCH_REQUEST
from kb.kb_support_library import get_cube_description
from kb.kb_support_library import get_full_value_for_measure
from kb.kb_support_library import get_full_values_for_dimensions
from kb.kb_support_library import get_representation_format
from solr import Solr
from text_preprocessing import TextPreprocessing


# Module, which is responsible for getting required from user data
class DataRetrieving:
    @staticmethod
    def get_data(user_request, request_id):
        """основной API метод для модуля

        :param user_request: запрос от пользователя
        :param request_id: идентификатор запроса
        :return: объект класса DrSolrResult()
        """

        # инстанс класса, производящего нормализацию слов
        text_preprocessor = TextPreprocessing(request_id)
        # нормализация запроса пользователя
        normalized_user_request = text_preprocessor.normalization(
            user_request,
            delete_question_words=False
        )

        # инстанс класса, ответственного за работу с Apache Solr
        solr = Solr(SETTINGS.SOLR_MAIN_CORE)

        # получение структурированных результатов поиска
        solr_result = solr.get_data(normalized_user_request)

        # Если хотя бы 1 документ найден:
        if solr_result.status:
            # Если документ по кубам найден
            if solr_result.answer.type == 'cube':
                # Запрос к серверу Кристы по API для получения числа
                # Обновление переменной solr_result_cube
                DataRetrieving._format_cube_answer(
                    solr_result.answer,
                    user_request,
                    request_id
                )

            # Если дополнительные ответы найдены
            if solr_result.more_answers:
                for answer in solr_result.more_answers:
                    if answer.type == 'cube':
                        answer.feedback = DataRetrieving._form_feedback(
                            answer.mdx_query,
                            answer.cube,
                            user_request
                        )
        else:
            solr_result.message = ERROR_NO_DOCS_FOUND
            logging_str = 'Документы не найдены Query_ID: {}\tSolr: {}'
            logging.info(logging_str.format(request_id, solr_result.error))

        return solr_result

    @staticmethod
    def _format_cube_answer(solr_cube_result, user_request, request_id):
        # Запрос отправка на серверы Кристы MDX-запроса по HTTP
        api_response = DataRetrieving._send_request_to_server(
            solr_cube_result.mdx_query,
            solr_cube_result.cube
        )
        api_response = api_response.text

        # Формирование читабельной обратной связи по результату
        solr_cube_result.feedback = DataRetrieving._form_feedback(
            solr_cube_result.mdx_query,
            solr_cube_result.cube,
            user_request
        )

        value = None

        # Обработка случая, когда подобные запросы блокируются администратором (в кафе, например)
        if 'Доступ закрыт!' in api_response:
            solr_cube_result.status = False
            solr_cube_result.message = ERROR_GENERAL
            solr_cube_result.response = api_response
            value = api_response
            logging.warning("Запрос {} не прошел. Запрещены POST-запросы".format(
                request_id
            ))
        # Обработка случая, когда что-то пошло не так, например,
        # в запросе указан неизвестный параметр
        elif '"success":false' in api_response:
            solr_cube_result.status = False
            solr_cube_result.message = ERROR_GENERAL
            solr_cube_result.response = api_response
            value = api_response
            logging.warning("Для запроса {} создался MDX-запрос с некорректными параметрами".format(
                request_id
            ))
        # Обработка случая, когда данных нет
        elif json.loads(api_response)["cells"][0][0]["value"] is None:
            solr_cube_result.status = False
            solr_cube_result.message = ERROR_NULL_DATA_FOR_SUCH_REQUEST
            solr_cube_result.response = None
        # В остальных случаях
        else:
            # Результат по кубам может возвращаться в трех видах - рубли, процент, штуки
            value = float(json.loads(api_response)["cells"][0][0]["value"])
            solr_cube_result.response = value

            # Получение из базы знаний (knowledge_base.dbs) формата для меры
            value_format = get_representation_format(solr_cube_result.mdx_query)

            # Добавление форматированного результата
            # Если формат для меры - 0, что означает число
            if not value_format:
                formatted_value = DataRetrieving._format_numerical(value)
                solr_cube_result.formatted_response = formatted_value
            # Если формат для меры - 1, что означает процент
            elif value_format == 1:
                # Перевод округление
                formatted_value = '{}%'.format(round(value, 5))
                solr_cube_result.formatted_response = formatted_value

            # Добавление к неформатированного результата
            # Если формат меры - 0, то просто целое число без знаков после запятой
            if not value_format:
                solr_cube_result.response = int(str(value).split('.')[0])
            # Если формат для меры - 1, то возращается полученный неокругленный результат
            elif value_format == 1:
                solr_cube_result.response = str(value)

            # добавление обратной связи в поле экземпляра класа
            solr_cube_result.message = ''

        # Создание фидбека в другом формате для удобного логирования
        feedback_verbal = solr_cube_result.feedback['verbal']
        verbal = '0. {}'.format(feedback_verbal['measure']) + ' '
        verbal += ' '.join([str(idx + 1) + '. ' + i['full_value']
                            for idx, i in enumerate(feedback_verbal['dims'])])

        logging_str = 'Query_ID: {}\tSolr: {}\tMDX-запрос: {}\tЧисло: {}'
        logging.info(logging_str.format(
            request_id,
            verbal,
            solr_cube_result.mdx_query,
            value
        ))

    @staticmethod
    def _send_request_to_server(mdx_query, cube):
        """Отправка запроса к серверу

        :param mdx_query: MDX-запрос
        :return: объект класса request.model.Response, название куба
        """

        # Подготовка POST-данных и запрос к серверу
        data_to_post = {'dataMartCode': cube, 'mdxQuery': mdx_query}
        api_response = requests.post(
            'http://conf.prod.fm.epbs.ru/mdxexpert/CellsetByMdx',
            data_to_post
        )

        return api_response

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
        full_verbal_dimensions_value = [get_full_values_for_dimensions(i['val']) for i in dims_vals]
        full_verbal_measure_value = get_full_value_for_measure(measure_value, cube)

        # фидбек в удобном виде для конвертации в JSON-объект
        feedback = {
            'formal': {
                'cube': cube,
                'measure': measure_value,
                'dims': dims_vals
            },
            'verbal': {
                'domain': get_cube_description(cube),
                'measure': full_verbal_measure_value,
                'dims': full_verbal_dimensions_value
            },
            'user_request': user_request
        }
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug("Получили фидбек {}".format(feedback))
        return feedback

    @staticmethod
    def _format_numerical(number):
        """Перевод числа в млн, млрд и трл вид. Например, 123 111 298 -> 123,1 млн

        :param number: число для форматирования
        :return: отфоратированное число в виде строки
        """

        str_num = str(number)

        # Если число через точку
        if '.' in str_num:
            str_num = str_num.split('.')[0]

        num_len = len(str_num)

        # Если число является отрицательным
        if '-' in str_num:
            num_len -= 1

        if num_len < 6:
            res = str_num
        elif 6 < num_len <= 9:
            res = '{},{} {}'.format(str_num[:-6], str_num[-6], 'млн')
        elif 9 < num_len <= 12:
            res = '{},{} {}'.format(str_num[:-9], str_num[-9], 'млрд')
        else:
            res = '{},{} {}'.format(str_num[:-12], str_num[-12], 'трлн')
        logging.debug("Сконвертировали {} в {}".format(number, res))
        return res
