#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Интерфейс для хранения настроек модели
"""

import json

from config import MODEL_CONFIG_PATH


class ModelManager:
    """
    Отвечает за хранение настроек модели и их исползьование
    """

    def __init__(self, path=""):
        self.params = {}
        if path:
            self.load(path)

    def __getitem__(self, key):
        return self.params[key]

    def __setitem__(self, key, value):
        self.params[key] = value

    def load(self, path: str):
        """Загружает настройки из файла"""
        with open(path) as file_in:
            self.params = json.load(file_in)

    def save(self, path: str):
        """Сохраняет настройки в файл"""
        with open(path, "w") as file_out:
            json.dump(self.params, file_out, indent=4)

    def set_default(self):
        """Устанавливает эту модель главной"""
        set_default_model(self)


def set_default_model(mdl: ModelManager):
    """
    Делает mdl общей для всей системы
    Поскольку params это сслыка, то такая реализация подойдёт
    """
    global MODEL_CONFIG
    MODEL_CONFIG.params = mdl.params
    return MODEL_CONFIG


def restore_default_model():
    """Восстанавливает настройки модели из файла"""
    global MODEL_CONFIG
    MODEL_CONFIG = ModelManager(MODEL_CONFIG_PATH)
    return MODEL_CONFIG


MODEL_CONFIG = restore_default_model()
