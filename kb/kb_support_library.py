#!/usr/bin/python3
# -*- coding: utf-8 -*-

import kb.kb_db_creation as dbc

from text_preprocessing import TextPreprocessing


def is_dim_in_dim_set(dim, dim_set, dd):
    """
    Проверка наличия в конкретном наборе измерения dim_set
    такого измерение, название которого равно dim
    """
    return bool(list(filter(lambda dim_id: dd[dim_id] == dim, iter(dim_set))))


def is_dim_in_cube(dim, dd):
    """Проверка наличия в среди всеъ измерений куба, измерения с названием dim"""
    return bool(list(filter(lambda dim_id: dd[dim_id] == dim, iter(dd))))


def filter_combinations(combs, dim_set, dd):
    """Фильтрация запросов на основе 1-4 пунктов от Алексея-методолога"""

    filtered_combs = list(combs)

    # уровень бюджета, если присутствует в измерения, должен быть указан (пункт 4)
    if is_dim_in_cube('BGLEVELS', dd) and not is_dim_in_dim_set('BGLEVELS', dim_set, dd):
        print('входная комбинация: {} входной массив: {}, сокращение: 100%'.format(dim_set, len(combs)))
        return []

    # год, если присутствует в измерения, должен быть указан (пункт 3)
    if is_dim_in_cube('YEARS', dd) and not is_dim_in_dim_set('YEARS', dim_set, dd):
        print('входная комбинация: {} входной массив: {}, сокращение: 100%'.format(dim_set, len(combs)))
        return []

    # без территории работают уместно использовать 5 уровней бюджета (пункт 1)
    if is_dim_in_dim_set('BGLEVELS', dim_set, dd) and not is_dim_in_dim_set('TERRITORIES', dim_set, dd):
        bg_level_values = set(['09-0', '09-1', '09-8', '09-9', '09-10'])

        for comb in combs:
            formal_values = [i[1] for i in comb]
            if not bg_level_values.intersection(set(formal_values)):
                filtered_combs.remove(comb)

    # с территорией определенные 5 уровней бюджета использовать неуместно (пункт 1)
    if is_dim_in_dim_set('BGLEVELS', dim_set, dd) and is_dim_in_dim_set('TERRITORIES', dim_set, dd):
        bg_level_values = set(['09-0', '09-1', '09-8', '09-9', '09-10'])

        for comb in combs:
            formal_values = [i[1] for i in comb]
            if bg_level_values.intersection(set(formal_values)):
                filtered_combs.remove(comb)

    # значение "все уровни" работает с показателем, если он равен "объем чистых кассовых доходов" (пункт 2)
    if is_dim_in_dim_set('BGLEVELS', dim_set, dd) and is_dim_in_dim_set('MARKS', dim_set, dd):
        bg_level_and_mark_value = set(['09-0', '02-2'])

        for comb in combs:
            formal_values = [i[1] for i in comb]
            if (
                        bg_level_and_mark_value.intersection(set(formal_values))
                    and not bg_level_and_mark_value.issubset(set(formal_values))
            ):
                try:
                    filtered_combs.remove(comb)
                except ValueError:
                    pass

    out_pattern = (
        'входная комбинация: {0}, ' +
        'входной массив: {1}, ' +
        'выходной массив: {2}, ' +
        'сокращение: {3:.2%}'
    )
    print(out_pattern.format(
        dim_set,
        len(combs),
        len(filtered_combs),
        1 - len(filtered_combs) / len(combs)
    ))
    return filtered_combs


def get_full_values_for_dimensions(cube_values):
    """Получение полных вербальных значений измерений по формальным значениями"""

    full_values = []
    for cube_value in cube_values:
        given_value = dbc.Value.get(dbc.Value.cube_value == cube_value)
        full_values.append(given_value.full_value)

    return full_values


