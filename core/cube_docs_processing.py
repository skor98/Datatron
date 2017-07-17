#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Работа с документами по кубам
"""

import requests
import logging
from kb.kb_support_library import get_cube_description
from kb.kb_support_library import get_full_value_for_measure
from kb.kb_support_library import get_full_values_for_dimensions
import logs_helper  # pylint: disable=unused-import


# TODO: переработать структуру документов
# TODO: обращение к БД только во время препроцессинга

class CubeProcessor:
    """
    Класс для обработки результатов по кубам
    """
    pass


class CubeResult:
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
