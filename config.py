#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Место хранения всех настроек, связанных с функционированием и поведением.
Константы задающие особенности поведения.
НЕ место для хранения какого-либо содержательного контента, типа сообщений пользователю.
"""

import json


def get_class_from_dict(dict_in):
    """Преобразует словарь в объект с членами -- ключами словаря"""
    class SettingsStorer:
        """
        Хранит в себе настройки, специфичные для разработчика.
        Члены подгружаются динамически
        """
        pass
    for key in dict_in:
        value = dict_in[key]
        setattr(SettingsStorer, key, value)
    return SettingsStorer

YANDEX_API_KEY = 'e05f5a12-8e05-4161-ad05-cf435a4e7d5b'
SETTINGS_PATH = "settings.json"

DATE_FORMAT = "%Y.%m.%d"
TIME_FORMAT = "%H:%M:%S"
DATETIME_FORMAT = "{} {}".format(DATE_FORMAT, TIME_FORMAT)

with open(SETTINGS_PATH, 'r') as file_settings:
    _settings_json = json.load(file_settings)

_cur_settings_dict = _settings_json["settings"][
    _settings_json["cur_settings"]
]

try:
    LOG_LEVEL = _settings_json["log_level"]
except:
    print('Пожалуйста, добавьте значение "log_level" в файл настроек')
    LOG_LEVEL = "INFO"
    print("Установлен уровень {}".format(LOG_LEVEL))

SETTINGS = get_class_from_dict(_cur_settings_dict)
