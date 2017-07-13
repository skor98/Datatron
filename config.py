#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Место хранения всех настроек, связанных с функционированием и поведением.
Константы задающие особенности поведения.
НЕ место для хранения какого-либо содержательного контента, типа сообщений пользователю.
"""

import json
from os import path


class SettingsStorer:
    """
    Хранит в себе настройки, специфичные для разработчика.
    Члены подгружаются динамически
    """

    def __init__(self, dict_in, defaults=None):
        if not defaults:
            defaults = {}
        for key in set(dict_in).union(defaults):
            value = dict_in.get(key, defaults.get(key))
            if isinstance(value, dict):
                value = SettingsStorer(value, defaults.get(key))
            setattr(self, key, value)

    _legacy = {
        "ADMIN_TELEGRAM_ID": "TELEGRAM.ADMIN_IDS",
        "PATH_TO_SOLR_POST_JAR_FILE": "SOLR.PATH_TO_POST_JAR",
        "PATH_TO_USER_DB": "*/dbs/users.db",
        "PATH_TO_KNOWLEDGEBASE": "*/kb/knowledge_base.db",
        "SOLR_HOST": "SOLR.HOST",
        "SOLR_MAIN_CORE": "SOLR.MAIN_CORE",
        "TELEGRAM_API_TOKEN": "TELEGRAM.API_TOKEN",
        "TELEGRAM_API_TOKEN_FINAL": "TELEGRAM.TOKEN_FINAL",
        "PATH_TO_MINFIN_ATTACHMENTS": "*/data/minfin/",
        "HOST": "WEB_SERVER.HOST",
        "WEBHOOK_PORT": "TELEGRAM.WEBHOOK_PORT"
    }

    # Очень толстый способ поддержания обратной совместимости
    def __getattr__(self, key):
        newkey = self._legacy.get(key)
        if not newkey:
            raise AttributeError
        elif newkey.startswith('*'):
            return self.DATATRON_FOLDER + newkey[1:]
        elif '.' in newkey:
            pref, suff = newkey.split('.', 1)
            return getattr(getattr(self, pref), suff)
        else:
            return getattr(self, newkey)


YANDEX_API_KEY = 'e05f5a12-8e05-4161-ad05-cf435a4e7d5b'

SETTINGS_PATH = "settings.json"
QUERY_DB_PATH = path.join("dbs", "query.db")
LOGS_PATH = 'logs.log'
MODEL_CONFIG_PATH = "model.json"

DATE_FORMAT = "%Y.%m.%d"
TIME_FORMAT = "%H:%M:%S"
DATETIME_FORMAT = "{} {}".format(DATE_FORMAT, TIME_FORMAT)

with open(SETTINGS_PATH, 'r') as file_settings:
    _settings_json = json.load(file_settings)

_cur_settings_dict = _settings_json["settings"][
    _settings_json["cur_settings"]
]
_default_settings_dict = _settings_json['settings']['_default']

try:
    LOG_LEVEL = _settings_json["log_level"]
except:
    print('Пожалуйста, добавьте значение "log_level" в файл настроек')
    LOG_LEVEL = "INFO"
    print("Установлен уровень {}".format(LOG_LEVEL))

SETTINGS = SettingsStorer(_cur_settings_dict, _default_settings_dict)

# Ещё немного обратной совместимости
API_PORT = getattr(SETTINGS.WEB_SERVER, 'API_PORT', None)
