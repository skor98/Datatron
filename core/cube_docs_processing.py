#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Работа с документами по кубам
"""

import copy
import logging

from config import SETTINGS
from core.graph import Graph
from core.support_library import CubeData
from core.support_library import FunctionExecutionError
from core.support_library import FunctionExecutionErrorNoMembers
import core.support_library as csl
import logs_helper  # pylint: disable=unused-import
from model_manager import MODEL_CONFIG


class CubeProcessor:
    """
    Класс для обработки результатов по кубам
    """

    @staticmethod
    def get_data(cube_data: CubeData, correct_cube: tuple = None):
        """API метод к работе с документами по кубам в ядре"""
        # уверенность ответа по кубам
        confidence = True

        # увеличения скора корректного по мнению классификатора куба
        CubeProcessor._boost_correct_cube_from_clf(cube_data, correct_cube)

        # увеличения скора мер от корректного по мнеию классификатора куба
        CubeProcessor._boost_measures_of_correct_cube_from_clf(
            cube_data, correct_cube)

        # увеличения скора элементов измерений
        # CubeProcessor._boost_members_of_correct_cube_form_clf(
        #     cube_data, correct_cube
        # )

        cube_data_list = []

        if cube_data:

            # Удаление территории в том случае, если есть вероятность,
            # что территория найдена по неключевым словам "автономный", "федеральный" и пр.
            if cube_data.terr_member:
                lem_key_words = cube_data.terr_member.get('lem_key_words', None)
                lem_territory = cube_data.terr_member['lem_member_caption']
                if lem_key_words:
                    if lem_key_words not in cube_data.norm_user_request:
                        if lem_territory.split()[0] not in cube_data.norm_user_request:
                            cube_data.terr_member = None

            # for member in list(cube_data.members):
            #     if member['cube_value'] == '09-20':
            #         cube_data.members.remove(member)
            #     elif member['dimension'] == 'KDGROUPS' and member['score'] < 8:
            #         cube_data.members.remove(member)


            # получение нескольких возможных вариантов
            cube_data_list = CubeProcessor._get_several_cube_answers(cube_data)

            if cube_data_list:
                logging.info(
                    "Query_ID: {}\tMessage: Собрано {} ответов "
                    "по кубам".format(
                        cube_data_list[0].request_id,
                        len(cube_data_list)
                    )
                )
            else:
                logging.info(
                    "Query_ID: {}\tMessage: Собрано 0 ответов "
                    "по кубам".format(cube_data.request_id)
                )

            if cube_data_list:
                # доработка вариантов
                for item in cube_data_list:
                    csl.select_measure_for_selected_cube(item)
                    csl.preprocess_territory_member(item)
                    csl.score_cube_question(item)

                cube_data_list = CubeProcessor._take_best_cube_data(
                    cube_data_list, correct_cube[0])

                for item in cube_data_list:
                    # обработка связанных значений
                    csl.process_with_members(item)

                    # обработка связанного значения для территории
                    csl.process_with_member_for_territory(item)

                    # обработка дефолтных значений элементов измерений
                    csl.process_default_members(item)

                    # обработка дефолтных значений для меры
                    csl.process_default_measures(item)

                    # создание MDX-запросов
                    csl.create_mdx_query(item)

            # фильтрация по наличие данных возможно только на этом этапе
            # когда собран MDX-запрос
            if SETTINGS.CHECK_CUBE_DATA_EXISTENCE:
                confidence = csl.filter_cube_data_without_answer(cube_data_list)

                # после фильтрации по наличию данных можно выбрать лучший
                # как с помощью классификатора, так и по умолчанию (то есть по скору)
                csl.best_answer_depending_on_cube(cube_data_list, correct_cube[0])

        answers = CubeProcessor._format_final_cube_answer(
            cube_data_list
        )

        return answers, confidence

    @staticmethod
    def _boost_correct_cube_from_clf(cube_data: CubeData, correct_cube: tuple):
        """
        Бустинг куба, который классификатор считает корректным
        """

        def boosting_function(score: float, clf_prob: float):
            """Степень бустинга растет с уверенностью классификатора"""
            new_score = score * (1 - clf_prob / (clf_prob - 1))

            # ограничение сверху, чтобы понизить максимальный скор
            # ответа по кубу и востановить баланс с ответам по минфину
            if new_score > MODEL_CONFIG["cube_boosting_threshold"]:
                new_score = MODEL_CONFIG["cube_boosting_threshold"]
            return new_score

        if correct_cube:
            for cube in cube_data.cubes:
                if cube['cube'] == correct_cube[0]:
                    cube['score'] = boosting_function(
                        cube['score'],
                        correct_cube[1]
                    )
                    break

            cube_data.cubes = sorted(
                cube_data.cubes,
                key=lambda elem: elem['score'],
                reverse=True
            )

    @staticmethod
    def _boost_measures_of_correct_cube_from_clf(
            cube_data: CubeData,
            correct_cube: tuple
    ):
        """
        Увеличение скора мер корректного по мнению
        классификатора куба
        """

        if correct_cube:
            for measure in cube_data.measures:
                if measure['cube'] == correct_cube:
                    measure['score'] += 1

            cube_data.measures = sorted(
                cube_data.measures,
                key=lambda elem: elem['score'],
                reverse=True
            )

    @staticmethod
    def _boost_members_of_correct_cube_form_clf(
            cube_data: CubeData,
            correct_cube: tuple
    ):
        if correct_cube:
            for member in cube_data.members:
                if member['cube'] == correct_cube:
                    member['score'] *= 1.25

            cube_data.members = sorted(
                cube_data.members,
                key=lambda elem: elem['score'],
                reverse=True
            )

    @staticmethod
    def _get_several_cube_answers(cube_data: CubeData):
        """Формирование нескольких ответов по кубам"""

        cube_data_list = []

        tree = Graph.inst(MODEL_CONFIG['tree_k_path_threshold'])

        for path in tree.tree_paths:

            # копия для каждого прогона
            cube_data_copy = copy.deepcopy(cube_data)

            try:
                # последовательное исполнение функций узлов
                for node_id in path:
                    tree.node[node_id]['function'](cube_data_copy)

                # занесение сработавшего пути
                cube_data_copy.tree_path = path

                # добавление успешного результата прогона в лист
                cube_data_list.append(cube_data_copy)
            except FunctionExecutionErrorNoMembers as error:
                # все равно добавление элемента список,
                # так как есть еще есть дефолтные значения
                cube_data_copy.tree_path = path
                cube_data_list.append(cube_data_copy)

                msg = error.args[0]
                logging.info('Query_ID: {}\tTree_path: {}\tMessage: {}-{}'.format(
                    cube_data_copy.request_id,
                    path,
                    msg['function'],
                    msg['message']))
            except FunctionExecutionError as error:
                msg = error.args[0]
                logging.info('Query_ID: {}\tTree_path: {}\tMessage: {}-{}'.format(
                    cube_data_copy.request_id,
                    path,
                    msg['function'],
                    msg['message']))

        return cube_data_list

    @staticmethod
    def _take_best_cube_data(cube_data_list: list, correct_cube: str):
        """Выбор нескольких лучших ответов по кубам"""

        threshold = MODEL_CONFIG['best_cube_data_threshold']
        scoring_model = MODEL_CONFIG["cube_answers_scoring_model"]

        csl.delete_repetitions(cube_data_list)

        cube_data_list = sorted(
            cube_data_list,
            key=lambda cube_data: cube_data.score[scoring_model],
            reverse=True)

        logging.info(
            "Query_ID: {}\tMessage: Алгоритмически лучший "
            "ответ создан на пути {}".format(
                cube_data_list[0].request_id,
                cube_data_list[0].tree_path
            )
        )

        # Выбор главного ответа по классификатору
        # Альтернативная версия выбора главного ответа
        csl.best_answer_depending_on_cube(cube_data_list, correct_cube)

        if SETTINGS.CHECK_CUBE_DATA_EXISTENCE:
            # так, как мы хотим, чтобы смотри также нормально работало
            # то при проверке на наличие данных придется проверять не первые три
            # запроса, а все; 5 запросов может быть мало
            threshold = 9

        return cube_data_list[:threshold + 1]

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

    @staticmethod
    def get_time_data_relevance(cube_answer):
        """
        Актуальность данных по кубам
        """

        date_of_update = '16.08.2017'
        updates = {
            'CLDO01': date_of_update,
            'CLDO02': date_of_update,
            'INDO01': date_of_update,
            'EXDO01': date_of_update
        }

        return updates.get(cube_answer.feedback['formal']['cube'], None)


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
        self.order = None

    def get_score(
            self,
            scoring_model=MODEL_CONFIG["cube_answers_scoring_model"]
    ):
        """
        Функция для получения score, используемого
        как ключа для сортировки
        """

        return self.score[scoring_model]

    def to_reduced_object(self):
        """Преобразование в сокращенный объект для API"""

        keys_to_return = (
            'type',
            'response',
            'formatted_response',
            'message',
            'feedback'
        )
        return {key: getattr(self, key, None) for key in keys_to_return}

    def to_reduced_api_object(self):
        """
        Нужно сделать препроцессинг, перед тем, как возращать в API
        """
        res = self.to_reduced_object()

        return res
