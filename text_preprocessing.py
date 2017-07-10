#!/usr/bin/python3
# -*- coding: utf-8 -*-


import logging
import json
import re

from nltk.corpus import stopwords
from nltk import FreqDist
import nltk

import pymorphy2

logging.getLogger("pymorphy2").setLevel(logging.ERROR)


class TextPreprocessing:
    def __init__(self, request_id):
        self.request_id = request_id
        self.norming_style = 'lem'
        self.language = 'russian'

    def normalization(self, text, delete_digits=False, delete_question_words=True, delete_repeatings=False):
        # TODO: обработка направильного спеллинга
        morph = pymorphy2.MorphAnalyzer()  # Лемматизатор

        # Замена нижнего подчеркивания встречающегося в caption в метаданных куба на пробел
        text = text.replace('_', ' ')

        # Выпиливаем всю оставшуюся пунктуацию, кроме дефисов
        text = re.sub('[^\w\s-]+', '', text)

        tokens = nltk.word_tokenize(text.lower())

        # Убираем цифры
        if delete_digits:
            tokens = [t for t in tokens if not t.isdigit()]

        # Лемматизация
        tokens = [morph.parse(t)[0].normal_form for t in tokens]

        if delete_repeatings:
            tokens = list(set(tokens))

        # TODO: что делать с вопросительными словами?
        # Базовый набор стоп-слов
        stop_words = stopwords.words(self.language)

        # Удаление из него отрицательной частицы
        stop_words.remove('не')

        # Если вопросительные слова и другие частицы не должны быть
        # удалены из запроса, так как отражают его смысл
        if not delete_question_words:
            delete_stop_words_list = ['кто', 'что', 'это', 'где', 'для', 'зачем', 'какой']
            stop_words = [sw for sw in stop_words if sw not in delete_stop_words_list]

        stop_words += "также иной год да нет -".split()

        # Убираем стоп-слова
        tokens = [t for t in tokens if t not in stop_words]

        normalized_request = ' '.join(tokens)

        logging_str = "Query_ID: {}\tЗапрос после нормализации: {}"
        logging.info(logging_str.format(self.request_id, normalized_request))

        return normalized_request

    @staticmethod
    def log_to_dict(log):
        """Принимает строку логов и возрврашает dict отображение, если это возможно"""
        json_str = ''
        try:
            log = log.split('\t')[1:]
            for log_line in log:
                log_line_parts = log_line.split(':')
                json_str += '"{}": "{}",'.format(
                    log_line_parts[0].strip(),
                    log_line_parts[1].strip()
                )

            json_str = '{' + json_str[:-1] + '}'
            return json.loads(json_str)
        except IndexError as ind_error:
            print('TextPreprocessing: ' + str(ind_error))
            return None

    @staticmethod
    def frequency_destribution(word_list, num=5):
        """Строит частотное распределение слов в тексте и возврашает num наиболее популярных"""

        freq_dist = FreqDist(word_list)
        most_popular_words = freq_dist.most_common(num)
        popular_words = [i[0] for i in most_popular_words]
        return popular_words
