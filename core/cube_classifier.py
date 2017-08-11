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
import json
from copy import deepcopy
from collections import Counter
import pickle
import logging

import numpy as np

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, log_loss, classification_report
from sklearn.model_selection import KFold, ParameterGrid

from nltk.corpus import stopwords

from text_preprocessing import get_normal_form
from config import TEST_PATH_CUBE, DATA_PATH
from model_manager import MODEL_CONFIG, save_default_model
import logs_helper
# pylint: disable=invalid-name

MODEL_PATH = DATA_PATH  # Положим там
MODEL_PREFIX = "cube_clf_"  # ставится перед началом файлов с моделью

CLASSIFIER_NAME = MODEL_PREFIX + "mdl.pkl"  # файл с самим классификатором
SCALER_NAME = MODEL_PREFIX + "scaler.pkl"  # препроцессор

WORDS_TO_IND_NAME = MODEL_PREFIX + "words_map.json"  # файл с выбранными словами
IND_TO_CUBE_NAME = MODEL_PREFIX + "cubes_map.json"  # преобразование индексов в имена кубов

STOP_WORDS = set(stopwords.words("russian"))
STOP_WORDS.update(set("подсказать также иной да нет -".split()))

WORDS_RE = re.compile("[а-яёА-ЯЁ]+")  # Регулярное выражение для выбора слов


class CubeClassifier():

    """
    Класс, который обеспечивает взаимодействие с ML-trained моделью
    По умолчанию загружается из файлов с моделью
    Синглтон! Singleton!
    """

    __instance = None

    @staticmethod
    def inst(is_train=False, params=None):
        """Реализует Синглтон"""
        if CubeClassifier.__instance is None:
            CubeClassifier.__instance = CubeClassifier(is_train, params)
        return CubeClassifier.__instance

    def __init__(self, is_train, params):
        """
        Если is_train==True, то тренировка модели, а потом её сохранение
        иниицилизация либо из файла по умолчанию
        либо по params:
        {
            'clf': классификатор,
            'scaler': препроцессор scikit-learn,
            'ind_to_cube': отображение индекса куба на его имя
            'words_to_ind': отображение слов на индекс в векторе
        }
        """
        if is_train:
            self.train()
            self.save()
            return

        if params is None:
            self.load()
        else:
            self._clf = deepcopy(params["clf"])
            self._scaler = deepcopy(params["scaler"])
            self._ind_to_cube = deepcopy(params["ind_to_cube"])
            self._words_to_ind = deepcopy(params["words_to_ind"])

    def predict(self, req: str):
        """Возвращает имя куба по запросу-строке"""
        preprocessed = self._preprocess_query(req)
        res = self._ind_to_cube[self._clf.predict(preprocessed)[0]]
        return res

    def predict_proba(self, req):
        """
        Возвращает по запросу значения:
        (ИМЯ_КУБА_1, вероятность_1), (ИМЯ_КУБА_2, вероятность_2), ...

        Гарантируется, что вероятность_1 >= вероятность_2 >= ..
        """
        res = self._clf.predict_proba(self._preprocess_query(req))[0]

        # (ИНДЕКС_КУБА, вероятность) -> сортируем -> (ИМЯ_КУБА, вероятность)
        return map(lambda x: (self._ind_to_cube[x[0]], x[1]),
            sorted(
                list(enumerate(res.tolist())),
                key=lambda x: x[1],
                reverse=True
            )
        )

    def train(self):
        """Полностью инкапсулирует обучение модели"""
        data, self._ind_to_cube = _get_tests_data()
        X, Y, self._words_to_ind, self._scaler = _prepare_test_data(data)
        self._clf = _train_model(X, Y)

    def load(self):
        """Загружает модель из предопределённого пути"""
        self._load(MODEL_PATH)

    def save(self):
        """Сохраняет модель по предопределённому пути"""
        self._save(MODEL_PATH)

    def _preprocess_query(self, req):
        """Предобрабатывает запрос так, чтобы его уже можно было отправлять в классификатор"""
        X = np.zeros((1, len(self._words_to_ind)))
        req_words = _preprocess(req)
        for word in req_words:
            if word not in self._words_to_ind:
                continue
            X[0, self._words_to_ind[word]] += 1
        X = self._scaler.transform(X)
        return X

    @logs_helper.time_with_message("CubeClassifier._load", "info")
    def _load(self, path: str):
        """Загружает модель. Не должен вызываться явно."""
        with open(os.path.join(path, CLASSIFIER_NAME), "rb") as f:
            self._clf = pickle.load(f)

        with open(os.path.join(path, SCALER_NAME), "rb") as f:
            self._scaler = pickle.load(f)

        with open(os.path.join(path, WORDS_TO_IND_NAME), "r") as f:
            self._words_to_ind = json.load(f)

        with open(os.path.join(path, IND_TO_CUBE_NAME), "r") as f:
            self._ind_to_cube = json.load(f)
        # надо сделать ключи числами:
        self._ind_to_cube = {int(i): self._ind_to_cube[i] for i in self._ind_to_cube}

    @logs_helper.time_with_message("CubeClassifier._save", "info")
    def _save(self, path: str):
        """Сохраняет модель. Не должен вызываться явно."""
        with open(os.path.join(path, CLASSIFIER_NAME), "wb") as f:
            pickle.dump(self._clf, f)

        with open(os.path.join(path, SCALER_NAME), "wb") as f:
            pickle.dump(self._scaler, f)

        with open(os.path.join(path, WORDS_TO_IND_NAME), "w") as f:
            json.dump(self._words_to_ind, f, indent=4, ensure_ascii=False, sort_keys=True)

        with open(os.path.join(path, IND_TO_CUBE_NAME), "w") as f:
            json.dump(self._ind_to_cube, f, indent=4, ensure_ascii=False)
        logging.info("Классификатор кубов сохранён в папке {}".format(path))


