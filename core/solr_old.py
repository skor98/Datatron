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
    def _process_cube_document(year, territory, dimensions, measures, cubes):
        """Сборка одного запроса по кубу"""

        cube_result = None

        # Фильтрация документов
        filtered_docs = Solr._filter_cube_documents(
            year,
            territory,
            dimensions,
            measures,
            cubes
        )

        if filtered_docs:
            (final_dimensions,
             final_measures,
             final_cube,
             cube_score) = filtered_docs

            # Сборка MDX запроса, если после фильтрации какие-то измерения остались
            if final_dimensions:
                cube_result.mdx_query = Solr._build_mdx_request(
                    final_dimensions,
                    final_measures,
                    final_cube
                )

                cube_result.cube = final_cube
                cube_result.cube_score = cube_score
                Solr._calculate_score_for_cube_questions(
                    final_dimensions,
                    measures,
                    year,
                    territory,
                    cube_result
                )

                cube_result.status = True
        else:
            # TODO: исправить
            cube_result.message = "Все измерения были удалены после фильтрации"

        return cube_result

    @staticmethod
    def _filter_cube_documents(year, territory, dimensions, measures, cubes):
        """Фильтрация найденных измерений"""

        final_dimension_list = []
        cube_above_territory_priority = False

        # Определение куба
        try:
            reference_cube = cubes[0]['cube']
            reference_cube_score = cubes[0]['score']
        except IndexError:
            # TODO: придумать более красивый выход
            # Если куб не найден (что очень мало вероятно)
            logging.warning('Куб для запроса не найден')
            return

            # Фильтрация по году
        if year:
            # Если указан текущий год, то запрос скорее всего относится
            # К кубу с оперативной информацией (CLDO01), год в которой не указывается
            if year['fvalue'] == datetime.datetime.now().year:
                year = None
            # Приоритет года над кубом
            else:
                # фильтр измерений по наличию в их кубах годов
                dimensions = [item for item in dimensions if 'Years' in get_cube_dimensions(item['cube'])]

                # фильтр списка кубов по наличию в кубе года
                cubes = [item for item in cubes if 'Years' in get_cube_dimensions(item['cube'])]

                # Если таковые найдены
                if cubes:
                    # выбор нового куба
                    reference_cube = cubes[0]['cube']
                    reference_cube_score = cubes[0]['score']
                    final_dimension_list.append(year)
                else:
                    # TODO: придумать более красивый выход
                    logging.warning('После фильтра по ГОДУ кубов не осталось')
                    return

                    # Доопределение куба
        if dimensions:
            # Замена куба на другой, если score найденного куба меньше score верхнего документа
            if (
                            reference_cube != dimensions[0]['cube'] and
                            reference_cube_score < dimensions[0]['score']
            ):
                reference_cube = dimensions[0]['cube']
                reference_cube_score = dimensions[0]['score']
            # Если найденный куб и куб верхнего документа совпадают,
            # а также score документа выше, то приоритет куба выше территории
            if (
                            reference_cube == dimensions[0]['cube'] and
                        (
                                        reference_cube_score < dimensions[0]['score'] or
                                        abs(reference_cube_score - dimensions[0]['score']) < 0.3 * reference_cube_score
                        )
            ):
                cube_above_territory_priority = True

        if cube_above_territory_priority:
            # Приоритет куба над территорией
            if territory:
                if 'Territories' not in get_cube_dimensions(reference_cube):
                    territory = None
        else:
            # Приоритет территории над кубом
            if territory:
                # Фильтр измерений по наличии в их кубах территории
                dimensions = [item for item in dimensions if 'Territories' in get_cube_dimensions(item['cube'])]

                # фильтр списка кубов по наличию в кубе территории
                cubes = [item for item in cubes if 'Territories' in get_cube_dimensions(item['cube'])]

                # Если таковые найдены
                if cubes:
                    # выбор нового куба
                    reference_cube = cubes[0]['cube']
                    reference_cube_score = cubes[0]['score']
                    final_dimension_list.append({
                        'name': territory['name'],
                        'cube': reference_cube,
                        'fvalue': territory[reference_cube],
                        'score': territory['score']
                    })
                else:
                    # TODO: придумать более красивый выход
                    logging.warning('После фильтра по ТЕРРИТОРИИ кубов не осталось')
                    return

                    # Построение иерархического списка измерений
        tmp_dimensions, idx = [], 0
        while dimensions:
            tmp_dimensions.append([])
            for doc in list(dimensions):
                # TODO: реализовать для смотри также
                if '{}_{}'.format(doc['name'], doc['cube']) in tmp_dimensions[idx]:
                    continue
                else:
                    tmp_dimensions[idx].append('{}_{}'.format(
                        doc['name'],
                        doc['cube']
                    ))
                    tmp_dimensions[idx].append(doc)
                    dimensions.remove(doc)
            idx += 1

        # Очистка от ненужных элементов
        dimensions = [list(filter(lambda elem: not isinstance(elem, str), level)) for level in tmp_dimensions]

        # если какие-то измерения (кроме территории, года) были найдены:
        if dimensions:
            # Это часть позволила улучшить алгоритм с 5/39 до 11/39
            # Берем все элементы из первой череды измерений для выбранного куба
            for dim in dimensions[0]:
                if dim['cube'] == reference_cube:
                    final_dimension_list.append(dim)

        # Если Solr нашел какие-нибудь меры
        if measures:
            # Фильтрация мер по принадлежности к выбранному кубу
            measures = [item for item in measures if item['cube'] == reference_cube]

        return final_dimension_list, measures, reference_cube, reference_cube_score

    @staticmethod
    def _calculate_score_for_cube_questions(dimensions, measures, year, territory, solr_result):
        """Подсчет различных видов score для запроса по кубу"""

        scores = []

        scores.append(solr_result.cube_score)

        # ToDo: Проверка, что ['score'] существует и к нему можно обратиться (2!)
        for dim in dimensions:
            scores.append(dim['score'])

        for measure in measures:
            scores.append(measure['score'])

        if year:
            scores.append(year['score'])

        if territory:
            scores.append(territory['score'])

        solr_result.avg_score = np.mean(scores)
        solr_result.min_score = min(scores)
        solr_result.max_score = max(scores)
        solr_result.sum_score = sum(scores)

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
