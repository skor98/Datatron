#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Управление классами ядра системы
"""

import logging

from core.solr import Solr
from core.support_library import group_documents
from core.answer_object import CoreAnswer
from core.cube_docs_processing import CubeProcessor
from core.minfin_docs_processing import MinfinProcessor

from text_preprocessing import TextPreprocessing

from config import SETTINGS
from constants import ERROR_NO_DOCS_FOUND


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

        # получение результатов поиска от Apache Solr в JSON-строке
        solr_response = Solr.get_data(norm_user_request, SETTINGS.SOLR_MAIN_CORE)['response']

        # Если хотя бы 1 документ найден:
        if solr_response['numFound']:
            # TODO: следующие 2 параметра могут быть полезны для аналитики
            # максимальный score по выдаче
            max_score = solr_response['maxScore']

            # количество найденных документов
            docs_num_found = solr_response['numFound']

            minfin_docs, cube_data = group_documents(solr_response['docs'])

            minfin_answers = MinfinProcessor.get_data(minfin_docs)
            cube_answers = CubeProcessor.get_data(cube_data, user_request)

            answers = DataRetrieving.sort_answers(minfin_answers, cube_answers)

            core_answer = DataRetrieving.format_core_answer(answers)
        else:
            pass
            # Обработка случая, когда документы не найдены
            core_answer.message = ERROR_NO_DOCS_FOUND

            # TODO: повысить содержательность логирования
            logging_str = 'Документы не найдены Query_ID: {}'.format(request_id)
            logging.info(logging_str)

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
        all_answers = sorted(cube_answers + minfin_answers,
                             key=lambda ans: ans.get_key(),
                             reverse=True)

        return all_answers

    @staticmethod
    def format_core_answer(answers: list):
        """Формирование структуры финального ответа"""

        core_answer = CoreAnswer()

        # Предельное количество "смотри также"
        THRESHOLD = 5

        if answers:
            core_answer.status = True
            core_answer.doc_found = len(answers)

            # Выбор главного ответа
            core_answer.answer = answers[0]

            # Добавление до 5 дополнительных ответов
            core_answer.more_answers = answers[1:THRESHOLD + 1]

        return core_answer
