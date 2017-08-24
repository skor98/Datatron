#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Работа с текстом: нормализация, частотное распределение
"""

from functools import lru_cache
import logging
import logs_helper  # pylint: disable=unused-import
from model_manager import MODEL_CONFIG
from nlp import nlp_utils
from nlp.parsers.num_parser import num_tp
from nlp.parsers.syn_parser import syn_tp
from nlp.parsers.time_parser import time_tp
from nltk import FreqDist
from nltk.corpus import stopwords
from pymorphy2 import MorphAnalyzer
import uuid


# этот импорт убирать нельзя, иначе полетит логгирование
logging.getLogger("pymorphy2").setLevel(logging.ERROR)

def _mc_get(key): return MODEL_CONFIG[key] if key in MODEL_CONFIG else False

class TextPreprocessing(object):
    """
    Класс для предварительной обработки текста
    """

    default_params = {
        'delete_digits': _mc_get("normalization_delete_digits_default"),
        'delete_question_words': _mc_get("normalization_delete_question_words_default"),
        'delete_repeatings': _mc_get("normalization_delete_repeatings_default"),
        'parse_syns': _mc_get("parser_syns_default"),
        'parse_nums': _mc_get("parser_nums_default"),
        'parse_time': _mc_get("parser_time_default"),
    }


    language = 'russian'

    question_words = set('кто что это где для зачем какой'.split())

    default_stop_words = set(stopwords.words(language)).difference(
        'не такой сейчас'.split(),
        question_words
    ).union(
        'подсказать также иной да нет'.split()
    )


    def __init__(self, log=True, label='NULL', **kwargs):
        self.log = log

        self.label = label.upper()
        self.uid = str(uuid.uuid4()).split('-')[0]

        self.stop_words = TextPreprocessing.default_stop_words

        self.params = TextPreprocessing.default_params.copy()
        for param in kwargs:
            val = kwargs[param]
            if param in self.params and isinstance(val, bool):
                self.params[param] = val

        self.lemmatize = TextPreprocessing._pymorphy_lem
        self.lemmatizer_name = 'pymorphy/nltk'

        if self.log:
            logging.info(
                self.setup_str.replace('] П', '] Препроцессор создан, п')
            )


    def normalize(self, text, request_id='<NoID>'):
        """Метод для нормализации текста"""

        # TODO: обработка направильного спеллинга
        
        # Убираем плюсы-ударения
        if '\\+' in text:
            text = text.replace('\\+', '')

        # Фильтруем важные символы
        text = TextPreprocessing._filter_symbols(text)

        # Токенизируем и лемматизируем
        tokens = self.lemmatize(text)

        # Парсинг всего
        if self.combined_parser is not None:
            tokens = self.combined_parser(tokens)

        # Убираем цифры
        if self.delete_digits:
            tokens = filter(lambda t: not t.isdigit(), tokens)

        # Если вопросительные слова и другие частицы не должны быть
        # удалены из запроса, так как отражают его смысл
        if self.delete_question_words:
            stop_words = self.stop_words.union(self.question_words)
        else:
            stop_words = self.stop_words

        # Убираем стоп-слова
        tokens = filter(lambda t: t not in stop_words, tokens)

        # Убираем повторяющиеся слова
        if self.delete_repeatings:
            tokens = [t for n, t in enumerate(tokens) if t not in tokens[:n]]

        normalized_request = ' '.join(tokens)

        if self.log:
            logging.info(
                "Query_ID: {}\tMessage: [TextPP #{}] Запрос после нормализации: {}".format(
                    request_id,
                    self.uid,
                    normalized_request
                )
            )

        return normalized_request


    __call__ = normalize



    @property
    def combined_parser(self):
        return TextPreprocessing._make_tonita_parser(
            self.parse_syns,
            self.parse_nums,
            self.parse_time,
        )


    @property
    def u_name(self):
        return '#{}-{}'.format(self.label, self.uid)


    @property
    def active_params(self):
        return tuple([p for p in self.params if self.params[p]])


    @property
    def setup_str(self):
        af_str = 'дополнительные фильтры неактивны'
        if self.active_params:
            af_str = 'активные фильтры — {}'.format(', '.join(self.active_params))
        return '[TextPP {}] Параметры: NLP ведётся через {}; {}'.format(
            self.u_name,
            self.lemmatizer_name,
            af_str
        )


    def __getattr__(self, attr):
        res = self.params.get(attr, None)
        if res is not None:
            return res
        raise AttributeError


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
        return list(map(
            TextPreprocessing._pymorphy_normal,
            nlp_utils.advanced_tokenizer(text, False, False)
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
    def _filter_symbols(text: str):
        """Обработка символов, несущих смысловую нагрузку"""
        symbols = {
            '%': 'процент',
            '$': 'доллар',
            '€': 'евро',
            '£': 'фунт стерлинглв',
            '₽': 'рубль',
        }
        for symb, repl in symbols.items():
            if symb in text:
                text = text.replace(symb, ' {} '.format(repl))
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
