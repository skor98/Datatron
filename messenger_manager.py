#!/usr/bin/python3
# -*- coding: utf-8 -*-

import logging
import random
import re

from core.answer_object import CoreAnswer
from data_retrieving import DataRetrieving
from dbs.query_db import log_query_to_db
from manual_testing import get_jaccard
from speechkit import SpeechException
from speechkit import speech_to_text
import constants


def log_user_query(request_id, user_id, user_name, platform, query, query_type):
    """
    Сохраняет пользовательский запрос как в самих логах,
    так и в отделной sqlite базе данных
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
    def make_voice_request(
            source, user_id, user_name,
            request_id, bin_audio=None, filename=None
    ):
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
    def personalization(text):
        """API метод для обработки приветствий от пользователя

        :param text: сообщение от пользователя
        :return: либо строку, либо None
        """

        # чем меньше, тем больше примеров будет подходить
        JACCARD_SIMILARITY_THRESHOLD = 0.7

        text, tokens = MessengerManager._simple_split(text)
        tokens = set(tokens)

        for word in tokens:
            if word in constants.HELLO:
                return random.choice(constants.HELLO_ANSWER)

        for cur_const in constants.HOW_ARE_YOU:
            cur_set = set(cur_const.split())
            if get_jaccard(tokens, cur_set) > JACCARD_SIMILARITY_THRESHOLD:
                return random.choice(constants.HOW_ARE_YOU_ANSWER)

        for cur_const in constants.WHO_YOU_ARE:
            cur_set = set(cur_const.split())
            if get_jaccard(tokens, cur_set) > JACCARD_SIMILARITY_THRESHOLD:
                return random.choice(constants.WHO_YOU_ARE_ANSWER)

        for cur_const in constants.WHAT_CAN_YOU_DO:
            cur_set = set(cur_const.split())
            if get_jaccard(tokens, cur_set) > JACCARD_SIMILARITY_THRESHOLD:
                return random.choice(constants.WHAT_CAN_YOU_DO_ANSWER)

        for cur_const in constants.WHO_IS_YOUR_CREATOR:
            cur_set = set(cur_const.split())
            if get_jaccard(tokens, cur_set) > JACCARD_SIMILARITY_THRESHOLD:
                return random.choice(constants.WHO_IS_YOUR_CREATOR_ANSWER)

        for cur_const in constants.WHO_IS_YOUR_CREATOR:
            cur_set = set(cur_const.split())
            if get_jaccard(tokens, cur_set) > JACCARD_SIMILARITY_THRESHOLD:
                return random.choice(constants.WHO_IS_YOUR_CREATOR_ANSWER)

        for key in constants.EASTER_EGGS.keys():
            if set(key.split()) == tokens:
                return random.choice(constants.EASTER_EGGS[key])

        for thank_you_word in constants.THANK_YOU:
            if thank_you_word in text:
                return random.choice(constants.THANK_YOU_ANSWER)

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
            core_answer = CoreAnswer(
                message=str(err),
                error=str(err)
            )
            return core_answer

    @staticmethod
    def _simple_split(text):
        """Простая токенизация"""

        text = re.sub(r'[^\w\s]', '', text.strip().lower())

        # сохранение всех слов длинной более 1 символа
        tokens = [t for t in text.split() if len(t) > 1]
        return " ".join(tokens).strip(), tuple(tokens)
