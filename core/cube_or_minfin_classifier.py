#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Специфическое для классификатора куб/минфин
"""
import logging

from config import TEST_PATH_CUBE, TEST_PATH_MINFIN, LOG_LEVEL
from core.ml_helper import BaseTextClassifier, get_folder_lines, preprocess, select_best_model
from core.support_library import get_pretty_feedback
import logs_helper


# pylint: disable=invalid-name
CONFIG_PREFIX = "model_cube_or_minfin_clf"


class CubeOrMinfinClassifier(BaseTextClassifier):
    """
    Класс, который обеспечивает взаимодействие с ML-trained моделью
    По умолчанию загружается из файлов с моделью
    Синглтон! Singleton!
    """

    __instance = None

    @staticmethod
    def inst(is_train=False, params=None):
        """Реализует Синглтон"""
        if CubeOrMinfinClassifier.__instance is None:
            CubeOrMinfinClassifier.__instance = CubeOrMinfinClassifier(
                is_train, params)
        return CubeOrMinfinClassifier.__instance

    def _get_path_prefix(self):
        """Возвращает префикс для файлов с моделью. Нужно переопределить"""
        return "cube_or_minfin_clf_"

    def _get_tests_data(self):
        return _get_cube_or_minfin_tests_data()

    def _get_config_prefix(self):
        """
        Возвращает префикс для сохранения в настройках.
        Должен быть переопределён
        """
        return CONFIG_PREFIX


@logs_helper.time_with_message("_get_cube_or_minfin_tests_data", "info")
def _get_cube_or_minfin_tests_data():
    """
    Читает тесты по кубам и возвращает массив вида
    [(ТОКЕНЫ1,КУБ_1),(ТОКЕНЫ2,КУБ_2)]
    и словарь соответствия между числами КУБ1, КУБ2, ... и реальным названием куба
    То есть по списку токенов и кубу на каждый пример
    """

    IndToClassName = {0: "Cube", 1: "Minfin"}

    res = []
    for class_ind, test_path in [(0, TEST_PATH_CUBE), (1, TEST_PATH_MINFIN)]:
        for line in get_folder_lines(test_path):
            if line.startswith('*'):
                continue

            req = " ".join(line.split(':')[:-1])
            answer = class_ind

            req = req.lower()
            req = preprocess(req)
            res.append((req, answer))

            # Добавим также pretty_feedback:
            if class_ind == 0:
                mdx_query = line.split(':')[-1]
                try:
                    # логгирование лучше выключить, иначе будет мусор
                    logging.getLogger().setLevel(logging.ERROR)
                    pretty_feedback = get_pretty_feedback(mdx_query)

                    # Фидбек относится к тому же кубу, что и исходные данные, добавляем
                    res.append((pretty_feedback, answer))
                except:
                    logging.error(
                        "Не могу получить pretty_feedback: {}".format(mdx_query))
                finally:
                    logging.getLogger().setLevel(logs_helper.string_to_log_level(LOG_LEVEL))

    return tuple(res), IndToClassName


@logs_helper.time_with_message("train_and_save_cube_or_minfin_clf", "info")
def train_and_save_cube_or_minfin_clf():
    """Инкапсулирует создание и сохранение модели"""
    clf = CubeOrMinfinClassifier.inst(is_train=True)
    return clf


@logs_helper.time_with_message("select_best_cube_or_minfin_clf", "info", 60 * 60)
def select_best_cube_or_minfin_clf():
    data, ind_to_class = _get_cube_or_minfin_tests_data()
    select_best_model(
        data,
        ind_to_class,
        kfolds=8,
        config_prefix=CONFIG_PREFIX
    )