def get_full_value_for_measure(cube_value, cube_name):
    """Получение полного вербального значения меры по формальному значению и кубу"""

    measure = (dbc.Measure
               .select(dbc.Measure.full_value)
               .join(dbc.CubeMeasure)
               .join(dbc.Cube)
               .where(dbc.Measure.cube_value == cube_value, dbc.Cube.name == cube_name))[0]

    return measure.full_value


def get_cube_dimensions(cube_name):
    """Получение списка измерения куба"""

    dimensions = []
    for cube in dbc.Cube.select().where(dbc.Cube.name == cube_name):
        for cube_dimension in dbc.CubeDimension.select().where(dbc.CubeDimension.cube_id == cube.id):
            for dimension in dbc.Dimension.select().where(dbc.Dimension.id == cube_dimension.dimension_id):
                dimensions.append(dimension.label)
    return dimensions


def check_dimension_value_in_cube(cube_name, value):
    """Проверка наличия в кубе значения"""

    for val in dbc.Value.select().where(dbc.Value.cube_value == value):
        for dimension_value in dbc.DimensionValue.select().where(dbc.DimensionValue.value_id == val.id):
            for cube_dimension in dbc.CubeDimension.select().where(
                            dbc.CubeDimension.dimension_id == dimension_value.dimension_id
            ):
                for cube in dbc.Cube.select().where(dbc.Cube.id == cube_dimension.cube_id):
                    return cube.name == cube_name


def create_automative_cube_description(cube_name):
    """Генерация автоматического описания к кубу"""

    values = []
    for cube in dbc.Cube.select().where(dbc.Cube.name == cube_name):
        for dimension in dbc.CubeDimension.select().where(dbc.CubeDimension.cube_id == cube.id):
            for dim_value in dbc.DimensionValue.select().where(
                            dbc.DimensionValue.dimension_id == dimension.dimension_id
            ):
                for value in dbc.Value.select().where(dbc.Value.id == dim_value.value_id):
                    values.append(value.lem_index_value)

    values = ' '.join(values).split()
    popular_words = TextPreprocessing.frequency_destribution(values)
    popular_words_repeatition = sorted(popular_words * 3)
    return ' '.join(popular_words_repeatition)


def get_classification_for_dimension(cube_name, dimension_name):
    """Получение значений измерения конкретного куба"""

    values = []
    for cube in dbc.Cube.select().where(dbc.Cube.name == cube_name):
        for cube_dimension in dbc.CubeDimension.select().where(dbc.CubeDimension.cube_id == cube.id):
            for dim in dbc.Dimension.select().where(
                                    dbc.Dimension.id == cube_dimension.dimension_id and dbc.Dimension.label == dimension_name
            ):
                for dim_value in dbc.DimensionValue.select().where(dbc.DimensionValue.dimension_id == dim.id):
                    for value in dbc.Value.select().where(dbc.Value.id == dim_value.value_id):
                        values.append(value.full_value)
    return values


def get_representation_format(mdx_query):
    """Получение формата меры (рубли, проценты) для куба"""

    left_part = mdx_query.split('(')[0]
    measure_value = left_part.split('}')[0].split('.')[1][1:-1]
    return int(dbc.Measure.get(dbc.Measure.cube_value == measure_value).format)


def get_default_cube_measure(cube_name):
    """Полчение меры по умолчанию для куба"""

    default_measure_id = dbc.Cube.get(dbc.Cube.name == cube_name).default_measure
    return dbc.Measure.get(dbc.Measure.id == default_measure_id).cube_value


def create_lem_manual_description(cube_name):
    """Создание нормализованного описания для куба"""

    tp = TextPreprocessing('Creating lemmatized manual description')
    manual_description = dbc.Cube.get(dbc.Cube.name == cube_name).manual_description
    lem_manual_description = tp.normalization(manual_description)
    dbc.Cube.update(manual_lem_description=lem_manual_description).where(dbc.Cube.name == cube_name).execute()


def get_default_value_for_dimension(cube_name, dimension_name):
    # TODO: переписать код
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
