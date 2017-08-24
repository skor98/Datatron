#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Поддерживающие скрипты к базе знаний
"""

import logging
from os import listdir, path
import random
import re

from config import SETTINGS, TEST_PATH_RESULTS
import kb.kb_db_creation as dbc
import logs_helper  # pylint: disable=unused-import
import pandas as pd
from text_preprocessing import TextPreprocessing


TPP = TextPreprocessing(
    'KBSL',
    delete_digits=True,
    delete_question_words=True
)


def get_caption_for_measure(cube_value, cube_name):
    """
    Получение полного вербального значения меры
    по формальному значению и кубу
    """

    measure = (dbc.Measure
               .select(dbc.Measure.caption)
               .join(dbc.CubeMeasure)
               .join(dbc.Cube)
               .where(dbc.Measure.cube_value == cube_value, dbc.Cube.name == cube_name)
               )[0]

    return measure.caption


def get_measure_lem_key_words(cube_value: str, cube_name: str):
    """
    Получение нормализованных ключевых слов для меры, если они есть
    """

    measure = (dbc.Measure
               .select()
               .join(dbc.CubeMeasure)
               .join(dbc.Cube)
               .where(dbc.Measure.cube_value == cube_value, dbc.Cube.name == cube_name)
               )[0]

    return measure.lem_key_words


def get_cube_dimensions(cube_name):
    """Получение списка измерения куба"""

    query = (dbc.Dimension
             .select()
             .join(dbc.CubeDimension)
             .join(dbc.Cube)
             .where(dbc.Cube.name == cube_name))

    dimensions = [dimension.cube_value for dimension in query]

    return dimensions


def create_automative_cube_description(cube_name):
    """
    Генерация автоматического описания к кубу на основе
    частотного распределения слов в значениях его измерений
    """

    TOP_WORDS_QUANTITY = 5
    WORDS_REPETITION = 3

    query = (dbc.Member
             .select()
             .join(dbc.DimensionMember)
             .join(dbc.Dimension)
             .join(dbc.CubeDimension)
             .join(dbc.Cube)
             .where(dbc.Cube.name == cube_name))

    members = [member.lem_caption for member in query]

    # токенизация по словам
    members = ' '.join(members).split()

    popular_words = TextPreprocessing.frequency_destribution(
        members,
        TOP_WORDS_QUANTITY
    )

    # увеличиваем вес популярных слов и сортируем их
    popular_words = sorted(popular_words * WORDS_REPETITION)

    return ' '.join(popular_words)


def get_representation_format(mdx_query):
    """
    Получение формата меры (рубли, проценты, штуки) для куба
    """

    left_part = mdx_query.split('(')[0]
    measure_value = left_part.split('}')[0].split('.')[1][1:-1]
    measure = dbc.Measure.get(dbc.Measure.cube_value == measure_value)
    return int(measure.format)


def get_default_cube_measure(cube_name):
    """Получение меры для куба по умолчанию"""

    cube = dbc.Cube.get(dbc.Cube.name == cube_name)
    default_measure = dbc.Measure.get(dbc.Measure.id == cube.default_measure_id)
    return default_measure.cube_value


def get_default_member_for_dimension(cube_name, dimension_cube_value):
    """Получение значения измерения по умолчанию"""

    dimension = (dbc.Dimension
                 .select()
                 .join(dbc.CubeDimension)
                 .join(dbc.Cube)
                 .where(dbc.Cube.name == cube_name, dbc.Dimension.cube_value == dimension_cube_value)
                 )[0]

    # Если для измерения указано дефольное значение
    # И если оно не уровня All (в БД уровень All обозначается 0)
    if dimension.default_value_id:
        def_value = dbc.Member.get(dbc.Member.id == dimension.default_value_id)

        return {'dimension_cube_value': dimension_cube_value,
                'member_cube_value': def_value.cube_value}


def get_with_member_to_given_member(member_id):
    """Возвращает связанное значение измерения с данным"""

    given_member = dbc.Member.get(dbc.Member.id == member_id)

    if given_member.with_member:
        with_member = dbc.Member.get(dbc.Member.id == given_member.with_member)

        dimension = (dbc.Dimension
                     .select(dbc.Dimension.cube_value)
                     .join(dbc.DimensionMember)
                     .join(dbc.Member)
                     .where(dbc.Member.id == with_member.id)
                     )[0]

        return {'dimension_cube_value': dimension.cube_value,
                'member_cube_value': with_member.cube_value}


def get_cube_caption(cube_name):
    """Возвращает описание куба"""

    return dbc.Cube.get(dbc.Cube.name == cube_name).caption


def get_captions_for_dimensions(cube_value):
    """
    Возвращает вербальное описание элемента измерения:
    - понятное пользователю название измерения
    - понятное пользователю элемента измерения
    """

    value = dbc.Member.get(dbc.Member.cube_value == cube_value)

    dim = (dbc.Dimension
           .select()
           .join(dbc.DimensionMember)
           .join(dbc.Member)
           .where(dbc.Member.cube_value == cube_value))[0]

    return {'dimension_caption': dim.caption,
            'member_caption': value.caption}


def create_cube_lem_key_words():
    """
    Формирование нормализованного описания к кубам на основе
    ключевых слов, составленных методологами
    """

    for item in dbc.Cube.select():
        if item.key_words:
            lem_key_words = TPP(item.key_words)

            query = (dbc.Cube
                     .update(lem_key_words=lem_key_words)
                     .where(dbc.Cube.id == item.id)
                     )

            query.execute()


def create_measure_lem_key_words():
    """
    Формирование нормализованных ключевых слов к мерам
    """

    for item in dbc.Measure.select():
        if item.key_words:
            lem_key_words = TPP(item.key_words)

            query = (dbc.Measure
                     .update(lem_key_words=lem_key_words)
                     .where(dbc.Measure.id == item.id)
                     )

            query.execute()


def create_dimension_lem_key_words():
    """
    Формирование нормализованных ключевых слов к измерениям
    """

    for item in dbc.Dimension.select():
        if item.key_words:
            lem_key_words = TPP(item.key_words)

            query = (dbc.Dimension
                     .update(lem_key_words=lem_key_words)
                     .where(dbc.Dimension.id == item.id)
                     )

            query.execute()


def read_minfin_data():
    """Чтение данных по минфину"""
    path_to_folder_file = SETTINGS.PATH_TO_MINFIN_ATTACHMENTS

    files = []
    file_paths = []

    # Сохранение имеющихся в дериктории xlsx файлов
    for file in listdir(path_to_folder_file):
        if file.endswith(".xlsx"):
            file_paths.append(path.join(path_to_folder_file, file))
            files.append(file)

    # Создания листа с датафреймами по всем документам
    dfs = []
    for file_path in file_paths:
        # id документа имеет структуру {партия}.{порядковый номер}
        # id необходимо имплицитно привести к типу str, чтобы
        # номер вопроса 3.10 не становился 3.1
        df = pd.read_excel(
            open(file_path, 'rb'),
            converters={
                'id': str,
                'question': str,
                'short_answer': str,
                'full_answer': str,
            }
        )

        # Нужно обрезать whitespace
        COLUMNS_TO_STRIP = (
            'id',
            'question',
            'short_answer',
            'full_answer'
        )

        for row_ind in range(df.shape[0]):
            for column in COLUMNS_TO_STRIP:
                df.loc[row_ind, column] = df.loc[row_ind, column].strip()

                # Из полного ответа деление на абзацы лучше не убирать
                if column == 'full_answer':
                    continue

                df.loc[row_ind, column] = ' '.join(
                    df.loc[row_ind, column].split()
                )

        df = df.fillna(0)
        dfs.append(df)

    return files, dfs


def get_good_queries(count=0):
    """
    Возвращает успешные вопросы по кубам и минфину в перемешанном виде.
    Если count == 0, то возвращает все успешные запросы
    """

    if not get_good_queries.queries:
        good_cube_query_re = re.compile(r"\d*\.\s+\+\s+(.+)")
        good_mifin_query_re = re.compile(r'Запрос\s*"(.+)"\s*отрабатывает корректно')
        get_good_queries.queries = []

        test_paths = listdir(TEST_PATH_RESULTS)
        try:
            latest_cube_path = max(filter(lambda x: x.startswith("cube"), test_paths))
        except ValueError:
            logging.error("Нет тестов по кубам!")

        get_good_queries.queries += good_cube_query_re.findall(open(
            path.join(TEST_PATH_RESULTS, latest_cube_path),
            encoding="utf-8"
        ).read())

        try:
            latest_mifin_path = max(filter(lambda x: x.startswith("minfin"), test_paths))
        except ValueError:
            logging.error("Нет тестов по минфину!")

        get_good_queries.queries += good_mifin_query_re.findall(open(
            path.join(TEST_PATH_RESULTS, latest_mifin_path),
            encoding="utf-8"
        ).read())

        # А теперь поставим везде заглавной первую букву
        for ind, val in enumerate(get_good_queries.queries):
            get_good_queries.queries[ind] = val[0].upper() + val[1:]

    if count == 0 or count > len(get_good_queries.queries):
        count = len(get_good_queries.queries)
    return random.sample(get_good_queries.queries, count)


get_good_queries.queries = None
