#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Реализация функции для узлов
"""

from core.support_library import CubeData
from core.support_library import check_if_year_is_current
from core.support_library import FunctionExecutionError


def tree_start(cube_data: CubeData):
    """Корневая функция дерева"""
    pass


def select_first_cube(cube_data: CubeData):
    """Выбор первого куба"""

    # Если кубов не найдено
    if not len(cube_data.cubes):
        raise FunctionExecutionError({
            "function": select_first_cube.__name__,
            "message": "Кубов не было найдено"
        })

    cube_data.selected_cube = cube_data.cubes[0]


def select_second_cube(cube_data: CubeData):
    """Выбор второго куба"""

    # Если найден только один куб
    if len(cube_data.cubes) < 2:
        raise FunctionExecutionError({
            "function": select_second_cube().__name__,
            "message": "Найден только 1 куб"
        })

    cube_data.selected_cube = cube_data.cubes[1]


def select_third_cube(cube_data: CubeData):
    """Выбор третьего куба"""

    # Если найден только один куб
    if len(cube_data.cubes) < 3:
        raise FunctionExecutionError({
            "function": select_third_cube().__name__,
            "message": "Найдено только 2 куба"
        })

    cube_data.selected_cube = cube_data.cubes[2]


def select_forth_cube(cube_data: CubeData):
    """Выбор четвертого куба"""

    # Если найден только один куб
    if len(cube_data.cubes) < 4:
        raise FunctionExecutionError({
            "function": select_forth_cube().__name__,
            "message": "Найдено только 3 куба"
        })

    cube_data.selected_cube = cube_data.cubes[3]


def ignore_current_year(cube_data: CubeData):
    """Игнорирование года, если он текущий"""

    if cube_data.year_member:
        if check_if_year_is_current(cube_data):
            cube_data.year_member = None


def not_ignore_current_year(cube_data: CubeData):
    """Не игнорирование текущего года"""
    pass


def define_year_privilege_over_cube(cube_data: CubeData):
    """
    Фильтрация значений измерений по наличию
    в их кубах года
    """

    if cube_data.year_member:
        if 'Years' not in cube_data.selected_cube['dimensions']:
            raise FunctionExecutionError({
                "function": define_year_privilege_over_cube().__name__,
                "message": "Найденный КУБ не содержит измерения ГОД"
            })

        # фильтр измерений по принадлежности к выбранному кубу
        cube_data.members = [
            elem for elem in cube_data.members
            if elem['cube'] == cube_data.selected_cube['cube']
        ]


def define_cube_privilege_over_year(cube_data: CubeData):
    """
    Отсутствие фильтрации значений измерений по наличию
    в их кубах года
    """

    if cube_data.year_member:
        cube_data.year_member = None


def define_territory_privilege_over_cube(cube_data: CubeData):
    """
    Фильтрация значений измерений по наличию
    в их кубах года
    """

    if cube_data.terr_member:
        if 'Territories' not in cube_data.selected_cube['dimensions']:
            raise FunctionExecutionError({
                "function": define_territory_privilege_over_cube().__name__,
                "message": "Найденный КУБ не содержит измерения ТЕРРИТОРИЯ"
            })

        # фильтр элементов измерений по принадлежности к выбранному кубу
        cube_data.members = [
            elem for elem in cube_data.members
            if elem['cube'] == cube_data.selected_cube['cube']
        ]

        cube_data.terr_member = {
            'dimension': cube_data.terr_member['dimension'],
            'cube': cube_data.selected_cube,
            'cube_value': cube_data.terr_member[cube_data.selected_cube],
            'score': cube_data.terr_member['score']
        }


def not_filter_dimensions_by_territory(cube_data: CubeData):
    """
    Отсутствие фильтрации значений измерений по наличию
    в их кубах года
    """

    if cube_data.terr_member:
        cube_data.terr_member = None


def form_members_in_hierachy_by_score(cube_data: CubeData):
    """Формирование иерархии измерений"""

    if not cube_data.members:
        raise FunctionExecutionError({
            "function": form_members_in_hierachy_by_score().__name__,
            "message": "Все ЭЛЕМЕНТЫ измерений были удалены"
        })

    tmp_dimensions, idx = [], 0
    while cube_data.members:
        tmp_dimensions.append([])
        for member in cube_data.members:
            if '{}_{}'.format(member['name'], member['cube']) in tmp_dimensions[idx]:
                continue
            else:
                tmp_dimensions[idx].append('{}_{}'.format(
                    member['dimension'],
                    member['cube']
                ))

                tmp_dimensions[idx].append(member)
                cube_data.members.remove(member)
        idx += 1

    # Очистка от строк для отслеживания уникальности элементов в уровнях иерархии
    cube_data.members = [
        list(filter(lambda elem: not isinstance(elem, str), level))
        for level in tmp_dimensions
    ]


def all_members_from_first_hierarchy_level(cube_data: CubeData):
    """Выбор лучшего полного набора"""

    cube_data.members = cube_data.members[0]


def all_members_from_second_hierarchy_level(cube_data: CubeData):
    """Выбор полного набора из 2го уровня"""
    if len(cube_data.members) < 2:
        raise FunctionExecutionError({
            "function": all_members_from_second_hierarchy_level().__name__,
            "message": "2 уровня ИЕРАРХИИ не существует"
        })

    cube_data.members = cube_data.members[1]


def all_members_from_third_hierarchy_level(cube_data: CubeData):
    """Выбор полного набора из 3го уровня"""

    if len(cube_data.members) < 3:
        raise FunctionExecutionError({
            "function": all_members_from_third_hierarchy_level().__name__,
            "message": "3 уровня ИЕРАРХИИ не существует"
        })

    cube_data.members = cube_data.members[2]


def all_members_from_forth_hierarchy_level(cube_data: CubeData):
    """Выбор полного набора из 4го уровня"""

    if len(cube_data.members) < 4:
        raise FunctionExecutionError({
            "function": all_members_from_forth_hierarchy_level().__name__,
            "message": "4 уровня ИЕРАРХИИ не существует"
        })

    cube_data.members = cube_data.members[3]


def tree_end(cube_data: CubeData):
    """Завершение дерева"""
    pass
