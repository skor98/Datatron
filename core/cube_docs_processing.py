#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Работа с документами по кубам
"""

import logging
import copy

from core.graph import Graph
import core.support_library as csl
from core.support_library import CubeData
from core.support_library import FunctionExecutionError

import logs_helper  # pylint: disable=unused-import


# TODO: переработать структуру документов
# TODO: обращение к БД только во время препроцессинга

class CubeProcessor:
    """
    Класс для обработки результатов по кубам
    """

    @staticmethod
    def get_data(cube_data: CubeData, user_request: str):
        csl.manage_years(cube_data)

        # получение нескольких возможных вариантов
        cube_data_list = CubeProcessor._get_several_cube_answers(cube_data)

        # доработка вариантов
        for item in cube_data_list:
            csl.filter_measures_by_selected_cube(item)
            csl.score_cube_question(item)

        best_cube_data_list = CubeProcessor._take_best_cube_data(cube_data_list)

        for item in best_cube_data_list:
            # обработка связанных значений
            csl.process_with_members(item)

            # обработка дефолтных значений элементов измерений
            csl.process_default_members(item)

            # обработка дефолтных значений для меры
            csl.process_default_measures(item)

            # создание MDX-запросов
            csl.create_mdx_query(item)

        answers = CubeProcessor._format_final_cube_answer(
            best_cube_data_list, user_request
        )

        return answers

    @staticmethod
    def _get_several_cube_answers(cube_data: CubeData):
        """Формирование нескольких ответов по кубам"""

        BEST_PATHS_TRESHOLD = 10

        cube_data_list = []
        graph = Graph()

        for path in graph.k_shortest_paths(0, 16, BEST_PATHS_TRESHOLD):

            # копия для каждого прогона
            cube_data_copy = copy.deepcopy(cube_data)

            try:
                # последовательное исполнение функций узлов
                for node_id in path:
                    graph.node[node_id]['function'](cube_data_copy)

                # добавление успешного результата прогона в лист
                cube_data_list.append(cube_data_copy)
            except FunctionExecutionError as e:
                msg = e.args[0]
                logging.info('{}: {}'.format(msg['function'], msg['message']))

        return cube_data_list

    @staticmethod
    def _take_best_cube_data(cube_data_list: list):
        """Выбор нескольких лучших ответов по кубам"""

        SCORING_MODEL = 'sum'
        TRESHOLD = 5

        cube_data_list = sorted(
            cube_data_list,
            key=lambda cube_data: cube_data.score[SCORING_MODEL],
            reverse=True)

        return cube_data_list[:TRESHOLD + 1]

    @staticmethod
    def _format_final_cube_answer(cube_data_list: list, user_request: str):
        """Формирование финальной структуры ответа"""

        cube_answer_list = []

        for item in cube_data_list:
            cube = item.selected_cube['cube']

            feedback = csl.form_feedback(
                item.mdx_query,
                cube,
                user_request
            )

            cube_answer_list.append(
                CubeAnswer(
                    item.score,
                    item.mdx_query,
                    cube,
                    feedback
                )
            )

        return cube_answer_list


class CubeAnswer:
    """
    Возвращаемый объект этого модуля
    """

    def __init__(self, score, mdx_query, cube, feedback):
        self.status = True
        self.type = 'cube'
        self.score = score
        self.mdx_query = mdx_query
        self.cube = cube
        self.message = ''
        self.response = None
        self.formatted_response = None
        self.feedback = feedback

    def get_score(self):
        """
        Функция для получения score, используемого
        как ключа для сортировки
        """
        return self.score['sum']

    def todict_API(self):
        keys_to_return = (
            'type',
            'response',
            'formatted_response',
            'message',
            'feedback'
        )
        return {key: getattr(self, key, None) for key in keys_to_return}
