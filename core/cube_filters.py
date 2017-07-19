#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Реализация функции для узлов
"""

from core.cube_docs_processing import CubeData


class FunctionExecutionError(Exception):
    """Ошибка при невозможности выполнении функции в узле"""
    pass


def tree_start(cube_data: CubeData):
    """Корневая функция дерева"""

    return cube_data


def select_first_cube(cube_data: CubeData):
    """Выбор первого куба"""

    # Если кубов не найдено
    if not len(cube_data.cube):
        raise FunctionExecutionError({
            "function": select_first_cube.__name__,
            "message": "Во входных данных нет кубов"
        })

    cube_data.cube = cube_data.cube[0]


def select_second_cube(cube_data: CubeData):
    """Выбор второго куба"""

    pass


def select_third_cube(cube_data: CubeData):
    """Выбор третьего куба"""

    pass


def select_forth_cube(cube_data: CubeData):
    """Выбор четвертого куба"""

    pass


def ignore_current_year(cube_data: CubeData):
    """Игнорирование года, если он текущий"""

    pass


def not_ignore_current_year(cube_data: CubeData):
    """Не игнорирование текущего года"""
    pass


def filter_dimensions_by_year(cube_data: CubeData):
    """
    Фильтрация значений измерений по наличию
    в их кубах года
    """

    pass


def not_filter_dimensions_by_year(cube_data: CubeData):
    """
    Отсутствие фильтрации значений измерений по наличию
    в их кубах года
    """
    pass


def filter_dimensions_by_territory(cube_data: CubeData):
    """
    Фильтрация значений измерений по наличию
    в их кубах года
    """

    pass


def not_filter_dimensions_by_territory(cube_data: CubeData):
    """
    Отсутствие фильтрации значений измерений по наличию
    в их кубах года
    """
    pass


def select_all_best_members(cube_data: CubeData):
    """Выбор всех лучших элементов измерений"""

    pass
