#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Инициализация и обработка логов.
Минимальное количество внешних зависимостей
Пока кажется, что в связи с небольшим размером проекта будет достаточно
одного логгера.
"""
# ToDo: непосредственная интеграция с вытеснением MessengerManagera
# ToDo: писать логи в SQLite?

import sys
import logging
from logging import FileHandler, StreamHandler

from config import DATETIME_FORMAT, LOG_LEVEL


def init_logging():
    """
    Устанавливает обработчики логгирования и другая инициализация логгирования
    """
    if init_logging.is_inited:
        logging.warning("Вызываем init_logging повторно. Что-то не так")
        return

    init_logging.is_inited = True
    logger = logging.getLogger()  # RootLogger
    logger.setLevel(logging.INFO)

    file_handler = FileHandler('logs_new.log', 'a', 'utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s  %(funcName)s at %(module)s:%(lineno)d %(message)s',
        datefmt=DATETIME_FORMAT
    ))
    logger.addHandler(file_handler)

    console_handler = StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s",
        datefmt=DATETIME_FORMAT
    ))
    logger.addHandler(console_handler)


def set_logging_level(level):
    """
    Устанавливает уровень
    :param level: Строка с уровнем или число 1..50 (напр. logging.INFO)
    """
    string_to_level = {
        "NOTSET": logging.NOTSET,
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    if isinstance(level, str):
        try:
            level_to_set = string_to_level[level.upper()]
        except KeyError:
            logging.error("Logging level {} не существует".format(level))
            return
    elif isinstance(level, int):
        if level < 0 or level > 50:
            logging.error("level должен быть от 0 до 50, а не {}".format(
                type(level)
            ))
            return
        level_to_set = level
    else:
        logging.error("Неверный тип level - {}".format(type(level)))
    logger = logging.getLogger()
    logger.setLevel(level_to_set)

init_logging.is_inited = False  # Инициализация должна пройти ровно один раз

init_logging()
set_logging_level(LOG_LEVEL)
