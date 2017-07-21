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

BEST_PATHS_TRESHOLD = 10
logic_tree = Graph(BEST_PATHS_TRESHOLD)


class CubeProcessor:
    """
    Класс для обработки результатов по кубам
    """

    @staticmethod
    def get_data(cube_data: CubeData):
        csl.manage_years(cube_data)

        # получение нескольких возможных вариантов
        cube_data_list = CubeProcessor._get_several_cube_answers(cube_data)

        if cube_data_list:
            # доработка вариантов
            for item in cube_data_list:
                csl.filter_measures_by_selected_cube(item)
                csl.score_cube_question(item)

            cube_data_list = CubeProcessor._take_best_cube_data(cube_data_list)

            for item in cube_data_list:
                # обработка связанных значений
                csl.process_with_members(item)

                # обработка дефолтных значений элементов измерений
                csl.process_default_members(item)

                # обработка дефолтных значений для меры
                csl.process_default_measures(item)

                # создание MDX-запросов
                csl.create_mdx_query(item)

        answers = CubeProcessor._format_final_cube_answer(
            cube_data_list
        )

        return answers

    @staticmethod
    def _get_several_cube_answers(cube_data: CubeData):
        """Формирование нескольких ответов по кубам"""

        cube_data_list = []

        # TODO: сделать сборку графа единажды при запуске программы
        for path in logic_tree.gr_answer_combinations:

            # копия для каждого прогона
            cube_data_copy = copy.deepcopy(cube_data)

            try:
                # последовательное исполнение функций узлов
                for node_id in path:
                    logic_tree.node[node_id]['function'](cube_data_copy)

                # добавление успешного результата прогона в лист
                cube_data_list.append(cube_data_copy)
            except FunctionExecutionError as e:
                msg = e.args[0]
                logging.info('Query_ID: {}\tTree_path: {}\tMessage: {}-{}'.format(
                    cube_data_copy.request_id,
                    path,
                    msg['function'],
                    msg['message']))

        return cube_data_list

    @staticmethod
    def _take_best_cube_data(cube_data_list: list):
        """Выбор нескольких лучших ответов по кубам"""

        SCORING_MODEL = 'sum'
        TRESHOLD = 5

        csl.delete_repetitions(cube_data_list)

        cube_data_list = sorted(
            cube_data_list,
            key=lambda cube_data: cube_data.score[SCORING_MODEL],
            reverse=True)

        return cube_data_list[:TRESHOLD + 1]

    @staticmethod
    def _format_final_cube_answer(cube_data_list: list):
        """Формирование финальной структуры ответа"""

        cube_answer_list = []

        for item in cube_data_list:
            cube = item.selected_cube['cube']

            feedback = csl.form_feedback(
                item.mdx_query,
                cube,
                item.user_request
            )

            cube_answer_list.append(
                CubeAnswer(
                    item.request_id,
                    item.user_request,
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

    def __init__(self, request_id, user_request, score, mdx_query, cube, feedback):
        self.status = True
        self.request_id = request_id
        self.user_request = user_request
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
