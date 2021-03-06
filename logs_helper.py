#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Инициализация и обработка логов.
Минимальное количество внешних зависимостей
Пока кажется, что в связи с небольшим размером проекта будет достаточно
одного логгера.
"""

from logging import FileHandler, StreamHandler
import datetime
import logging
import re
import sys

from config import DATETIME_FORMAT, LOG_LEVEL, LOGS_PATH
from dbs.query_db import get_queries


def string_to_log_level(in_str, default=logging.INFO):
    """
    Возвращает числовой log level соотвествующий строке in_str
    если такого нет, то возращается default или TypeError если default==0
    """
    if not isinstance(in_str, str):
        raise TypeError("Пытались привести НЕстроку к уровню лога")

    in_str = in_str.upper()
    string_to_level = {
        "NOTSET": logging.NOTSET,
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    try:
        return string_to_level[in_str]
    except KeyError:
        logging.error("Logging level {} не существует".format(in_str))
        if default:
            return default
        else:
            raise KeyError


def init_logging():
    """
    Устанавливает обработчики логгирования и другая инициализация логгирования
    """
    if init_logging.is_inited:
        logging.warning("Вызываем init_logging повторно. Что-то не так")
        return

    init_logging.is_inited = True
    logger = logging.getLogger()  # RootLogger
    logger.setLevel(string_to_log_level(LOG_LEVEL))

    file_handler = FileHandler(LOGS_PATH, 'a', 'utf-8')
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

    if isinstance(level, str):
        level_to_set = string_to_log_level(
            level,
            logging.getLogger().level
        )
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


def time_with_message(message, level="INFO", critical_seconds=None):
    """
    Декоратор для просто логгирования времени исполнения.
    Можно установить уровень: debug или info
    Можно установить critical_seconds: если займёт больше времени, то будет warning
    """

    level_to_pass = level

    def proc(func):
        def func_to_return(*args, **kwargs):
            dt_now = datetime.datetime.now()
            func_result = func(*args, **kwargs)
            time_delta = datetime.datetime.now() - dt_now

            log_string = '"{}" заняло {}'.format(message, time_delta)
            level = level_to_pass.lower()
            if level == "info":
                logging.info(log_string)
            elif level == "debug":
                logging.debug(log_string)
            else:
                raise Exception("Указан неправильный формат логирования")

            if critical_seconds is not None:
                critical_td = datetime.timedelta(seconds=critical_seconds)

                if time_delta > critical_td:
                    warning_template = 'ПРЕВЫШЕНО критическое время "{}" реальное: {}'
                    logging.warning(
                        warning_template.format(message, time_delta))

            return func_result

        return func_to_return

    return proc


class LogsRetriever:
    """
    Класс для вывода логов в Телеграме. Используется как нами,
    так и методологами для тестирования.
    """

    # Должен быть именно в этом файле так как жёстко связан с форматом логов
    def __init__(self, path_to_log_file=LOGS_PATH):
        self.path_to_log_file = path_to_log_file

    def get_log(self, kind='all', user_id=None, time_delta=15):
        """Возвращает лог"""
        if not isinstance(time_delta, datetime.timedelta):
            time_delta = datetime.timedelta(seconds=time_delta * 60)
        # Все логи
        if kind == 'all':
            return self._get_all_logs()
        # Логи за сессию
        elif kind == 'session':
            return self._get_session_logs(user_id, time_delta)
        # Все логи уровня INFO
        elif kind == 'info':
            return self._get_all_info_logs(time_delta)
        # Все логи уровня WARNING
        elif kind == 'warning':
            return self._get_all_warning_logs(time_delta)
        # Запросы пользователя
        elif kind == 'queries':
            return self._get_queries_logs(user_id, time_delta)
        # Логи последнего запроса
        else:
            raise Exception("Неизвестный тип лога {}".format(kind))

    def _get_all_logs(self):
        """Возвращает весь файл с логами"""
        with open(self.path_to_log_file, encoding='utf-8') as log_in:
            all_logs = log_in.read()
        return all_logs

    def _get_queries_logs(self, user_id, time_delta):
        """Возвращает запросы пользователя к БД"""
        if user_id == "all":
            return '\n'.join(get_queries(None, time_delta))

        return '\n'.join(get_queries(user_id, time_delta))

    def _get_session_logs(self, user_id, time_delta):
        """
        Логи только текущей сессии
        Возвращает список запросов и их идентификторов
        """
        user_re = re.compile(
            r"Query_ID:\s*([\d\w-]+)\s*ID-пользователя:\s*{}.*Запрос:\s*(.+)\s*Формат".format(user_id)
        )
        query_pattern = r".*Query_ID:\s*{}.*"
        logs = []

        dt_now = datetime.datetime.now()
        possible_querie_res = []
        for line in open(self.path_to_log_file, encoding='utf-8'):
            line = line.strip()
            try:
                is_found_in_query = False
                for query_re in possible_querie_res:
                    if query_re.match(line):
                        logs.append(line)
                        is_found_in_query = True
                        break
                if is_found_in_query:
                    continue

                # Этот блок кода должен быть в начале, так быстрее
                query_id, query_text = user_re.findall(line)[0]
                query_id = query_id.strip()
                query_text = query_text.strip()

                line_splitted = line.split()
                line_dt = LogsRetriever._get_dt_from_line(
                    line_splitted[0] + " " + line_splitted[1])
                if line_dt + time_delta < dt_now:
                    # слишком старое
                    continue
                possible_querie_res.append(
                    re.compile(query_pattern.format(query_id)))

                logs.append("{} {}".format(query_id, query_text))
            except:
                # Если возникла ошибка, то RegExp не подходит или это стек трейс
                pass

        return '\n'.join(list(reversed(logs)))

    def _get_all_info_logs(self, time_delta):
        return self._get_logs_at_level("INFO", time_delta)

    def _get_all_warning_logs(self, time_delta):
        return self._get_logs_at_level("WARNING", time_delta)

    def _get_logs_at_level(self, min_level, time_delta):
        log_out = []

        dt_now = datetime.datetime.now()
        need_level = string_to_log_level(min_level)

        for line in open(self.path_to_log_file, encoding='utf-8'):
            try:
                line_splitted = line.split()
                line_dt = LogsRetriever._get_dt_from_line(
                    line_splitted[0] + " " + line_splitted[1])
                if line_dt + time_delta < dt_now:
                    # слишком старое
                    continue
                if string_to_log_level(line_splitted[2], default=logging.WARNING) < need_level:
                    continue
                log_out.append(line)
            except:
                # Если возникла ошибка, то это интересно и нужно записать
                log_out.append(" -> ")
                log_out.append(line)

        log_out.reverse()

        return ''.join(log_out)  # Перенсо строки не нужен, т.к. уже есть

    @staticmethod
    def _get_dt_from_line(data_log_part):
        return datetime.datetime.strptime(data_log_part, DATETIME_FORMAT)


init_logging.is_inited = False  # Инициализация должна пройти ровно один раз

init_logging()
set_logging_level(LOG_LEVEL)
