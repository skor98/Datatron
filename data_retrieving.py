#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Управление классами ядра системы
"""

import logging

from core.solr import Solr
from core.cube_docs_processing import CubeAnswer
from core.support_library import group_documents
from core.support_library import send_request_to_server
from core.support_library import format_cube_answer
from core.answer_object import CoreAnswer
from core.cube_docs_processing import CubeProcessor
from core.minfin_docs_processing import MinfinProcessor

from text_preprocessing import TextPreprocessing

from config import SETTINGS
from constants import ERROR_NO_DOCS_FOUND
import logs_helper  # pylint: disable=unused-import


class DataRetrieving:
    """
    Модуль связывающие в себе результаты работы Apache Solr,
    и классов обработки его выдачи - CubeProcessor и MinfinProcessor
    """

    @staticmethod
    def get_data(user_request: str, request_id: str):
        """API метод к ядру системы"""

        core_answer = CoreAnswer()

        text_proc = TextPreprocessing(request_id)

        # нормализация запроса пользователя
        norm_user_request = text_proc.normalization(
            user_request,
            delete_question_words=False
        )

        # Год необходимо учитовать в нормированных данных по кубам
        # Но необходимо исключать из запросов, иначе вверх
        # поисковой выдачи выходят документы по Минфину
        if 'год' in norm_user_request:
            norm_user_request = norm_user_request.replace(
                'год', ''
            )

        # получение результатов поиска от Apache Solr в JSON-строке
        solr_response = Solr.get_data(
            norm_user_request, request_id, SETTINGS.SOLR_MAIN_CORE
        )['response']

        # Если хотя бы 1 документ найден:
        if solr_response['numFound']:
            minfin_docs, cube_data = group_documents(
                solr_response['docs'],
                user_request,
                request_id
            )

            minfin_answers = MinfinProcessor.get_data(minfin_docs)
            cube_answers = CubeProcessor.get_data(cube_data)

            logging.info(
                "Query_ID: {}\tMessage: Найдено {} докумета(ов) по кубам и {} по Минфину".format(
                    request_id,
                    len(cube_answers),
                    len(minfin_answers)
                )
            )

            answers = DataRetrieving.sort_answers(minfin_answers, cube_answers)

            core_answer = DataRetrieving.format_core_answer(answers, request_id)
        else:
            # Обработка случая, когда документы не найдены
            core_answer.message = ERROR_NO_DOCS_FOUND
            logging.info(
                'Query_ID: {}\tMessage: Документа не найдены'.format(request_id)
            )

        return core_answer

    @staticmethod
    def sort_answers(minfin_answers: list, cube_answers: list):
        """Сортировка ответов по кубам и минфину в общем списке"""

        # Если по минфину найден только 1 ответ
        if not isinstance(minfin_answers, list):
            minfin_answers = [minfin_answers]

        # Если по куба найден только 1 ответ
        if not isinstance(cube_answers, list):
            cube_answers = [cube_answers]

        # Фильтрация выборки в порядке убывания по score
        # TODO: подумать над улучшением параметра для сравнения
        all_answers = sorted(
            cube_answers + minfin_answers,
            key=lambda ans: ans.get_score(),
            reverse=True
        )

        return all_answers

    @staticmethod
    def format_core_answer(answers: list, request_id: str):
        """Формирование структуры финального ответа"""

        core_answer = CoreAnswer()

        # Предельное количество "смотри также"
        THRESHOLD = 5

        if answers:
            core_answer.status = True
            core_answer.doc_found = len(answers)

            # Выбор главного ответа
            core_answer.answer = answers[0]

            if isinstance(core_answer.answer, CubeAnswer):
                logging.info(
                    "Query_ID: {}\tMessage: Главный ответ - ответу по кубу - {}".format(
                        request_id,
                        core_answer.answer.mdx_query
                    ))

                response = send_request_to_server(
                    core_answer.answer.mdx_query,
                    core_answer.answer.cube
                )

                format_cube_answer(core_answer.answer, response)
            else:
                logging.info(
                    "Query_ID: {}\tMessage: Главный ответ - ответу по Минфину - {}".format(
                        request_id,
                        core_answer.answer.number
                    ))

            # Добавление до 5 дополнительных ответов
            core_answer.more_answers = answers[1:THRESHOLD + 1]

        return core_answer
