#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Регулярная актуализация даты обновления
данных в OLAP-кубах
"""

import schedule
import time
import datetime
import requests
import logging

from model_manager import MODEL_CONFIG
from model_manager import save_default_model

import logs_helper  # pylint: disable=unused-import


def refresh_cube_update_date():
    """
    Актуализация даты обновления данных в оперативных кубах
    """

    url = "http://conf.prod.fm.epbs.ru/mdxexpert/Cube"
    data = {
        "schemaName": "CLDO01",
        "cubeName": "DB"
    }

    update_date = requests.post(url, data).json()["lastUpdated"][:10]

    update_date = datetime.datetime.strptime(update_date, '%Y-%m-%d')
    update_date = update_date.strftime('%d.%m.%Y')

    if MODEL_CONFIG["cube_update_date"] != update_date:
        MODEL_CONFIG["cube_update_date"] = update_date

        MODEL_CONFIG.set_default()
        save_default_model(MODEL_CONFIG)

        logging.info(
            "Дата обновления данных в кубах актуализирована ({})".format(
                MODEL_CONFIG["cube_update_date"]
            )
        )
    else:
        logging.info("Дата обновления данных корректна")


schedule.every().monday.do(refresh_cube_update_date)

while True:
    schedule.run_pending()
    time.sleep(1)
