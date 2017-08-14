#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Работа с текстом: нормализация, частотное распределение
"""

import logging
import re
from functools import lru_cache

from nltk.corpus import stopwords
from nltk import FreqDist
import nltk

import pymorphy2

from model_manager import MODEL_CONFIG
from core.tonita_parser import TonitaParser

logging.getLogger("pymorphy2").setLevel(logging.ERROR)


@lru_cache(maxsize=16384)  # на самом деле, 8192 почти достаточно
def get_normal_form(s):
    return get_normal_form.morph.parse(s)[0].normal_form


get_normal_form.morph = pymorphy2.MorphAnalyzer()  # Лемматизатор


class TextPreprocessing:
    """
    Класс для предварительной обработки текста
    """

    def __init__(self, request_id=None):
        self.request_id = request_id
        self.language = 'russian'

        # TODO: что делать с вопросительными словами?
        # Базовый набор стоп-слов
        self.stop_words = set(stopwords.words(self.language))
        self.stop_words -= {'не', 'такой'}
        self.stop_words.update(set("подсказать также иной да нет -".split()))

    def normalization(
            self,
            text,
            delete_digits=MODEL_CONFIG["normalization_delete_digits_default"],
            delete_question_words=MODEL_CONFIG["normalization_delete_question_words_default"],
            delete_repeatings=MODEL_CONFIG["normalization_delete_repeatings_default"],
            parse_dates = MODEL_CONFIG["normalization_parse_dates_default"]
    ):
        """Метод для нормализации текста"""

        # TODO: обработка направильного спеллинга

        # Применение фильтров
        text = TextPreprocessing._filter_percent(text)
        text = TextPreprocessing._filter_underscore(text)
        # text = TextPreprocessing._filter_volume(text)

        # Выпиливаем всю оставшуюся пунктуацию, кроме дефисов
        text = re.sub(r'[^\w-]+', ' ', text)

        # Токенизируем
        tokens = nltk.word_tokenize(text.lower())

        # Убираем цифры
        if delete_digits:
            tokens = [t for t in tokens if not t.isdigit()]

        # Лемматизация
        tokens = [get_normal_form(t) for t in tokens]

        # Если вопросительные слова и другие частицы не должны быть
        # удалены из запроса, так как отражают его смысл
        stop_words = set(self.stop_words)
        if not delete_question_words:
            delete_stop_words_set = set(['кто', 'что', 'это', 'где', 'для', 'зачем', 'какой'])
            stop_words = stop_words - delete_stop_words_set

        # Убираем стоп-слова
        tokens = [t for t in tokens if t not in stop_words]

        # Парсим даты
        if parse_dates:
            tokens = TonitaParser.process(' '.join(tokens)).split(' ')

        # Убираем повторяющиеся слова
        if delete_repeatings:
            tokens = list(set(tokens))

        normalized_request = ' '.join(tokens)

        logging.info(
            "Query_ID: {}\tMessage: Запрос после нормализации: {}".format(
                self.request_id, normalized_request
            )
        )

        return normalized_request

    @staticmethod
    def _filter_underscore(text: str):
        """Обработка нижнего подчеркивания"""

        if '_' in text:
            text = text.replace('_', ' ')
        return text

    @staticmethod
    def _filter_percent(text: str):
        """Обработка процента"""

        if '%' in text:
            text = text.replace('%', ' процент')
        return text

    @staticmethod
    def _filter_volume(text: str):
        """
        Обработка неправильной нормализации слова "объем"
        """

        if 'объем' in text:
            text = text.replace('объем', 'объём')

        return text

    @staticmethod
    def frequency_destribution(word_list, quantity):
        """
        Частотное распределение слов в тексте и возврашает
        n=quantity наиболее популярных
        """

        freq_dist = FreqDist(word_list)
        most_popular_words = freq_dist.most_common(quantity)
        popular_words = [i[0] for i in most_popular_words]
        return popular_words
