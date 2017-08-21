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
from pymorphy2 import MorphAnalyzer
from nltk import word_tokenize

from model_manager import MODEL_CONFIG

from core.parsers.syn_parser import syn_tp
from core.parsers.num_parser import num_tp
from core.parsers.time_parser import time_tp

from config import SETTINGS

logging.getLogger("pymorphy2").setLevel(logging.ERROR)


class TextPreprocessing(object):
    """
    Класс для предварительной обработки текста
    """
    
    delete_digits = MODEL_CONFIG["normalization_delete_digits_default"]
    delete_question_words = MODEL_CONFIG["normalization_delete_question_words_default"]
    delete_repeatings = MODEL_CONFIG["normalization_delete_repeatings_default"]
    parse_syns = MODEL_CONFIG["parser_syns_default"]
    parse_nums = MODEL_CONFIG["parser_nums_default"]
    parse_time = MODEL_CONFIG["parser_time_default"]
    use_pymystem = SETTINGS.USE_PYMYSTEM

    def __init__(self, log=True, **kwargs):
        self.log = log
        self.language = 'russian'

        # TODO: что делать с вопросительными словами?
        # Базовый набор стоп-слов
        self.stop_words = set(stopwords.words(self.language))
        self.stop_words -= {'не', 'такой'}
        self.stop_words.update(set("подсказать также иной да нет -".split()))
        
        for param in ('delete_digits', 'delete_question_words', 'delete_repeatings',
                      'parse_syns', 'parse_nums', 'parse_time', 'use_pymystem'):
            if param in kwargs:
                setattr(self, param, kwargs[param])
                
        if self.use_pymystem:
            self.lemmatize = TextPreprocessing._pymystem_lem
        else:
            self.lemmatize = TextPreprocessing._pymorphy_lem
        
        self._tonita_parser = TextPreprocessing._make_tonita_parser(
            self.parse_syns,
            self.parse_nums,
            self.parse_time,
        )

    def normalize(self, text, request_id=None):
        """Метод для нормализации текста"""

        # TODO: обработка направильного спеллинга

        # Применение фильтров
        text = TextPreprocessing._filter_percent(text)
        text = TextPreprocessing._filter_underscore(text)

        # Токенизируем и лемматизируем
        tokens = self.lemmatize(text)

        # Парсинг всего
        if self._tonita_parser is not None:
            tokens = self._tonita_parser(tokens)

        # Убираем цифры
        if self.delete_digits:
            tokens = filter(lambda t: not t.isdigit(), tokens)

        # Если вопросительные слова и другие частицы не должны быть
        # удалены из запроса, так как отражают его смысл
        stop_words = set(self.stop_words)
        if not self.delete_question_words:
            delete_stop_words_set = set(['кто', 'что', 'это', 'где', 'для', 'зачем', 'какой'])
            stop_words = stop_words - delete_stop_words_set

        # Убираем стоп-слова
        tokens = filter(lambda t: t not in stop_words, tokens)

        # Убираем повторяющиеся слова
        if self.delete_repeatings:
            tokens = list(set(tokens))

        normalized_request = ' '.join(tokens)

        if self.log:
            logging.info(
                "Query_ID: {}\tMessage: Запрос после нормализации: {}".format(
                    request_id, normalized_request
                )
            )

        return normalized_request
    
    def __call__(self, text, request_id=None):
        return self.normalize(text, request_id)

    mystem = Mystem()
    mystem.start()
    
    @staticmethod
    def _filter_words(wordlist: list):
        return filter(lambda t: re.fullmatch(r'\W*', t) is None, wordlist)

    @staticmethod
    def _pymystem_lem(text: str):
        return TextPreprocessing._filter_words(
            TextPreprocessing.mystem.lemmatize(text)
        )

    morph = MorphAnalyzer()
    
    @staticmethod
    @lru_cache(maxsize=16384)
    def _pymorphy_normal(word: str):
        res = TextPreprocessing.morph.parse(word)[0].normal_form
        if 'ё' in res:
            res = res.replace('ё', 'е')
        return res

    @staticmethod
    def _pymorphy_lem(text: str):
        return TextPreprocessing._filter_words(
            map(
                TextPreprocessing._pymorphy_normal,
                word_tokenize(text)
            )
        )
    
    @staticmethod
    @lru_cache(maxsize=64)
    def _make_tonita_parser(
        parse_syns,
        parse_nums,
        parse_time,
    ):
        parser = None
        if parse_syns:
            parser += syn_tp
        if parse_nums:
            parser += num_tp
        if parse_time:
            parser += time_tp
        return parser

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
    def frequency_destribution(word_list, quantity):
        """
        Частотное распределение слов в тексте и возврашает
        n=quantity наиболее популярных
        """

        freq_dist = FreqDist(word_list)
        most_popular_words = freq_dist.most_common(quantity)
        popular_words = [i[0] for i in most_popular_words]
        return popular_words