@logs_helper.time_with_message("select_best_model", "info", 60 * 60)
def select_best_model():
    """
    Выполняет поиск наилучшей модели и сохраняет её параметры.
    Может долго работать!
    Пока гарантируются, что он не будет работать больше часа
    """

    def get_classifier():
        """
        Генератор моделей для перебора.
        Нужен для инкапсуляции выбора моделей и последовательной их генерации
        """
        classifiers = {
            "logistic": (LogisticRegression, ParameterGrid({
                "C": [1, 4, 10],
                "n_jobs": [-1]
            })),
            "GB": (GradientBoostingClassifier, ParameterGrid({
                "learning_rate": [0.3, 0.1],
                "n_estimators":  [100, 240, 400],
                "max_depth": [1, 2, 3]
            }))
        }
        for clf_name in classifiers:
            for params in classifiers[clf_name][1]:
                yield clf_name, params, classifiers[clf_name][0](**params)

    # главный параметр, отвечающий за компромисс между точностью и временем
    # работы при неизменном наборе классификаторов
    # время работы ~ KFOLD_PARTS ^ (3/2)
    KFOLD_PARTS = 40

    data, ind_to_cube = _get_tests_data()
    X, Y, words_to_ind, scaler = _prepare_test_data(data)

    logging.info("Используется {} Fold'ов".format(KFOLD_PARTS))
    kfolds_generator = KFold(n_splits=KFOLD_PARTS, shuffle=True, random_state=42)

    best_clf_name = None
    best_params = None
    best_log_loss = 100  # маленький хорошо, большой плохо
    best_y_test_pred = None
    best_y_test_pred_proba = None
    best_y_test_real = None

    for clf_name, params, clf in get_classifier():
        y_train_pred = np.array([])
        y_train_real = np.array([])

        y_test_pred = np.array([])
        y_test_pred_proba = np.zeros((0, len(ind_to_cube)))
        y_test_real = np.array([])

        for train_index, test_index in kfolds_generator.split(X):
            X_train = X[train_index]
            Y_train = Y[train_index]

            X_test = X[test_index]
            Y_test = Y[test_index]

            clf.fit(X_train, Y_train)

            y_train_pred = np.concatenate((y_train_pred, clf.predict(X_train)))
            y_train_real = np.concatenate((y_train_real, Y_train))

            y_test_pred = np.concatenate((y_test_pred, clf.predict(X_test)))
            y_test_pred_proba = np.concatenate((y_test_pred_proba, clf.predict_proba(X_test)))
            y_test_real = np.concatenate((y_test_real, Y_test))

        if log_loss(y_test_real, y_test_pred_proba) < best_log_loss:
            best_clf_name = clf_name
            best_params = params
            best_log_loss = log_loss(y_test_real, y_test_pred_proba)
            best_y_test_pred = y_test_pred
            best_y_test_pred_proba = y_test_pred_proba
            best_y_test_real = y_test_real

        print("{} {} train_acc: {:.3f} test_acc: {:.3f} test_log_loss {:.3f}".format(
            clf_name,
            params,
            accuracy_score(y_train_pred, y_train_real),
            accuracy_score(y_test_pred, y_test_real),
            log_loss(y_test_real, y_test_pred_proba)
        ))
    print("Лучший {} {} с acc: {:.3f} и log_loss: {:.3f}".format(
        best_clf_name,
        best_params,
        accuracy_score(y_test_real, best_y_test_pred),
        log_loss(y_test_real, best_y_test_pred_proba)
    ))

    print(classification_report(
        best_y_test_real,
        best_y_test_pred,
        target_names=tuple(ind_to_cube.values())
    ))

    logging.info("Сохраняю новые параметры {}-{}".format(best_clf_name, best_params))
    if best_clf_name == "logistic":
        MODEL_CONFIG["model_cube_clf_type"] = "LogisticRegression"
        MODEL_CONFIG["model_cube_clf_lr_reg"] = best_params["C"]
    elif best_clf_name == "GB":
        MODEL_CONFIG["model_cube_clf_type"] = "GradientBoosting"
        MODEL_CONFIG["model_cube_clf_gb_estimators"] = best_params["n_estimators"]
        MODEL_CONFIG["model_cube_clf_gb_learning_rate"] = best_params["learning_rate"]
        MODEL_CONFIG["model_cube_clf_gb_max_depth"] = best_params["max_depth"]
    else:
        raise Exception("Неизвестная модель {}".format(best_clf_name))

    save_default_model(MODEL_CONFIG)


