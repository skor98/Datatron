#!/usr/bin/python3
# -*- coding: utf-8 -*-


import logging
import json

from string import punctuation as pct
from nltk.corpus import stopwords
from nltk import FreqDist
import nltk

import pymorphy2


class TextPreprocessing:
    def __init__(self, request_id, norming_style='lem'):
        self.request_id = request_id
        self.norming_style = norming_style
        self.language = 'russian'

    def normalization(self, text, delete_digits=False, delete_repeating_tokens=True):
        # TODO: обработка направильного спеллинга
        morph = pymorphy2.MorphAnalyzer()  # Лемматизатор

        # Замена нижнего подчеркивания встречающегося в caption в метаданных куба на пробел
        text = text.replace('_', ' ')
        tokens = nltk.word_tokenize(text.lower())

        # TODO: что делать с вопросительными словами?
        stop_words = stopwords.words(self.language)
        stop_words.remove('не')
        stop_words += "также иной г. год года году да нет".split()

        # Убираем знаки пунктуации и стоп слова
        tokens = [t for t in tokens if (t not in stop_words) and (t not in pct)]

        # Убираем дополнительные символы
        only_correct_symbols = [sym for sym in ' '.join(tokens) if sym not in ["«", "»", "`", "'"]]
        tokens = (''.join(only_correct_symbols)).split()

        # Убираем цифры
        if delete_digits:
            tokens = [t for t in tokens if not t.isdigit()]

        # Лемматизация
        tokens = [morph.parse(t)[0].normal_form for t in tokens]

        if delete_repeating_tokens:
            # Удаление повторяющихся токенов
            tokens = TextPreprocessing._delete_repeating_with_saving_order(tokens)

        normalized_request = ' '.join(tokens)

        logging_str = "ID-запроса: {}\tМодуль: {}\tЗапрос после нормализации: {}"
        logging.info(logging_str.format(self.request_id, __name__, normalized_request))

        return normalized_request

    @staticmethod
    def _delete_repeating_with_saving_order(tokens):
        # Распределени слов по повторениям
        fdist = nltk.FreqDist(tokens)

        # Отбор слов, повторяющихся более одного раза
        repeatings = [(i, fdist[i]) for i in fdist.keys() if fdist[i] > 1]

        # переворот листа для убирания повторов с конца
        tokens.reverse()

        # Удаление повторов
        for rep in repeatings:
            i = 0
            while i < rep[1] - 1:
                tokens.remove(rep[0])
                i += 1

        # возвращение исходного порядка
        tokens.reverse()

        return tokens

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
