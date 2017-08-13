#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Вспомогательные методы для работы с кубами
"""

import logging
import json
import datetime
import requests
import numpy

from kb.kb_support_library import get_cube_caption
from kb.kb_support_library import get_caption_for_measure
from kb.kb_support_library import get_captions_for_dimensions
from kb.kb_support_library import get_representation_format
from kb.kb_support_library import get_default_member_for_dimension

from core.ling_parser import Phrase

from constants import ERROR_GENERAL, ERROR_NULL_DATA_FOR_SUCH_REQUEST
from constants import CUBE_FEEDBACK_MASKS

from model_manager import MODEL_CONFIG
import logs_helper  # pylint: disable=unused-import


class CubeData:
    """Структура для данных передаваемых между узлами"""

    def __init__(self, user_request='', request_id=''):
        self.user_request = user_request
        self.request_id = request_id
        self.tree_path = None
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

    # TODO: костыль на тот случай пока сервер отвечает через раз
    if api_response.status_code != 200:
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

    feedback['pretty_feedback'] = get_pretty_feedback(
        cube,
        feedback['verbal']
    )

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

    if num_len <= 6:
        res = str_num
    elif 6 < num_len <= 9:
        res = '{},{} {}'.format(str_num[:-6], str_num[-6], 'млн')
    elif 9 < num_len <= 12:
        res = '{},{} {}'.format(str_num[:-9], str_num[-9], 'млрд')
    else:
        res = '{},{} {}'.format(str_num[:-12], str_num[-12], 'трлн')

    res += ' руб.'
    logging.debug("Сконвертировали {} в {}".format(number, res))

    return res


def process_server_response(cube_answer, response: requests):
    """
    Работа над ответом по кубу: получение данных и обработка ответа
    от сервера Кристы
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
        logging.error(
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
        logging.error(
            "Query ID: {}\tError: Был создан MDX-запрос с некорректными параметрами {}".format(
                cube_answer.request_id,
                response.get('message', '')
            ))
        return
        # Обработка случая, когда данных нет
    elif response["cells"][0][0]["value"] is None:
        cube_answer.status = False
        cube_answer.message = ERROR_NULL_DATA_FOR_SUCH_REQUEST
        cube_answer.response = None
        return
        # В остальных случаях, то есть когда все хорошо
    else:
        return float(response["cells"][0][0]["value"])


def check_mdx_returns_data(response: requests):
    """
    Быстрая обработка ответа сервера, специально для отсеивания запросов,
    не возвращающих данные
    """

    if response.status_code == 200:
        try:
            response = response.json()
        except json.JSONDecodeError:
            return
    else:
        return

    # Обработка случая, когда MDX-запрос некорректный
    if not response.get('success', 1):
        return
    # Обработка случая, когда данных нет
    elif response["cells"][0][0]["value"] is None:
        return
    # В остальных случаях, то есть когда все хорошо
    else:
        return True


def process_cube_answer(cube_answer, value):
    """
    Доформирование ответа по кубам: форматирование ответа
    """

    # Результат по кубам может возвращаться в трех видах - рубли, процент, штуки
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
    verbal = '1. {}'.format(feedback_verbal['measure']) + ' '

    # pylint: disable=invalid-sequence-index
    verbal += ' '.join([str(idx + 2) + '. ' + val['member_caption']
                        for idx, val in enumerate(feedback_verbal['dims'])])

    logging.info(
        'Query_ID: {}\tMessage: {}'.format(
            cube_answer.request_id,
            "Выделенные параметры - " + verbal
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
            year = str(datetime.datetime.strptime(year, '%y').year)

            cube_data.year_member['cube_value'] = year


def check_if_year_is_current(cube_data: CubeData):
    """Проверка на то, что год в данных является текущим годом"""

    given_year = int(cube_data.year_member['cube_value'])
    return bool(given_year == datetime.datetime.now().year)


def select_measure_for_selected_cube(cube_data: CubeData):
    """Фильтрация мер по принадлежности к выбранному кубу"""

    if cube_data.measures:
        cube_data.measures = [
            item for item in cube_data.measures
            if item['cube'] == cube_data.selected_cube['cube']
            ]

        if cube_data.measures:
            # Чтобы снизить стремление алгоритма выбрать хоть какую-нибудь меру
            # для повышения скора
            if cube_data.measures[0]['score'] > MODEL_CONFIG["measure_matching_threshold"]:
                cube_data.selected_measure = cube_data.measures[0]


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
            # если лучшая территория еще не найдена
            if not cube_data.terr_member:
                cube_data.terr_member = doc
        elif doc['type'] == 'cube':
            cube_data.cubes.append(doc)
        elif doc['type'] == 'measure':
            cube_data.measures.append(doc)
        elif doc['type'] == 'minfin':
            minfin_docs.append(doc)

    logging.info(
        "Query_ID: {}\tMessage: Найдено {} cubes, "
        "{} dim_members, {} year_dim_member, {} terr_dim_member, {} measures".format(
            request_id,
            len(cube_data.cubes),
            len(cube_data.members),
            1 if cube_data.year_member else 0,
            1 if cube_data.terr_member else 0,
            len(cube_data.measures)
        ))

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
        if cube_data.selected_measure:
            measure_score = cube_data.selected_measure['score']

        cube_data.score['sum'] = (
            MODEL_CONFIG["cube_weight_in_sum_scoring_model"] * cube_score +
            avg_member_score +
            MODEL_CONFIG["measure_weight_in_sum_scoring_model"] * measure_score
        )

    # получение скоринг-модели
    score_model = MODEL_CONFIG["cube_answers_scoring_model"]

    if score_model == 'sum':
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


def process_with_member_for_territory(cube_data: CubeData):
    """Обработка связанных значений для ТЕРРИТОРИЙ"""

    if cube_data.terr_member:
        found_cube_dimensions = [elem['dimension'] for elem in cube_data.members]

        # если территория уже добавлена, как связанное значение
        if cube_data.terr_member['dimension'] in found_cube_dimensions:
            cube_data.terr_member = None
            return

        connected_dim = cube_data.terr_member.get(
            'connected_value.dimension_cube_value',
            None
        )

        if connected_dim:
            # если вместо связанного значения уже что-то используется другое
            if connected_dim not in found_cube_dimensions:
                # добавление связанного значения
                cube_data.members.append(
                    {
                        'dimension': connected_dim,
                        'cube_value': cube_data.terr_member['connected_value.member_cube_value']
                    }
                )


def process_default_members(cube_data: CubeData):
    """Обработка дефолтных значений"""

    # используемые измерения на основе выдачи Solr,
    # а также измерения связанных элементов
    used_cube_dimensions = [elem['dimension'] for elem in cube_data.members]

    if cube_data.terr_member:
        used_cube_dimensions.append(cube_data.terr_member['dimension'])

    if cube_data.year_member:
        used_cube_dimensions.append(cube_data.year_member['dimension'])

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
    if not cube_data.selected_measure:
        cube_data.selected_measure = {
            'cube_value': cube_data.selected_cube['default_measure']
        }


def create_mdx_query(cube_data: CubeData, mdx_type='basic'):
    """
    Формирование MDX-запроса различных видов, на основе найденных документов
    """

    def create_basic_mdx_query():
        """Базовый MDX-запрос"""

        # шаблон MDX-запроса
        mdx_template = 'SELECT {{[MEASURES].[{}]}} ON COLUMNS FROM [{}.DB] WHERE ({})'

        dim_tmp, dim_str_value = "[{}].[{}]", []

        for member in cube_data.members:
            # TODO: удалить костыль по игнорированию KOSGU
            if member['dimension'] != 'KOSGU':
                dim_str_value.append(dim_tmp.format(
                    member['dimension'],
                    member['cube_value']
                ))

        # Отдельная обработка лет
        if cube_data.year_member:
            dim_str_value.append(dim_tmp.format(
                cube_data.year_member['dimension'],
                cube_data.year_member['cube_value']
            ))

        # Отдельная обработка территория
        if cube_data.terr_member:
            dim_str_value.append(dim_tmp.format(
                cube_data.terr_member['dimension'],
                cube_data.terr_member['cube_value']
            ))

        cube_data.mdx_query = mdx_template.format(
            cube_data.selected_measure['cube_value'],
            cube_data.selected_cube['cube'],
            ','.join(dim_str_value)
        )

    # закладка под расширение типов MDX-запросов
    if mdx_type == 'basic':
        create_basic_mdx_query()


def best_answer_depending_on_cube(cube_data_list: list, correct_cube: str):
    """
    Выбор лучшего ответа по заданному кубу, если это возможно
    """

    # Для работы системы до появления классификатора
    if not correct_cube:
        return

    # Если данные есть
    if cube_data_list:
        used_cube = cube_data_list[0].selected_cube['cube']

        if used_cube != correct_cube:
            for cube_data in list(cube_data_list):
                scoring_model = MODEL_CONFIG["cube_answers_scoring_model"]

                if cube_data.selected_cube['cube'] == correct_cube:
                    # Перемена (swap) скора алгоритмически лучшего и
                    # верного по классификатору ответов местами

                    (
                        cube_data.score[scoring_model],
                        cube_data_list[0].score[scoring_model]
                    ) = (
                        cube_data_list[0].score[scoring_model],
                        cube_data.score[scoring_model],
                    )

                    # ответы снова в порядке убывания скора
                    cube_data_list = sorted(
                        cube_data_list,
                        key=lambda cube_data_elem: cube_data_elem.score[scoring_model],
                        reverse=True
                    )

                    logging.info(
                        "Query_ID: {}\tMessage: {}".format(
                            cube_data.request_id,
                            'Лучший ответ был сменен. Был куб {}, '
                            'стал {}, лучший путь {}'.format(
                                used_cube,
                                correct_cube,
                                cube_data.tree_path
                            )
                        )
                    )

                    return
        else:
            logging.info(
                "Query_ID: {}\tMessage: {}".format(
                    cube_data_list[0].request_id,
                    'Куб алгоритмически лучшего ответа '
                    'совпадает с кубом из классификатора'
                )
            )
            return

        logging.info(
            "Query_ID: {}\tMessage: {}".format(
                cube_data_list[0].request_id,
                "Выбор лучшим запроса на основе куба из "
                "классификатора не возможен, нет подходящих путей"
            )
        )
    else:
        logging.info(
            "Message: нет данных для выбора лучшего "
            "ответа по заданному куба"
        )


def delete_repetitions(cube_data_list: list):
    """
    Удаление из результата после прогона дерева
    повторяющихся комбинаций
    """

    cube_data_repr = []
    before_deleting = len(cube_data_list)

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

    after_deleting = len(cube_data_list)

    logging.info(
        "Query_ID: {}\tMessage: Удаление {} повторяющихся запросов".format(
            cube_data_list[0].request_id,
            before_deleting - after_deleting
        )
    )


def filter_cube_data_without_answer(cube_data_list: list):
    """
    Метод, который оставляет в списке только возвращающие данные запросы
    """

    if cube_data_list:
        request_id = cube_data_list[0].request_id
        before_filtering = len(cube_data_list)

        for cube_data in list(cube_data_list):

            response = send_request_to_server(
                cube_data.mdx_query,
                cube_data.selected_cube['cube']
            )

            if not check_mdx_returns_data(response):
                cube_data_list.remove(cube_data)

        after_filtering = len(cube_data_list)

        logging.info(
            'Query_ID: {}\tMessage: {} запрос(a/ов) не имели данных'.format(
                request_id,
                before_filtering - after_filtering
            )
        )


def feedback_preprocessing(verbal_feedback):
    """
    Преобразование для дальнейшего парсинга словаря с вербальными значениями измерений.
    Здесь же обрабатываются замены отдельных значений на более удобные.
    """
    res = {'куб': verbal_feedback.get('domain')}
    for dim in verbal_feedback.get('dims', []):
        newkey = dim['dimension_caption'].split(' ', 1)[0].lower()
        res[newkey] = dim['member_caption']

    if res.get('территория', '').lower() == 'неуказанная территория':
        res['территория'] = 'РФ'
    if verbal_feedback.get('measure', 'значение').lower() == 'значение':
        res['мера'] = None
    else:
        res['мера'] = verbal_feedback.get('measure')

    if 'месяц' in res and 'год' in res:
        res['месгод'] = '{} {} года'.format(res.get('месяц'), res.get('год'))
    elif 'год' in res:
        res['месгод'] = '{} год'.format(res.get('год'))
    elif 'месяц' in res:
        res['месгод'] = res.get('месяц')

    return {key: Phrase(res[key]) for key in res if res[key] is not None}


def get_pretty_feedback(cube_name, verbal_feedback):
    """
    Создание человекочитаемого фидбека из словаря по маске.
    """

    prepr_feedback = feedback_preprocessing(verbal_feedback)
    mask = CUBE_FEEDBACK_MASKS.get(cube_name)

    res = []
    for word in mask.split('{'):
        if '}' not in word:
            res.append(word)
            continue

        code, context = word.split('}', 1)
        code = code.split('?')
        word_index = 2 if code[0] == '' else 0
        word = code[word_index].split('*')
        val = prepr_feedback.get(word[0].lstrip('_').lower())
        if val is None:
            res.append(context)
            continue

        if len(word) == 1:
            val = val.verbal
        else:
            val = val.inflect(word[1:]).verbal

        if word[0][0] == '_':
            pass
        elif word[0][0].isupper():
            val = val[0].upper() + val[1:]
        else:
            val = val[0].lower() + val[1:]

        code[word_index] = val
        res += code + [context]

    return ''.join(res)