@logs_helper.time_with_message("trainAndSaveModel", "info")
def train_and_save_model():
    """Инкапсулирует создание и сохранение модели"""
    clf = CubeClassifier.inst(is_train=True)
    return clf


@logs_helper.time_with_message("_train_model", "info")
def _train_model(X, Y):
    """
    Возвращает готовую модель по обучающей выборке.
    Тип модели выбирается из ModelManager'а
    Инкапсулирует чтение настроек и создание классов модели
    """

    model_type = MODEL_CONFIG["model_cube_clf_type"]

    if model_type == "LogisticRegression":
        clf_reg = MODEL_CONFIG["model_cube_clf_lr_reg"]  # регуляризация
        clf = LogisticRegression(C=clf_reg, n_jobs=-1)
    elif model_type == "GradientBoosting":
        n_estimators = MODEL_CONFIG["model_cube_clf_gb_estimators"]
        learning_rate = MODEL_CONFIG["model_cube_clf_gb_learning_rate"]
        max_depth = MODEL_CONFIG["model_cube_clf_gb_max_depth"]
        clf = GradientBoostingClassifier(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth
        )
    else:
        err_msg = "Неизвестный тип модели {}".format(model_type)
        logging.error(err_msg)
        raise Exception(err_msg)

    clf.fit(X, Y)
    return clf


@logs_helper.time_with_message("_prepare_test_data", "info")
def _prepare_test_data(data):
    """
    Принимает на вход [(ТОКЕНЫ1,КУБ_1),(ТОКЕНЫ2,КУБ_2)]
    и возвращает готовый фильтрованный numpy массив,
    Y=[КУБ1, КУБ2,...]
    отображение фильтрованных слов в индексы массива
    и Scaler
    Каждая строка этого массива строится так:
    1. Строится пустой массив из нулей, размеров во все фильтрованные слов
    2. Как только встречается фильтрованное слово в токенах, то соотв. элемент инкементируется
    """

    all_freqs = Counter()
    for line in data:
        for word in line[0]:
            all_freqs[word] += 1

    logging.info("Всего {} слова. Из них значимых {}".format(
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

    # вот тут могло получиться так, что какие-то два примера стали одинаковыми
    # месяц март -> месяц <- месяц май
    # это плохо для тестирования производительности и надо отсеять такие примеры

    # токены отсортированные и преобразованные к строке
    # (январь, месяц, быть) -> (быть, месяц, январь) -> бытьмесяцянварь
    used_queries = set()
    filtered_data = []

    for line in data:
        stringed_example = "".join(sorted(line[0]))
        if stringed_example in used_queries:
            continue
        used_queries.add(stringed_example)
        filtered_data.append(line)

    logging.info("Отфильтровали {} примеров, осталось {}".format(
        len(data) - len(filtered_data),
        len(filtered_data)
    ))

    X = np.zeros((len(filtered_data), len(WordIndex)))
    Y = np.zeros(len(filtered_data))

    for ind, line in enumerate(filtered_data):
        req_words = line[0]
        for word in req_words:
            if word not in WordIndex:
                continue
            X[ind, WordIndex[word]] += 1
        Y[ind] = line[1]

    # предобраотка данных, полезна в любом случае
    # смещение и нормализация дисперсии
    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    return X, Y, WordIndex, scaler


@logs_helper.time_with_message("_get_tests_data", "info")
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
    for test_path in _get_folder_files(TEST_PATH_CUBE):
        with open(test_path, 'r', encoding='utf-8') as file_in:
            for line in file_in:
                line = line.strip()
                if not line:
                    continue

                if line.startswith('*'):
                    continue

                req, answer = line.split(':')
                answer = CUBE_RE.search(answer).group()

                if answer not in CubesMap:
                    if not CubesMap:
                        CubesMap[answer] = 0
                    else:
                        CubesMap[answer] = max(CubesMap.values()) + 1

                answer = CubesMap[answer]
                req = _preprocess(req)
                res.append((req, answer))
    BackCubesMap = {CubesMap[i]: i for i in CubesMap}
    return tuple(res), BackCubesMap


def _preprocess(s: str):
    """Возвращает массив токенов по строке"""
    return tuple(map(
        get_normal_form,
        filter(
            lambda x: x not in STOP_WORDS,
            WORDS_RE.findall(s.lower())
        )
    ))


def _get_folder_files(test_path):
    """Генератор путей к файлам в указанной папке"""
    for file_name in os.listdir(test_path):
        yield os.path.join(test_path, file_name)
