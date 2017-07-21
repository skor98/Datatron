#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Вспомогательные методы для работы с кубами
"""

import requests
import logging
import json
import datetime
import numpy

from kb.kb_support_library import get_cube_caption
from kb.kb_support_library import get_caption_for_measure
from kb.kb_support_library import get_captions_for_dimensions
from kb.kb_support_library import get_representation_format
from kb.kb_support_library import get_default_member_for_dimension
from constants import ERROR_GENERAL, ERROR_NULL_DATA_FOR_SUCH_REQUEST
import logs_helper  # pylint: disable=unused-import


class CubeData:
    """Структура для данных передаваемых между узлами"""

    def __init__(self, user_request='', request_id=''):
        self.user_request = user_request
        self.request_id = request_id
        self.selected_cube = None
        self.cubes = []
        self.members = []
        self.year_member = None
        self.terr_member = None
        self.selected_measure = None
        self.measures = []
        self.mdx_query = ''
        self.score = {}


class FunctionExecutionError(Exception):
    """Ошибка при невозможности выполнении функции в узле"""
    pass


def send_request_to_server(mdx_query: str, cube: str):
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


def form_feedback(mdx_query: str, cube: str, user_request: str):
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


def format_numerical(number: float):
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


def format_cube_answer(cube_answer, response: requests):
    """
    Работа над ответом по кубу: получение данных, форматирование
    ответа, добавление обратной связи
    """

    if response.status_code == 200:
        try:
            response = response.json()
        except json.JSONDecodeError:
            cube_answer.status = False
            cube_answer.message = ERROR_GENERAL
            logging.exception(
                'Query_ID: {}\tMessage: Сервер вернул НЕ JSON'.format(cube_answer.request_id)
            )
            return
    else:
        cube_answer.status = False
        cube_answer.message = ERROR_GENERAL
        logging.exception(
            'Query_ID: {}\tMessage: Запрос к серверу вызвал ошибку {}'.format(
                cube_answer.request_id,
                response.status_code
            )
        )
        return

    # Обработка случая, когда MDX-запрос некорректный
    if not response.get('success', 1):
        cube_answer.status = False
        cube_answer.message = ERROR_GENERAL
        cube_answer.response = response
        logging.warning(
            "Query ID: {}\tError: Был создан MDX-запрос с некорректными параметрами".format(
                cube_answer.request_id
            ))
    # Обработка случая, когда данных нет
    elif response["cells"][0][0]["value"] is None:
        cube_answer.status = False
        cube_answer.message = ERROR_NULL_DATA_FOR_SUCH_REQUEST
        cube_answer.response = None
    # В остальных случаях
    else:
        # Результат по кубам может возвращаться в трех видах - рубли, процент, штуки
        value = float(response["cells"][0][0]["value"])

        # Получение из базы знаний (knowledge_base.db) формата для меры
        value_format = get_representation_format(cube_answer.mdx_query)

        # Добавление форматированного результата
        # Если формат для меры - 0, что означает число
        if not value_format:
            formatted_value = format_numerical(value)
            cube_answer.formatted_response = formatted_value
        # Если формат для меры - 1, что означает процент
        elif value_format == 1:
            # Перевод округление
            formatted_value = '{}%'.format(round(value, 5))
            cube_answer.formatted_response = formatted_value

        # Добавление к неформатированного результата
        # Если формат меры - 0, то просто целое число без знаков после запятой
        if not value_format:
            cube_answer.response = int(str(value).split('.')[0])
        # Если формат для меры - 1, то возращается полученный неокругленный результат
        elif value_format == 1:
            cube_answer.response = str(value)

        # добавление обратной связи в поле экземпляра класа
        cube_answer.message = ''

    # Создание фидбека в другом формате для удобного логирования
    feedback_verbal = cube_answer.feedback['verbal']
    verbal = '0. {}'.format(feedback_verbal['measure']) + ' '

    # pylint: disable=invalid-sequence-index
    verbal += ' '.join([str(idx + 1) + '. ' + val['member_caption']
                        for idx, val in enumerate(feedback_verbal['dims'])])

    logging.info(
        'Query_ID: {}\tMDX-запрос: {}\tСмысл: {}'.format(
            cube_answer.request_id,
            cube_answer.mdx_query,
            verbal
        ))


def manage_years(cube_data: CubeData):
    """Обработка лет из 1 и 2 цифр"""

    # проверка на наличие измерения года
    if cube_data.year_member:
        year = cube_data.year_member['cube_value']

        # обработка лет из 1 и 2 цифр
        if int(year) < 2006:
            if int(year) < 10:
                year = '0' + year
            cube_data.year_member = str(datetime.datetime.strptime(year, '%y').year)


def check_if_year_is_current(cube_data: CubeData):
    """Проверка на то, что год в данных является текущим годом"""

    given_year = int(cube_data.year_member['cube_value'])
    return bool(given_year == datetime.datetime.now().year)


def filter_measures_by_selected_cube(cube_data: CubeData):
    """Фильтрация мер по принадлежности к выбранному кубу"""

    if cube_data.measures:
        cube_data.measures = [
            item for item in cube_data.measures
            if item['cube'] == cube_data.selected_cube
            ]


def group_documents(solr_documents: list, user_request: str, request_id: str):
    """
    Разбитие найденных документы по переменным
    для различных типов вопросов
    """

    # Найденные документы по Минфин вопросам
    minfin_docs = []

    cube_data = CubeData(user_request, request_id)

    for doc in solr_documents:
        if doc['type'] == 'dim_member':
            cube_data.members.append(doc)
        elif doc['type'] == 'year_dim_member':
            cube_data.year_member = doc
        elif doc['type'] == 'terr_dim_member':
            cube_data.terr_member = doc
        elif doc['type'] == 'cube':
            cube_data.cubes.append(doc)
        elif doc['type'] == 'measure':
            cube_data.measures.append(doc)
        elif doc['type'] == 'minfin':
            minfin_docs.append(doc)

    return minfin_docs, cube_data


def score_cube_question(cube_data: CubeData):
    """Подсчет различных видов score для запроса по кубу"""

    def sum_scoring():
        """
        Базовый вариант подсчета score ответа:
        Сумма скора куба, среднего скора элементов измерений и меры
        """

        cube_score = cube_data.selected_cube['score']
        avg_member_score = numpy.mean([member['score'] for member in cube_data.members])
        measure_score = 0
        if cube_data.measures:
            measure_score = cube_data.measures['score']

        cube_data.score['sum'] = cube_score + avg_member_score + measure_score

    sum_scoring()


def process_with_members(cube_data: CubeData):
    """Обработка связанных значений"""

    # используемые измерения на основе выдачи Solr
    found_cube_dimensions = [elem['dimension'] for elem in cube_data.members]

    for member in cube_data.members:
        with_member_dim = member.get('connected_value.dimension_cube_value', None)

        if with_member_dim and with_member_dim not in found_cube_dimensions:
            cube_data.members.append(
                {
                    'dimension': with_member_dim,
                    'cube_value': member['connected_value.member_cube_value']
                }
            )


def process_default_members(cube_data: CubeData):
    """Обработка дефолтных значений"""

    # используемые измерения на основе выдачи Solr,
    # а также измерения связанных элементов
    used_cube_dimensions = [elem['dimension'] for elem in cube_data.members]

    # не использованные измерения
    unused_dimensions = (
        set(cube_data.selected_cube['dimensions']) - set(used_cube_dimensions)
    )

    for dim in unused_dimensions:
        default_value = get_default_member_for_dimension(cube_data.selected_cube['cube'], dim)
        if default_value:
            cube_data.members.append(
                {
                    'dimension': default_value['dimension_cube_value'],
                    'cube_value': default_value['member_cube_value']
                }
            )


def process_default_measures(cube_data: CubeData):
    """Обработка значения меры по умолчанию"""
    if cube_data.measures:
        cube_data.selected_measure = cube_data.measures[0]['cube_value']
    else:
        cube_data.selected_measure = cube_data.selected_cube['default_measure']


def create_mdx_query(cube_data: CubeData, type='basic'):
    """
    Формирование MDX-запроса различных видов, на основе найденных документов
    """

    def create_basic_mdx_query():
        """Базовый MDX-запрос"""

        # шаблон MDX-запроса
        mdx_template = 'SELECT {{[MEASURES].[{}]}} ON COLUMNS FROM [{}.DB] WHERE ({})'

        dim_tmp, dim_str_value = "[{}].[{}]", []

        for member in cube_data.members:
            dim_str_value.append(dim_tmp.format(
                member['dimension'],
                member['cube_value']
            ))

        cube_data.mdx_query = mdx_template.format(
            cube_data.selected_measure,
            cube_data.selected_cube['cube'],
            ','.join(dim_str_value)
        )

    # закладка под расширение типов MDX-запросов
    if type == 'basic':
        create_basic_mdx_query()


def delete_repetitions(cube_data_list: list):
    """
    Удаление из результата после прогона дерева
    повторяющихся комбинация
    """

    cube_data_repr = []

    for cube_data in list(cube_data_list):

        elements = [cube_data.selected_cube['cube']]

        for member in cube_data.members:
            elements.append(member['member_caption'])

        for measure in cube_data.measures:
            elements.append(measure['member_caption'])

        str_cube_data_elems = ''.join(elements)

        if str_cube_data_elems in cube_data_repr:
            cube_data_list.remove(cube_data)
        else:
            cube_data_repr.append(str_cube_data_elems)
