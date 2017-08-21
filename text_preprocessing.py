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

from pymystem3 import Mystem

from model_manager import MODEL_CONFIG

from core.parsers.syn_parser import syn_tp
from core.parsers.num_parser import num_tp
from core.parsers.time_parser import time_tp

logging.getLogger("pymorphy2").setLevel(logging.ERROR)


@lru_cache(maxsize=16384)  # на самом деле, 8192 почти достаточно
def lemmatize(s):
    lem = lemmatize.morph.lemmatize(s)
    return list(filter(lambda t: re.fullmatch(r'\W*', t) is None, lem))

lemmatize.morph = Mystem()  # Лемматизатор
lemmatize.morph.start()


class TextPreprocessing:
    """
    Класс для предварительной обработки текста
    """

    def __init__(self, request_id=None, log=True):
        self.request_id = request_id
        self.log = log
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
            parse_syns=MODEL_CONFIG["parser_syns_default"],
            parse_nums=MODEL_CONFIG["parser_nums_default"],
            parse_time=MODEL_CONFIG["parser_time_default"],
    ):
        """Метод для нормализации текста"""

        # TODO: обработка направильного спеллинга

        # Применение фильтров
        text = TextPreprocessing._filter_percent(text)
        text = TextPreprocessing._filter_underscore(text)
        text = TextPreprocessing._filter_yo(text)

        # Токенизируем и лемматизируем
        tokens = lemmatize(text)

        # Генерация одного большого парсера
        parser = None
        if parse_syns:
            parser += syn_tp
        if parse_nums:
            parser += num_tp
        if parse_time:
            parser += time_tp

        # Парсинг всего
        if parser is not None:
            tokens = parser(tokens)

        # Убираем цифры
        if delete_digits:
            tokens = filter(lambda t: not t.isdigit(), tokens)

        # Если вопросительные слова и другие частицы не должны быть
        # удалены из запроса, так как отражают его смысл
        stop_words = set(self.stop_words)
        if not delete_question_words:
            delete_stop_words_set = set(['кто', 'что', 'это', 'где', 'для', 'зачем', 'какой'])
            stop_words = stop_words - delete_stop_words_set

        # Убираем стоп-слова
        tokens = filter(lambda t: t not in stop_words, tokens)

        # Убираем повторяющиеся слова
        if delete_repeatings:
            tokens = list(set(tokens))

        normalized_request = ' '.join(tokens)

        if self.log:
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
    def _filter_yo(text: str):
        """
        Обработка неправильной нормализации слова "объем"
        """

        if 'ё' in text:
            text = text.replace('ё', 'е')

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
