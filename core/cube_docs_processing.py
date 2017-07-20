#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Работа с документами по кубам
"""

import requests
import logging
import copy

from core.graph import define_graph_structure
import core.support_library as csl
from core.support_library import CubeData
from core.support_library import FunctionExecutionError
import networkx as nx

import logs_helper  # pylint: disable=unused-import


# TODO: переработать структуру документов
# TODO: обращение к БД только во время препроцессинга

class CubeProcessor:
    """
    Класс для обработки результатов по кубам
    """

    @staticmethod
    def get_data(cube_data: CubeData):
        csl.manage_years(cube_data)

        # форрмирование дерева
        graph = define_graph_structure()

        # получение нескольких возможных вариантов
        cube_data_list = CubeProcessor.get_several_cube_answers(cube_data, graph)

        # доработка вариантов
        for item in cube_data_list:
            csl.filter_measures_by_selected_cube(item)
            csl.score_cube_question(cube_data)

        best_cube_data_list = CubeProcessor.take_best_cube_datas(cube_data_list)

        for item in best_cube_data_list:
            # TODO: обработка связанных значений
            # TODO: обаботка дефолтных значений
            pass

        return [CubeAnswer()]

    @staticmethod
    def get_several_cube_answers(cube_data: CubeData, graph: nx.DiGraph()):
        """Формирование нескольких ответов по кубам"""

        cube_data_list = []
        for path in nx.all_shortest_paths(graph, source=0, target=16, weight='weight'):

            cube_data_copy = copy.deepcopy(cube_data)

            try:
                for node_id in path:
                    graph.node[node_id]['function'](cube_data_copy)

                cube_data_list.append(cube_data_copy)
            except FunctionExecutionError as e:
                msg = e.argsp[0]
                logging.error('{}: {}'.format(msg['function'], msg['message']))

        return cube_data_list

    @staticmethod
    def take_best_cube_datas(cube_data_list: list):
        """Выбор нескольких лучших ответов по кубам"""

        SCORING_MODEL = 'sum'
        TRESHOLD = 5

        cube_data_list = sorted(
            cube_data_list,
            key=lambda cube_data: cube_data.score[SCORING_MODEL],
            reverse=True)

        return cube_data_list[:TRESHOLD + 1]


class CubeAnswer:
    """
    Возвращаемый объект этого модуля
    """

    def __init__(self):
        self.status = False
        self.type = 'cube'
        self.cube_score = 0
        self.avg_score = 0
        self.max_score = 0
        self.min_score = 0
        self.sum_score = 0
        self.mdx_query = None
        self.cube = None
        self.response = None
        self.formatted_response = None
        self.message = None
        self.feedback = None

    def get_key(self):
        """
        Функция для получения score, используемого
        как ключа для сортировки
        """
        return self.sum_score
    
    def todict_API(self):
        keys_to_return = (
            'type',
            'response',
            'formatted_response',
            'message',
            'feedback'
        )
        return {key: getattr(self, key, None) for key in keys_to_return}
