#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Поддерживающие скрипты к базе знаний
"""

import kb.kb_db_creation as dbc

from text_preprocessing import TextPreprocessing


def get_full_value_for_measure(cube_value, cube_name):
    """
    Получение полного вербального значения меры
    по формальному значению и кубу
    """

    measure = (dbc.Measure
               .select(dbc.Measure.full_value)
               .join(dbc.CubeMeasure)
               .join(dbc.Cube)
               .where(dbc.Measure.cube_value == cube_value, dbc.Cube.name == cube_name))[0]

    return measure.full_value


def get_cube_dimensions(cube_name):
    """Получение списка измерения куба"""

    query = (dbc.Dimension
             .select()
             .join(dbc.CubeDimension)
             .join(dbc.Cube)
             .where(dbc.Cube.name == cube_name))

    dimensions = [dimension.label for dimension in query]

    return dimensions


def create_automative_cube_description(cube_name):
    """
    Генерация автоматического описания к кубу на основе
    частотного распределения слов в значениях его измерений
    """

    TOP_WORDS_QUANTITY = 5
    WORDS_REPETITION = 3

    query = (dbc.Value
             .select()
             .join(dbc.DimensionValue)
             .join(dbc.Dimension)
             .join(dbc.CubeDimension)
             .join(dbc.Cube)
             .where(dbc.Cube.name == cube_name))

    values = [value.lem_index_value for value in query]

    # токенизация по словам
    values = ' '.join(values).split()

    popular_words = TextPreprocessing.frequency_destribution(
        values,
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


def get_default_value_for_dimension(cube_name, dimension_name):
    """Получение значения измерения по умолчанию"""

    dimension = (dbc.Dimension
                 .select()
                 .join(dbc.CubeDimension)
                 .join(dbc.Cube)
                 .where(dbc.Cube.name == cube_name, dbc.Dimension.label == dimension_name))[0]

    # Если для измерения указано дефольное значение
    # И если оно не уровня All (в БД уровень All обозначается 0)
    if dimension.default_value_id:
        def_value = dbc.Value.get(dbc.Value.id == dimension.default_value_id)

        return {'dimension': dimension_name,
                'fvalue': def_value.cube_value}


def get_connected_value_to_given_value(cube_value):
    """Возвращает связанное значение измерения с данным"""

    given_value = dbc.Value.get(dbc.Value.cube_value == cube_value)
    if given_value.connected_value:
        connected_value = dbc.Value.get(dbc.Value.id == given_value.connected_value)

        dimension = (dbc.Dimension
                     .select(dbc.Dimension.label)
                     .join(dbc.DimensionValue)
                     .join(dbc.Value)
                     .where(dbc.Value.id == connected_value.id))[0]

        return {'dimension': dimension.label,
                'fvalue': connected_value.cube_value}


def get_cube_description(cube_name):
    """Возвращает описание куба"""

    return dbc.Cube.get(dbc.Cube.name == cube_name).description


def get_full_values_for_dimensions(cube_value):
    """
    Возвращает вербальное описание значения измерения:
    - понятное пользователю название измерения
    - понятное пользователю значение измерения
    """

    value = dbc.Value.get(dbc.Value.cube_value == cube_value)

    dim = (dbc.Dimension
           .select()
           .join(dbc.DimensionValue)
           .join(dbc.Value)
           .where(dbc.Value.cube_value == cube_value))[0]

    return {'dimension': dim.full_value,
            'full_value': value.full_value}
