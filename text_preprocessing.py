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

# этот импорт убирать нельзя, иначе полетит логгирование
import logs_helper  # pylint: disable=unused-import

logging.getLogger("pymorphy2").setLevel(logging.ERROR)

def mc_get(key): return MODEL_CONFIG[key] if key in MODEL_CONFIG else False

class TextPreprocessing(object):
    """
    Класс для предварительной обработки текста
    """

    default_params = {
        'delete_digits': mc_get("normalization_delete_digits_default"),
        'delete_question_words': mc_get("normalization_delete_question_words_default"),
        'delete_repeatings': mc_get("normalization_delete_repeatings_default"),
        'parse_syns': mc_get("parser_syns_default"),
        'parse_nums': mc_get("parser_nums_default"),
        'parse_time': mc_get("parser_time_default"),
    }

    default_use_pymystem = getattr(SETTINGS, 'USE_PYMYSTEM', False)

    language = 'russian'

    question_words = set('кто что это где для зачем какой'.split())

    default_stop_words = set(stopwords.words(language)).difference(
        'не такой сейчас'.split(),
        question_words
    ).union(
        'подсказать также иной да нет'.split()
    )

    def __init__(self, log=True, use_pymystem=None, **kwargs):
        self.log = log

        # TODO: что делать с вопросительными словами?
        # Базовый набор стоп-слов
        self.stop_words = TextPreprocessing.default_stop_words

        self.params = TextPreprocessing.default_params.copy()
        for param in kwargs:
            val = kwargs[param]
            if param in self.params and isinstance(val, bool):
                self.params[param] = val

        self.active_param_names =  [p for p in self.params if self.params[p]]

        if use_pymystem is not None:
            self.use_pymystem = bool(use_pymystem)
        else:
            self.use_pymystem = TextPreprocessing.default_use_pymystem

        if self.use_pymystem:
            self.lemmatize = TextPreprocessing._pymystem_lem
            TextPreprocessing.mystem.start()
            self.lemmatizer_name = 'pymystem'
        else:
            self.lemmatize = TextPreprocessing._pymorphy_lem
            self.lemmatizer_name = 'pymorphy/nltk'

        self.tonita_parser = TextPreprocessing._make_tonita_parser(
            self.parse_syns,
            self.parse_nums,
            self.parse_time,
        )

        if self.log:
            logging.info(
                'Предобработка текста ведётся через {}; активные фильтры - {}'.format(
                    self.lemmatizer_name,
                    ', '.join(self.active_param_names)
                )
            )


    def __getattr__(self, attr):
        res = self.params.get(attr, None)
        if res is not None:
            return res
        raise AttributeError


    def normalize(self, text, request_id=None):
        """Метод для нормализации текста"""

        # TODO: обработка направильного спеллинга

        # Применение фильтров
        text = TextPreprocessing._filter_percent(text)

        # Токенизируем и лемматизируем
        tokens = self.lemmatize(text)

        # Парсинг всего
        if self.tonita_parser is not None:
            tokens = self.tonita_parser(tokens)

        # Убираем цифры
        if self.delete_digits:
            tokens = filter(lambda t: not t.isdigit(), tokens)

        # Если вопросительные слова и другие частицы не должны быть
        # удалены из запроса, так как отражают его смысл
        if self.delete_question_words:
            stop_words = self.stop_words.union(TextPreprocessing.question_words)
        else:
            stop_words = self.stop_words

        # Убираем стоп-слова
        tokens = filter(lambda t: t not in stop_words, tokens)

        # Убираем повторяющиеся слова
        if self.delete_repeatings:
            tokens = list(set(tokens))

        normalized_request = ' '.join(tokens)

        if self.log:
            logging.info(
                "Query_ID: {}\tMessage: Запрос после нормализации: {}".format(
                    request_id,
                    normalized_request
                )
            )

        return normalized_request

    __call__ = normalize

    _noword_re = re.compile(r'[_\W]*')

    @staticmethod
    def _filter_words(words: list):
        return filter(lambda t: TextPreprocessing._noword_re.fullmatch(t) is None, words)

    mystem = Mystem()

    @staticmethod
    def _pymystem_lem(text: str):
        return list(TextPreprocessing._filter_words(
            TextPreprocessing.mystem.lemmatize(text)
        ))

    morph = MorphAnalyzer()
    _stripper_re = re.compile(r'(^)?[_\W]*(?(1)|$)')

    @staticmethod
    @lru_cache(maxsize=16384)
    def _pymorphy_normal(word: str):
        word = TextPreprocessing._stripper_re.sub('', word)
        res = TextPreprocessing.morph.parse(word)[0].normal_form
        if 'ё' in res:
            res = res.replace('ё', 'е')
        return res

    @staticmethod
    def _pymorphy_lem(text: str):
        return list(map(
            TextPreprocessing._pymorphy_normal,
            TextPreprocessing._filter_words(
                word_tokenize(TextPreprocessing._filter_underscore(text))
            )
        ))

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
            text = text.replace('%', ' процент ')
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
