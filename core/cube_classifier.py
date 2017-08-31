#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Специфическое для классификатора типов кубов
"""
import re
import logging

from config import TEST_PATH_CUBE, LOG_LEVEL
from core.ml_helper import BaseTextClassifier, get_folder_lines, preprocess, select_best_model
from core.support_library import get_pretty_feedback
import logs_helper


# pylint: disable=invalid-name
CONFIG_PREFIX = "model_cube_clf"


class CubeClassifier(BaseTextClassifier):
    """
    Класс, который обеспечивает взаимодействие с ML-trained моделью
    По умолчанию загружается из файлов с моделью Синглтон! Singleton!
    """

    __instance = None

    @staticmethod
    def inst(is_train=False, params=None):
        """Реализует Синглтон"""
        if CubeClassifier.__instance is None:
            CubeClassifier.__instance = CubeClassifier(is_train, params)
        return CubeClassifier.__instance

    def _get_path_prefix(self):
        """Возвращает префикс для файлов с моделью. Нужно переопределить"""
        return "cube_clf_"

    def _get_tests_data(self):
        return _get_cubes_tests_data()

    def _get_config_prefix(self):
        """
        Возвращает префикс для сохранения в настройках.
        Должен быть переопределён
        """
        return CONFIG_PREFIX


@logs_helper.time_with_message("_get_cubes_tests_data", "info")
def _get_cubes_tests_data():
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
    for line in get_folder_lines(TEST_PATH_CUBE):
        if line.startswith('*'):
            continue

        req, mdx_query = " ".join(line.split(':')[:-1]), line.split(':')[-1]
        answer = CUBE_RE.search(mdx_query).group()

        if answer not in CubesMap:
            if not CubesMap:
                CubesMap[answer] = 0
            else:
                CubesMap[answer] = max(CubesMap.values()) + 1

        answer = CubesMap[answer]
        req = preprocess(req)
        res.append((req, answer))

        # Добавим также красивый фидбек данного запроса
        try:
            # логгирование лучше выключить, иначе будет мусор
            logging.getLogger().setLevel(logging.ERROR)
            pretty_feedback = get_pretty_feedback(mdx_query)

            # Фидбек относится к тому же кубу, что и исходные данные, добавляем
            res.append((pretty_feedback, answer))
        except:
            logging.error("Не могу получить красивый фидбек по {}".format(mdx_query))
        finally:
            logging.getLogger().setLevel(logs_helper.string_to_log_level(LOG_LEVEL))
    BackCubesMap = {CubesMap[i]: i for i in CubesMap}
    return tuple(res), BackCubesMap


@logs_helper.time_with_message("train_and_save_cube_clf", "info")
def train_and_save_cube_clf():
    """Инкапсулирует создание и сохранение модели"""
    clf = CubeClassifier.inst(is_train=True)
    return clf


@logs_helper.time_with_message("select_best_cube_clf", "info", 60 * 60)
def select_best_cube_clf():
    data, ind_to_class = _get_cubes_tests_data()
    select_best_model(
        data,
        ind_to_class,
        kfolds=30,
        config_prefix=CONFIG_PREFIX
    )
