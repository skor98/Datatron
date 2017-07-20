#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Взаимодействие с Solr. Логику необходимо разбить.

В данном файле лишь в одном методе происходит взаимодействие
с Solr, а во всех остальных идет работа с его выдачей.

На текущей момент:
1. Здесь идет обращение с нормализованным запросом в Solr
2. Сборка запроса по куба
3. Выбор ответов по Минфину
4. Формирование структуры финального возвращаемого объекта,
который далее пройдет обратно через data_retrieving, message_manager
к ui-элементу.
"""

import logging
import datetime

import numpy as np

from kb.kb_support_library import get_cube_dimensions
from kb.kb_support_library import get_default_member_for_dimension
from kb.kb_support_library import get_with_member_to_given_member
from kb.kb_support_library import get_default_cube_measure


# TODO: доделать логгирование принятия решений


class Solr:
    """
    Класс для взимодействия с поисковой системой Apache Solr
    """

    @staticmethod
    def _build_mdx_request(dimensions, measures, cube):
        """Формирование MDX-запроса, на основе найденных документов

        :param dimensions: список документов измерений
        :param measures: список документов мер
        :param cube: имя правильного куба
        :return: MDX-запрос
        """

        # шаблон MDX-запроса
        mdx_template = 'SELECT {{[MEASURES].[{}]}} ON COLUMNS FROM [{}.DB] WHERE ({})'

        # список измерения для куба
        all_cube_dimensions = get_cube_dimensions(cube)

        # найденные значения в Solr
        found_cube_dimensions = [doc['name'] for doc in dimensions]

        dim_tmp, dim_str_value = "[{}].[{}]", []

        for doc in dimensions:
            # добавление значений измерений в строку
            dim_str_value.append(dim_tmp.format(doc['name'], doc['fvalue']))

            # удаление из списка измерений использованное
            all_cube_dimensions.remove(doc['name'])

            # обработка связанных значений
            connected_value = get_with_member_to_given_member(doc['fvalue'])

            # Если у значения есть связанное значение
            if connected_value and connected_value['dimension'] not in found_cube_dimensions:
                dim_str_value.append(dim_tmp.format(
                    connected_value['dimension'],
                    connected_value['fvalue']))

                # удаление из списка измерений использованное
                all_cube_dimensions.remove(connected_value['dimension'])

        # обработка дефолтных значений для измерейни
        for ref_dim in all_cube_dimensions:
            default_value = get_default_member_for_dimension(cube, ref_dim)
            if default_value:
                dim_str_value.append(dim_tmp.format(
                    default_value['dimension'],
                    default_value['fvalue']))

        measure = get_default_cube_measure(cube)

        if measures:
            measure = measures[0]['formal']

        return mdx_template.format(measure, cube, ','.join(dim_str_value))
