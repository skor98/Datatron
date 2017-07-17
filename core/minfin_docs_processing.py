#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Работа с документами по Минфину
"""

import logging
import logs_helper  # pylint: disable=unused-import


class MinfinProcessor:
    """
    Класс для обработки результатов по Минфину
    """

    @staticmethod
    def _process_minfin_question(minfin_documents):
        """Работа с документами для вопросов Минфина

        :param minfin_documents: документы министерства финансов
        :return: список объектов класса MinfinResult() или None
        """

        # Обработка случая, когда документов по минфину не найдено
        if not minfin_documents:
            return

        answers = []

        for document in minfin_documents:
            answer = MinfinResult()

            answer.score = document['score']
            answer.status = True
            answer.number = document['number']
            answer.question = document['question']
            answer.short_answer = document['short_answer']

            try:
                answer.full_answer = document['full_answer']
            except KeyError:
                pass

            try:
                answer.link_name = document['link_name']
                answer.link = document['link']
            except KeyError:
                pass

            try:
                answer.picture_caption = document['picture_caption']
                answer.picture = document['picture']
            except KeyError:
                pass

            try:
                answer.document_caption = document['document_caption']
                answer.document = document['document']
            except KeyError:
                pass

            answers.append(answer)

        return answers


class MinfinResult:
    """
    Возвращаемый объект этого модуля
    """

    def __init__(self):
        self.status = False
        self.type = 'minfin'
        self.score = 0
        self.number = 0
        self.question = ''
        self.short_answer = ''
        self.full_answer = None
        self.link_name = None
        self.link = None
        self.picture_caption = None
        self.picture = None
        self.document_caption = None
        self.document = None
        self.message = None

    def get_key(self):
        """
        Функция для получения score, используемого
        как ключа для сортировки
        """
        return self.score
