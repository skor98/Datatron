#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json


def getClassFromDict(d):
    """Преобразует словарь в объект с членами -- ключами словаря"""
    class res:
        pass
    for key in d:
        setattr(res, key, d[key])
    return res

YANDEX_API_KEY = 'e05f5a12-8e05-4161-ad05-cf435a4e7d5b'
SETTINGS_PATH = "settings.json"


with open(SETTINGS_PATH, 'r') as file_settings:
    _settings_json = json.load(file_settings)

_cur_settings_dict = _settings_json["settings"][
    _settings_json["cur_settings"]
]

SETTINGS = getClassFromDict(_cur_settings_dict)
