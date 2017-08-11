#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Структура объекта ответа системы
"""

import json


class TextResponseModel:
    def __init__(self):
        self.status = False
        self.question = None
        self.full_answer = 'Ответ не найден'
        self.short_answer = 'Ответ не найден'
        self.document_links = None
        self.image_links = None
        self.http_ref_links = None
        self.see_more = None

    def toJSON(self):
        return json.dumps(self, default=lambda obj: obj.__dict__, indent=4, ensure_ascii=False)

    def toJSON_API(self):
        keys_to_return = (
            'status',
            'question',
            'full_answer',
            'short_answer',
            'see_more',
        )

        if self.document_links is not None:
            keys_to_return.append('document_links')

        if self.image_links is not None:
            keys_to_return.append('image_links')

        if self.http_ref_links is not None:
            keys_to_return.append('http_ref_links')

        result_dict = {key: getattr(self, key, None) for key in keys_to_return}

        return json.dumps(
            result_dict,
            default=lambda obj: getattr(obj, 'to_reduced_api_object', lambda: None)(),
            ensure_ascii=False,
        ).encode("utf-8")
