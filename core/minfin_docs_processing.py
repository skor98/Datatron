#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Работа с документами по Минфину
"""


class MinfinProcessor:
    """
    Класс для обработки результатов по Минфину
    """

    @staticmethod
    def get_data(minfin_docs: list, user_request: str):
        """Работа с документами для вопросов Минфина"""

        answers = []

        # Обработка случая, когда документов по минфину не найдено
        if not minfin_docs:
            return answers

        for document in minfin_docs:
            answer = MinfinAnswer(user_request)

            answer.score = document['score']
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


class MinfinAnswer:
    """
    Возвращаемый объект этого модуля
    """

    def __init__(self, user_request=''):
        self.user_request = user_request
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
        self.order = None

    def get_score(self):
        """
        Функция для получения score, используемого
        как ключа для сортировки
        """
        return self.score

    def to_reduced_object(self):
        keys_to_return = (
            'user_request'
            'type',
            'number',
            'question',
            'short_answer',
            'full_answer',
            'link_name',
            'link',
            'picture_caption',
            'picture',
            'document_caption',
            'document',
            'message'
        )
        return {key: getattr(self, key, None) for key in keys_to_return}

    def to_reduced_api_object(self):
        """
        Нужно сделать препроцессинг, перед тем, как возращать в API
        """
        res = self.to_reduced_object()

        if res["link"] or res["document"] or res["picture"]:
            res["attachments"] = []
            if res["link"]:
                for link,  link_name in zip(res["link"], res["link_name"]):
                    res["attachments"].append({
                        "type": "url",
                        "path": link,
                        "description": link_name
                    })

            if res["document"]:
                for doc_name,  doc_caption in zip(res["document"], res["document_caption"]):
                    res["attachments"].append({
                        "type": "document",
                        "path": doc_name,
                        "description": doc_caption
                    })

            if res["picture"]:
                for pic_name, pic_caption in zip(res["picture"], res["picture_caption"]):
                    res["attachments"].append({
                        "type": "image",
                        "path": pic_name,
                        "description": pic_caption
                    })
        else:
            res["attachments"] = None

        del res["link"]
        del res["link_name"]

        del res["document"]
        del res["document_caption"]

        del res["picture"]
        del res["picture_caption"]

        return res


