#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging
import random
import re

import constants
from data_retrieving import DataRetrieving
from dbs.query_db import log_query_to_db
from core.answer_object import CoreAnswer
from speechkit import SpeechException
from speechkit import speech_to_text


def log_user_query(request_id, user_id, user_name, platform, query, query_type):
    """
    Сохраняет пользователский запрос и в самих логах и в отделной
    sqlite базе данных
    """
    logging_str = (
        "Query_ID: {}\t" +
        "ID-пользователя: {}\t" +
        "Имя пользователя: {}\t" +
        "Платформа: {}\t" +
        "Запрос: {}\t" +
        "Формат: {}"
    )
    logging.info(logging_str.format(
        request_id,
        user_id,
        user_name,
        platform,
        query,
        query_type
    ))

    # Сохраняем в базе
    log_query_to_db(request_id, user_id, user_name, platform, query, query_type)


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
        log_user_query(
            request_id,
            user_id,
            user_name,
            source,
            text,
            'text'
        )

        return MessengerManager._querying(text, request_id)

    @staticmethod
    def make_voice_request(source, user_id, user_name, request_id, bin_audio=None, filename=None):
        """Универсальный API метод для обработки голосовых запросов

        :param source: источник (web, cmd, telegram, unity)
        :param user_id: идетификатор пользователя
        :param user_name: имя пользователя
        :param request_id: идентификатор запроса
        :param bin_audio: набор байтов аудиозаписи
        :param filename: файл айдиозаписи
        :return: объект класса DrSolrResult()
        """

        try:
            if filename:
                text = speech_to_text(filename=filename)
            else:
                text = speech_to_text(bin_audio=bin_audio)
            log_user_query(
                request_id,
                user_id,
                user_name,
                source,
                text,
                'voice'
            )
        except SpeechException:
            core_answer = CoreAnswer(
                message=constants.ERROR_CANNOT_UNDERSTAND_VOICE,
                error=constants.ERROR_CANNOT_UNDERSTAND_VOICE
            )
            return core_answer
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
    def _querying(user_request_string, request_id):
        try:
            result = DataRetrieving.get_data(user_request_string, request_id)
            if result.status is True:
                result.message = constants.MSG_WE_WILL_FORM_DATA_AND_SEND_YOU
            return result
        except Exception as err:
            logging.exception(err)
            logging.warning('Query_ID: {}\tОшибка: {}'.format(
                request_id,
                err
            ))
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
