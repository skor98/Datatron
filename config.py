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


def fixed_path(file):
    return path.join(path.dirname(__file__), file)


SETTINGS_PATH = fixed_path("settings.json")
QUERY_DB_PATH = fixed_path(path.join("dbs", "query.db"))
LOGS_PATH = fixed_path('logs.log')
MODEL_CONFIG_PATH = fixed_path("model.json")

TEST_PATH_CUBE = fixed_path(path.join("tests", "cube"))
TEST_PATH_MINFIN = fixed_path(path.join("tests", "minfin"))
TEST_PATH_RESULTS = fixed_path(path.join("tests", "results"))

DATA_PATH = fixed_path("data")

WRONG_AUTO_MINFIN_TESTS_FILE = 'minfin_wrong_auto_tests.json'

TECH_CUBE_DOCS_FILE = fixed_path(
    path.join('kb', 'tech_cube_data_for_indexing.json')
)

TECH_MINFIN_DOCS_FILE = 'tech_minfin_data_for_indexing.json'

FEEDBACK_TESTS_FOLDER = fixed_path(path.join("tests", "cubes_pretty"))

DATE_FORMAT = "%Y.%m.%d"
TIME_FORMAT = "%H:%M:%S"
DATETIME_FORMAT = "{} {}".format(DATE_FORMAT, TIME_FORMAT)

with open(SETTINGS_PATH, 'r') as file_settings:
    _settings_json = json.load(file_settings)

_cur_settings_dict = _settings_json["settings"][
    _settings_json["cur_settings"]
]
_default_settings_dict = _settings_json['settings']['_default']

LOG_LEVEL = _settings_json.get("log_level", 'INFO')

SETTINGS = SettingsStorer(_cur_settings_dict, _default_settings_dict)
