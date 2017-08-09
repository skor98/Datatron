#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Содержит в себе всё связанное с классификацией кубов с использованием ML
* Загрузка модели
* Запуск модели
* Обучение модели
* Выбор оптимальной модели
"""
import os
import re
from copy import deepcopy
from collections import Counter

from sklearn.externals import joblib

from nltk.corpus import stopwords

from text_preprocessing import get_normal_form
from manual_testing import get_test_files
from config import TEST_PATH_CUBE, DATA_PATH

STOP_WORDS = set(stopwords.words("russian"))
STOP_WORDS.update(set("также иной да нет -".split()))

WORDS_RE = re.compile("[а-яёА-ЯЁ]+")  # Регулярное выражение для выбора слов

class CubeClassifier():
    """
    Класс, который обеспечивает взаимодействие с ML-trained моделью
    По умолчанию загружается из файлов с моделью
    """

    def __init__(self, path=DATA_PATH, params=None):
        """
        иниицилизация либо по пути,
        либо по params:
        {
            'clf': классификатор,
            'back_index': отображение индекса куба на его имя
            'words': отображение слов на индекс в векторе
            'scaler': препроцессов scikit-learn
        }
        """
        if params not is None:
            self._clf = deepcopy(params["clf"])
            deepcopy(params["back_index"])
            deepcopy(params["words"])

    def predict(self):
        """
        scikit-learn compatible вызов

        """
        pass

    def get_ind_to_cubes(self):
        """Явно возвращает отображение от индексов к именам кубов"""
        return self.

    def get_model(self):
        """Явно возвращает используемую модель"""
        return self._clf

    def _get_scaler(self):
        """Возвращает используемый препроцессор scikit-learn"""

def selectBestModel():
    """
    Выполняет поиск наилучшей модели и возвращает её параметры.
    Может долго работать!
    """

def trainModel():
    """
    Возвращает готовую модель. Тип модели выбирается из ModelManager'а
    """
    X, Y

def _prepare_test_data(data):
    """
    Принимает на вход [(ТОКЕНЫ1,КУБ_1),(ТОКЕНЫ2,КУБ_2)]
    и возвращает numpy массив, Y=[КУБ1, КУБ2,...] и отображение фильтрованных слов
    Каждая строка этого массива строится так:
    1. Строится пустой массив из нулей, размеров во все фильтрованные слов
    2. Как только встречается фильтрованное слово в токенах, то соотв. элемент инкементируется
    """

    all_freqs = Counter()
    for line in data:
        for word in line[0]:
            all_freqs[word] += 1

    logging("Всего {} слова. Из них значимых {}".format(
        len(all_freqs),
        len(list(filter(
            lambda x: all_freqs[x] >= 3,
            all_freqs.keys()
        )))
    ))

    # Отображение фильтрованных слов в индексы
    WordIndex = {}
    for ind, word in enumerate(filter(lambda x: all_freqs[x] >= 3, all_freqs)):
        WordIndex[word] = ind

    X = np.zeros((len(data),len(WordIndex)))
    Y = np.zeros(len(data))

    for ind, line in enumerate(data):
        req_words = line[0]
        for word in req_words:
            if word not in WordIndex:
                continue
            X[ind,WordIndex[word]] += 1
        Y[ind] = line[1]

    return X, Y, WordIndex


def _get_tests_data():
    """
    Читает тесты по кубам и возвращает массив вида
    [(ТОКЕНЫ1,КУБ_1),(ТОКЕНЫ2,КУБ_2)]
    и словарь соответствия между числами КУБ1, КУБ2, ... и реальным названием куба
    То есть по списку токенов и кубу на каждый пример
    """

    # регулярное выражение для извлечения куба из MDX
    CUBE_RE = re.compile(r'(?<=FROM \[)\w*')

    res = []
    CubesMap = {}
    for test_path in get_test_files(TEST_PATH_CUBE, "cubes_test"):
        with open(test_path, 'r', encoding='utf-8') as file_in:
            for idx, line in enumerate(file_in):
                line = line.strip()
                if not line:
                    continue

                if line.startswith('*'):
                    continue

                req, answer = line.split(':')
                answer = CUBE_RE.search(answer).group()

                if not answer in CubesMap:
                    if not CubesMap:
                        CubesMap[answer] = 0
                    else:
                        CubesMap[answer] = max(CubesMap.values()) + 1

                answer = CubesMap[answer]
                req = _preprocess(req)
                res.append((req, answer))
    return tuple(res), CubesMap

def _preprocess(s: str):
    """Возвращает массив токенов по строке"""
    return tuple(map(
        lambda x: get_normal_form(x),
        filter(
            lambda x: x not in STOP_WORDS,
            WORDS_RE.findall(s.lower())
        )
    ))
