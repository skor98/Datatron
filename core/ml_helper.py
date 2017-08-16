#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Содержит в себе всё связанное с ML, что можно переиспользовать:
1. Загрузка и предобработка данных
2. Выбор и тестирование моделей
3. Тренировка моделей.
4. Слой для привязки к более высокми уровням
"""

import os
import re
import json
import logging
import pickle
from collections import Counter
from copy import deepcopy

from peewee import fn

from nltk.corpus import stopwords

import numpy as np

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, log_loss, classification_report
from sklearn.model_selection import KFold, ParameterGrid
from sklearn.svm import SVC

from kb.kb_db_creation import Member
from text_preprocessing import get_normal_form
from config import DATA_PATH
from model_manager import MODEL_CONFIG, save_default_model
import logs_helper

STOP_WORDS = set(stopwords.words("russian"))
STOP_WORDS.update(set("подсказать также иной да нет -".split()))

WORDS_RE = re.compile("[а-яёА-ЯЁ]+")  # Регулярное выражение для выбора слов
YEARS_RE = re.compile(r"\s(\d\d(\d\d)?)\s")
WORDS_NO_PROCESS = {"текущийгод", "нетекущийгод"}


class BaseTextClassifier():
    """
    Базовый класс для создания текстовых классификаторов.
    Способен обеспечить базовую логику полностью.
    Наследникам желательно стать Синглтонами.
    Необходимо переопределить префикс для сохранения в настройках
    """
    KFOLD_PARTS = 10
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
            self._ind_to_class = deepcopy(params["ind_to_class"])
            self._words_to_ind = deepcopy(params["words_to_ind"])

    def predict(self, req: str):
        """Возвращает имя куба по запросу-строке"""
        preprocessed = self._preprocess_query(req)
        res = self._ind_to_class[self._clf.predict(preprocessed)[0]]
        return res

    def predict_proba(self, req):
        """
        Возвращает по запросу значения:
        (ИМЯ_КЛАССА_1, вероятность_1), (ИМЯ_КЛАССА_2, вероятность_2), ...

        Гарантируется, что вероятность_1 >= вероятность_2 >= ..
        """
        res = self._clf.predict_proba(self._preprocess_query(req))[0]

        # (ИНДЕКС_КУБА, вероятность) -> сортируем -> (ИМЯ_КУБА, вероятность)
        return map(lambda x: (self._ind_to_class[x[0]], x[1]),
            sorted(
                list(enumerate(res.tolist())),
                key=lambda x: x[1],
                reverse=True
            )
        )

    def train(self):
        """Полностью инкапсулирует обучение модели"""
        data, self._ind_to_class = self._get_tests_data()
        X, Y, self._words_to_ind, self._scaler = _prepare_test_data(data)
        self._clf = _train_model(X, Y, self._get_config_prefix())

    def load(self):
        """Загружает модель из предопределённого пути"""
        self._load(self._get_model_path())

    def save(self):
        """Сохраняет модель по предопределённому пути"""
        self._save(self._get_model_path())

    def _preprocess_query(self, req):
        """Предобрабатывает запрос так, чтобы его уже можно было отправлять в классификатор"""
        X = np.zeros((1, len(self._words_to_ind)))
        req_words = preprocess(req)
        for word in req_words:
            if word not in self._words_to_ind:
                continue
            X[0, self._words_to_ind[word]] += 1
        X = self._scaler.transform(X)
        return X

    def _load(self, path: str):
        """Загружает модель. Не должен вызываться явно."""
        with open(os.path.join(path, self._get_classifier_name()), "rb") as f:
            self._clf = pickle.load(f)

        with open(os.path.join(path, self._get_scaler_name()), "rb") as f:
            self._scaler = pickle.load(f)

        with open(os.path.join(path, self._get_words_to_ind_name()), "r") as f:
            self._words_to_ind = json.load(f)

        with open(os.path.join(path, self._get_ind_to_class_name()), "r") as f:
            self._ind_to_class = json.load(f)
        # надо сделать ключи числами:
        self._ind_to_class = {int(i): self._ind_to_class[i] for i in self._ind_to_class}

    def _save(self, path: str):
        """Сохраняет модель. Не должен вызываться явно."""
        with open(os.path.join(path, self._get_classifier_name()), "wb") as f:
            pickle.dump(self._clf, f)

        with open(os.path.join(path, self._get_scaler_name()), "wb") as f:
            pickle.dump(self._scaler, f)

        with open(os.path.join(path, self._get_words_to_ind_name()), "w") as f:
            json.dump(self._words_to_ind, f, indent=4, ensure_ascii=False, sort_keys=True)

        with open(os.path.join(path, self._get_ind_to_class_name()), "w") as f:
            json.dump(self._ind_to_class, f, indent=4, ensure_ascii=False)
        logging.info("Классификатор кубов сохранён в папке {}".format(path))

    def _get_model_path(self):
        return DATA_PATH

    def _get_path_prefix(self):
        """Возвращает префикс для файлов с моделью. Нужно переопределить"""
        raise NotImplementedError

    def _get_classifier_name(self):
        """Имя файла с моделью scikit-learn"""
        return self._get_path_prefix() + "mdl.pkl"

    def _get_scaler_name(self):
        """Имя файла с нормализотором scikit-learn"""
        return self._get_path_prefix() + "scaler.pkl"

    def _get_words_to_ind_name(self):
        """Отображение исходных слов в их индексы в векторе для передачи в модель"""
        return self._get_path_prefix() + "words_map.json"

    def _get_ind_to_class_name(self):
        """Преобразование индексов классов в их имена"""
        return self._get_path_prefix() + "ind_map.json"

    def _get_tests_data(self):
        """
        Читает тесты  и возвращает массив вида
        [(ТОКЕНЫ1,КЛАСС_1),(ТОКЕНЫ2,КЛАСС_2)]
        и словарь соответствия между числами КЛАСС_1, КЛАСС_2, ... и реальным названием класса
        То есть по списку токенов и классу на каждый пример
        Должен быть переопределён
        """
        raise NotImplementedError

    def _get_config_prefix(self):
        """
        Возвращает префикс для сохранения в настройках.
        Должен быть переопределён
        """
        raise NotImplementedError


def select_best_model(data, ind_to_class, kfolds: int, config_prefix: str):
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
            })),
            "SVM": (SVC, ParameterGrid({
                "C": [1, 4, 10],
                "probability": [True],
                "decision_function_shape": ["ovr"]
            })),
        }
        for clf_name in classifiers:
            for params in classifiers[clf_name][1]:
                yield clf_name, params, classifiers[clf_name][0](**params)

    # главный параметр, отвечающий за компромисс между точностью и временем
    # работы при неизменном наборе классификаторов
    # время работы ~ KFOLD_PARTS ^ (3/2)
    X, Y, words_to_ind, scaler = _prepare_test_data(data)

    logging.info("Используется {} Fold'ов".format(kfolds))
    kfolds_generator = KFold(n_splits=kfolds, shuffle=True, random_state=42)

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
        y_test_pred_proba = np.zeros((0, len(ind_to_class)))
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
        target_names=tuple(ind_to_class.values())
    ))

    logging.info("Сохраняю новые параметры {}-{}".format(best_clf_name, best_params))
    if best_clf_name == "logistic":
        MODEL_CONFIG["{}_type".format(config_prefix)] = "LogisticRegression"
        MODEL_CONFIG["{}_reg".format(config_prefix)] = best_params["C"]
    elif best_clf_name == "GB":
        MODEL_CONFIG["{}_type".format(config_prefix)] = "GradientBoosting"
        MODEL_CONFIG["{}_gb_estimators".format(config_prefix)] = best_params["n_estimators"]
        MODEL_CONFIG["{}_gb_learning_rate".format(config_prefix)] = best_params["learning_rate"]
        MODEL_CONFIG["{}_gb_max_depth".format(config_prefix)] = best_params["max_depth"]
    elif best_clf_name == "SVM":
        MODEL_CONFIG["{}_type".format(config_prefix)] = "SVM"
        MODEL_CONFIG["{}_reg".format(config_prefix)] = best_params["C"]
    else:
        raise Exception("Неизвестная модель {}".format(best_clf_name))

    save_default_model(MODEL_CONFIG)


@logs_helper.time_with_message("_train_model", "info")
def _train_model(X, Y, config_prefix):
    """
    Возвращает готовую модель по обучающей выборке.
    Тип модели выбирается из ModelManager'а
    Инкапсулирует чтение настроек и создание классов модели
    """

    model_type = MODEL_CONFIG["{}_type".format(config_prefix)]

    if model_type == "LogisticRegression":
        clf_reg = MODEL_CONFIG["{}_reg".format(config_prefix)]  # регуляризация
        clf = LogisticRegression(C=clf_reg, n_jobs=-1)
    elif model_type == "GradientBoosting":
        n_estimators = MODEL_CONFIG["{}_gb_estimators".format(config_prefix)]
        learning_rate = MODEL_CONFIG["{}_gb_learning_rate".format(config_prefix)]
        max_depth = MODEL_CONFIG["{}_gb_max_depth".format(config_prefix)]
        clf = GradientBoostingClassifier(
            n_estimators=n_estimators,
            learning_rate=learning_rate,
            max_depth=max_depth
        )
    elif model_type == "SVM":
        clf_reg = MODEL_CONFIG["{}_reg".format(config_prefix)]
        clf = SVC(
            C=clf_reg,
            probability=True,
            decision_function_shape="ovr"
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
    Принимает на вход [(ТОКЕНЫ1,КЛАСС_1),(ТОКЕНЫ2,КЛАСС_2)]
    и возвращает готовый фильтрованный numpy массив,
    Y=[КЛАСС1, КЛАСС2,...]
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
    words_to_ind = {}
    for ind, word in enumerate(filter(lambda x: all_freqs[x] >= 3, all_freqs)):
        words_to_ind[word] = ind

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

    X = np.zeros((len(filtered_data), len(words_to_ind)))
    Y = np.zeros(len(filtered_data))

    for ind, line in enumerate(filtered_data):
        req_words = line[0]
        for word in req_words:
            if word not in words_to_ind:
                continue
            X[ind, words_to_ind[word]] += 1
        Y[ind] = line[1]

    # предобраотка данных, полезна в любом случае
    # смещение и нормализация дисперсии
    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    return X, Y, words_to_ind, scaler

def get_folder_lines(test_path):
    """Генератор непустых строчек из файлов в указанной папке"""
    for file_name in os.listdir(test_path):
        with open(os.path.join(test_path, file_name), encoding='utf-8') as file_in:
            for line in file_in:
                line = line.strip()
                if not line:
                    continue
                yield line

def preprocess(s: str):
    """
    Возвращает массив токенов по строке
    Переопределение не предполагается, но возможно на уровне модуля
    """
    s = s.replace("2017", "текущийгод")
    s = s.replace("17", "текущийгод")
    s = YEARS_RE.sub(" нетекущийгод ", s + " ")
    res = set(map(
        lambda x: get_normal_form(x) if x not in WORDS_NO_PROCESS else x,
        filter(
            lambda x: x not in STOP_WORDS,
            WORDS_RE.findall(s.lower())
        )
    ))
    for terr in get_territories():
        if terr.issubset(res):
            res = res.difference(terr)
            res.add("члентерритория")
            break

    return tuple(res)

def get_territories():
    """Возвращает территории, которые хранятся в базе. Кешируется"""
    if get_territories.territories:
        return get_territories.territories

    terr_query = Member.select(
        Member.lem_caption,
        Member.lem_synonyms
    ).where(
        fn.Lower(fn.Substr(Member.cube_value, 1, 2)) == '08'
    )

    territories = []

    for territory in terr_query:
        if territory.lem_caption in ["неуказанный территория", "неуказанный наименование"]:
            continue
        territories.append(set(territory.lem_caption.split()))
        if territory.lem_synonyms:
            for synonym in territory.lem_synonyms.split():
                territories.append(set([synonym]))
    territories.append({"кабардино", "балкария"})
    territories.append({"хмао"})
    territories.append({"крымский"})
    territories.append({"крым"})
    territories.append({"кабардино", "балкарский", "республика"})

    territories = tuple(territories)

    get_territories.territories = territories

    return get_territories.territories

get_territories.territories = None
