#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Вспомогательные методы для работы с кубами
"""

import requests
import logging
import json

from kb.kb_support_library import get_cube_caption
from kb.kb_support_library import get_caption_for_measure
from kb.kb_support_library import get_captions_for_dimensions
from kb.kb_support_library import get_representation_format
from constants import ERROR_GENERAL, ERROR_NULL_DATA_FOR_SUCH_REQUEST
import logs_helper  # pylint: disable=unused-import


def _send_request_to_server(mdx_query: str, cube: str):
    """
    Отправка запроса к серверу Кристы для получения
    ответа по MDX-запросу
    """

    # Подготовка POST-данных и запрос к серверу
    data_to_post = {'dataMartCode': cube, 'mdxQuery': mdx_query}
    api_response = requests.post(
        'http://conf.prod.fm.epbs.ru/mdxexpert/CellsetByMdx',
        data_to_post
    )

    return api_response


def _form_feedback(mdx_query: str, cube: str, user_request: str):
    """
    Формирование обратной связи по запросу
    для экспертной и обычной обратной связи
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
    full_verbal_dimensions_value = [get_captions_for_dimensions(i['val']) for i in dims_vals]
    full_verbal_measure_value = get_caption_for_measure(measure_value, cube)

    # фидбек в удобном виде для конвертации в JSON-объект
    feedback = {
        'formal': {
            'cube': cube,
            'measure': measure_value,
            'dims': dims_vals
        },
        'verbal': {
            'domain': get_cube_caption(cube),
            'measure': full_verbal_measure_value,
            'dims': full_verbal_dimensions_value
        },
        'user_request': user_request
    }
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        logging.debug("Получили фидбек {}".format(feedback))
    return feedback


def _format_numerical(number: float):
    """
    Перевод числа в млн, млрд и трл вид.
    Например, 123 111 298 -> 123,1 млн.
    """

    str_num = str(number)

    # Если число через точку, что должно
    # выполняться всегда для рублевых мер
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


@staticmethod
def _format_cube_answer(solr_cube_result, user_request, request_id):
    """
    Работа над ответом по кубу: получение данных, форматирование
    ответа, добавление обратной связи
    """

    # TODO: рефакторинг

    # Запрос отправка на серверы Кристы MDX-запроса по HTTP
    api_response = _send_request_to_server(
        solr_cube_result.mdx_query,
        solr_cube_result.cube
    )
    api_response = api_response.text

    # Формирование читабельной обратной связи по результату
    solr_cube_result.feedback = _form_feedback(
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
            formatted_value = _format_numerical(value)
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

    # pylint: disable=invalid-sequence-index
    verbal += ' '.join([str(idx + 1) + '. ' + val['full_value']
                        for idx, val in enumerate(feedback_verbal['dims'])])

    logging_str = 'Query_ID: {}\tSolr: {}\tMDX-запрос: {}\tЧисло: {}'
    logging.info(logging_str.format(
        request_id,
        verbal,
        solr_cube_result.mdx_query,
        value
    ))
