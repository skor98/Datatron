#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Структура объекта ответа системы
"""

import json


class CoreAnswer:
    def __init__(self, message='', error=''):
        self.status = False
        self.doc_found = 0
        self.answer = None
        self.more_answers = None
        self.message = message
        self.error = error

    def toJSON(self):
        return json.dumps(self, default=lambda obj: obj.__dict__, indent=4, ensure_ascii=False)

    def toJSON_API(self):
        keys_to_return = (
            'status',
            'doc_found',
            'answer',
            'more_answers'
        )

        result_dict = {key: getattr(self, key, None) for key in keys_to_return}

        return json.dumps(
            result_dict,
            default=lambda obj: getattr(obj, 'to_reduced_object', lambda: None)(),
            indent=4,
            ensure_ascii=False,
        )
