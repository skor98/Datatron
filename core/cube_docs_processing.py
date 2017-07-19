#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Работа с документами по кубам
"""

import requests
import logging
from kb.kb_support_library import get_cube_caption
from kb.kb_support_library import get_caption_for_measure
from kb.kb_support_library import get_captions_for_dimensions
from core.support_library import CubeData
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
        return [CubeAnswer()]

    @staticmethod
    def define_graph_structure():
        dir_graph = nx.DiGraph()

        def define_nodes():
            """Определение вершин"""
            pass

        def define_edges():
            """Определение связей между ними"""
            pass


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
