#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Управление классами ядра системы
"""

import logging

from config import SETTINGS
from core.solr_old import Solr
from text_preprocessing import TextPreprocessing

from constants import ERROR_NO_DOCS_FOUND


class DataRetrieving:
    """
    Модуль связывающие в себе результаты работы Apache Solr,
    и классов обработки его выдачи - CubeProcessor и MinfinProcessor
    """

    @staticmethod
    def get_data(user_request: str, request_id: str):
        """API метод к сердцу системы.

        :param user_request: запрос от пользователя
        :param request_id: идентификатор запроса
        :return: ...
        """

        # TODO: рефакторинг, разбить код на более мелкие функции

        # инстанс класса, производящего нормализацию слов
        text_preprocessor = TextPreprocessing(request_id)

        # нормализация запроса пользователя
        normalized_user_request = text_preprocessor.normalization(
            user_request,
            delete_question_words=False
        )

        # инстанс класса, ответственного за работу с Apache Solr
        solr = Solr(SETTINGS.SOLR_MAIN_CORE)

        # получение структурированных результатов поиска
        found_docs = solr.get_data(normalized_user_request)

        # Если хотя бы 1 документ найден:
        if len(found_docs):
            # TODO: разделение документов по типу
            # TODO: отпрвка документов в CubeProcessor
            # TODO: отпрвка документов в MinfinProcessor
            # TODO: отпрвка ошибок во время исполнения CubeProcessor и MinfinProcessor
            # TODO: ранжирование объединенных ответов
            # TODO: формирование финального объекта
            pass
        else:
            # Обработка случая, когда документы не найдены
            found_docs.message = ERROR_NO_DOCS_FOUND
            logging_str = 'Документы не найдены Query_ID: {}\tSolr: {}'
            logging.info(logging_str.format(request_id, found_docs.error))

        return found_docs
