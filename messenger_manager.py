#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging
import random
import re

import constants
from config import DATETIME_FORMAT
from data_retrieving import DataRetrieving
from solr import DrSolrResult
from speechkit import SpeechException
from speechkit import speech_to_text

logging.basicConfig(
    handlers=[logging.FileHandler('logs.log', 'a', 'utf-8')],
    level='INFO',
    format='%(asctime)s\t%(levelname)s\t%(message)s',
    datefmt=DATETIME_FORMAT
)

logging_str = (
    "ID-запроса: {}\t" +
    "Модуль: {}\t" +
    "ID-пользователя: {}\t" +
    "Имя пользователя: {}\t" +
    "Платформа: {}\t" +
    "Запрос: {}\t" +
    "Формат: {}"
)


class MessengerManager:
    """
    Класс, который идет взаимодействие с сердцем системы (DataRetrieving).
    Этот класс имеет API из 5 методов
    """

    @staticmethod
    def make_request(text, source, user_id, user_name, request_id):
        """Самый универсальный API метод для текстовых запросов.

        :param text: запрос
        :param source: источник (web, cmd, telegram, unity)
        :param user_id: идетификатор пользователя
        :param user_name: имя пользователя
        :param request_id: идентификатор запроса
        :return: объект класса DrSolrResult()
        """

        text = ' '.join(text.split())  # Удаление переносов, табуляций и пр.
        logging.info(logging_str.format(
            request_id,
            __name__,
            user_id,
            user_name,
            source,
            text,
            'text'
        ))

        return MessengerManager._querying(text, request_id)

    @staticmethod
    def make_voice_request(source, user_id, user_name, request_id, bytes=None, filename=None):
        """Универсальный API метод для обработки голосовых запросов

        :param source: источник (web, cmd, telegram, unity)
        :param user_id: идетификатор пользователя
        :param user_name: имя пользователя
        :param request_id: идентификатор запроса
        :param bytes: набор байтов аудиозаписи
        :param filename: файл айдиозаписи
        :return: объект класса DrSolrResult()
        """

        try:
            if filename:
                text = speech_to_text(filename=filename)
            else:
                text = speech_to_text(bytes=bytes)
            logging.info(logging_str.format(
                request_id,
                __name__,
                user_id,
                user_name,
                source,
                text,
                'voice'
            ))
        except SpeechException:
            dsr = DrSolrResult()
            dsr.error = dsr.message = constants.ERROR_CANNOT_UNDERSTAND_VOICE
            return dsr
        else:

            return MessengerManager._querying(text, request_id)

    @staticmethod
    def greetings(text):
        """API метод для обработки приветствий от пользователя

        :param text: сообщение от пользователя
        :return: либо строку, либо None
        """

        greets = MessengerManager._greetings(text)

        if greets is not None:
            return greets

    @staticmethod
    def log_data(_logging_str, level='info'):
        """Метод для выноса процесса логирования из конкретного UI

        :param _logging_str: строка для логов
        :param level: уровень логгирования
        :return:
        """
        if level == 'info':
            logging.info(_logging_str)
        elif level == 'warning':
            logging.warning(_logging_str)

    @staticmethod
    def _querying(user_request_string, request_id):
        try:
            result = DataRetrieving.get_data(user_request_string, request_id)
            if result.status is True:
                result.message = constants.MSG_WE_WILL_FORM_DATA_AND_SEND_YOU
            return result
        except Exception as err:
            logging.warning('ID-запроса: {}\tМодуль: {}\tОшибка: {}'.format(
                request_id,
                __name__,
                err
            ))
            print('MessengerManager: ' + str(err))
            dsr = DrSolrResult()
            dsr.message = dsr.error = str(err)
            return dsr

    @staticmethod
    def _simple_split(string_to_tokenize):
        """Простая токенизация"""

        string_to_tokenize = string_to_tokenize.lower()
        cleared_string = re.sub(r'[^\w\s]', '', string_to_tokenize)
        return cleared_string.split()

    @staticmethod
    def _greetings(text):
        """Обработка приветов и вопрос из серии 'как дела?'"""

        text = text.lower()
        for word in MessengerManager._simple_split(text):
            if word in constants.HELLO:
                return random.choice(constants.HELLO_ANSWER)
            elif word in constants.HOW_ARE_YOU:
                return random.choice(constants.HOW_ARE_YOU_ANSWER)
