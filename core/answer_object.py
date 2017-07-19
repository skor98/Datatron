#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Структура объекта ответа системы
"""

import json


class CoreAnswer:
    def __init__(self):
        self.status = False
        self.doc_found = 0
        self.answer = None
        self.more_answers = None
        self.message = ''
        self.error = ''

    def toJSON(self):
        return json.dumps(self, default=lambda obj: obj.__dict__, indent=4, ensure_ascii=False)

    def toJSON_API(self):
        # Если ответ был найден
        if self.status:

            # преобразование JSON в словарь
            # TODO: как это сделать менее костыльно?
            result_to_dict = json.loads(
                json.dumps(self, default=lambda obj: obj.__dict__, indent=4, ensure_ascii=False)
            )

            # Ключи для удаления из базового класса
            keys_to_remove_from_base_object = (
                'message',
                'error'
            )

            # Ключи для удаления из ответа по кубам
            key_to_remove_from_cube_answer = (
                'min_score', 'max_score', 'avg_score',
                'sum_score', 'cube_score', 'mdx_query',
                'status', 'cube'
            )

            # Ключи для удаления из ответа по Минфину
            key_to_remove_from_minfin_answer = (
                'score',
                'status'
            )

            # Удаление ключей из базового класса
            for key in keys_to_remove_from_base_object:
                result_to_dict.pop(key, None)

            # Объединение всех ответов в один список
            answers = [result_to_dict['answer']]
            if result_to_dict['more_answers']:
                answers.extend(result_to_dict['more_answers'])

            # Удаление ключей из ответов
            for answer in answers:
                if answer['type'] == 'cube':
                    for key in key_to_remove_from_cube_answer:
                        answer.pop(key, None)
                else:
                    for key in key_to_remove_from_minfin_answer:
                        answer.pop(key, None)

            return json.dumps(result_to_dict, ensure_ascii=False)
        else:
            return json.dumps(self, default=lambda obj: obj.__dict__, indent=4, ensure_ascii=False)
