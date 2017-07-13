#!/usr/bin/python3
# -*- coding: utf-8 -*-


import logging
import re

from nltk.corpus import stopwords
from nltk import FreqDist
import nltk

import pymorphy2

from model_manager import MODEL_CONFIG

logging.getLogger("pymorphy2").setLevel(logging.ERROR)


class TextPreprocessing:
    """
    Класс для предварительной обработки текста
    """
    def __init__(self, request_id):
        self.request_id = request_id
        self.norming_style = 'lem'
        self.language = 'russian'

        # TODO: что делать с вопросительными словами?
        # Базовый набор стоп-слов
        self.stop_words = stopwords.words(self.language)
        self.stop_words.remove('не')
        self.stop_words += "также иной год да нет -".split()

    def normalization(
            self,
            text,
            delete_digits=MODEL_CONFIG["normalization_delete_digits_default"],
            delete_question_words=MODEL_CONFIG["normalization_delete_question_words_default"],
            delete_repeatings=MODEL_CONFIG["normalization_delete_repeatings_default"]
    ):
        # TODO: обработка направильного спеллинга
        morph = pymorphy2.MorphAnalyzer()  # Лемматизатор

        # Замена нижнего подчеркивания встречающегося в caption в метаданных куба на пробел
        text = text.replace('_', ' ')

        # Выпиливаем всю оставшуюся пунктуацию, кроме дефисов
        text = re.sub(r'[^\w\s-]+', '', text)

        tokens = nltk.word_tokenize(text.lower())

        # Убираем цифры
        if delete_digits:
            tokens = [t for t in tokens if not t.isdigit()]

        # Лемматизация
        tokens = [morph.parse(t)[0].normal_form for t in tokens]

        if delete_repeatings:
            tokens = list(set(tokens))

        # Если вопросительные слова и другие частицы не должны быть
        # удалены из запроса, так как отражают его смысл

        stop_words = self.stop_words[:]  # копия, чтобы не испортить
        if not delete_question_words:
            delete_stop_words_list = ['кто', 'что', 'это', 'где', 'для', 'зачем', 'какой']
            stop_words = [sw for sw in stop_words if sw not in delete_stop_words_list]

        # Убираем стоп-слова
        tokens = [t for t in tokens if t not in stop_words]

        normalized_request = ' '.join(tokens)

        logging_str = "Query_ID: {}\tЗапрос после нормализации: {}"
        logging.info(logging_str.format(self.request_id, normalized_request))

        return normalized_request

    @staticmethod
    def frequency_destribution(word_list, num=5):
        """Строит частотное распределение слов в тексте и возврашает num наиболее популярных"""

        freq_dist = FreqDist(word_list)
        most_popular_words = freq_dist.most_common(num)
        popular_words = [i[0] for i in most_popular_words]
        return popular_words
