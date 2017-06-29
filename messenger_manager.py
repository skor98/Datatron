import logging
import constants
from speechkit import speech_to_text
from speechkit import SpeechException
from data_retrieving import DataRetrieving
from dr.solr import DrSolrResult
import re
import random as rnd

logging.basicConfig(handlers=[logging.FileHandler('logs.log', 'a', 'utf-8')], level='INFO',
                    format='%(asctime)s\t%(levelname)s\t%(message)s', datefmt='%Y-%m-%d %H:%M')

logging_str = "ID-запроса: {}\tМодуль: {}\tID-пользователя: {}\tИмя пользователя: {}\tПлатформа: {}\tЗапрос: {}\tФормат: {}"


class MessengerManager:
    """Класс MessengerManager имеет API из 5 методов. Подробнее в документации к ним"""

    @staticmethod
    def make_request(text, source, user_id, user_name, request_id):
        """Самый универсальный API метод для текстовых запросов.

        Принимает на вход запрос (text), источник запроса (source), идентификатор пользователя (user_id).

        Возвращает объект класса M1Result."""

        text = ' '.join(text.split())  # Удаление переносов, табуляций и пр.
        logging.info(logging_str.format(request_id, __name__, user_id, user_name, source, text, 'text'))

        return MessengerManager._querying(text, request_id)

    @staticmethod
    def make_request_directly_to_m2(text, source, user_id, user_name, request_id):
        """API метод, используемый на данный момент только в inline-режиме

        Принимает на вход запрос (text), источник запроса (source), идентификатор пользователя (user_id).
        Данный метод позволяет получить ответ исключительно от второго модуля.

        В inline-режиме используется для проверки может ли система обработать
        запрос пользователя или нет.

        Возвращает объект класса M2Result."""

        text = ' '.join(text.split())  # Удаление переносов, табуляций и пр.
        logging.info(logging_str.format(request_id, __name__, user_id, user_name, source, text, 'text'))

        return DataRetrieving.get_data(text, request_id)

    @staticmethod
    def make_minfin_request(text):
        text = ' '.join(text.split())  # Удаление переносов, табуляций и пр.
        return DataRetrieving.get_minfin_data(text)

    @staticmethod
    def make_minfin_request_voice(bytes=None, filename=None):
        try:
            if filename:
                text = speech_to_text(filename=filename)
            else:
                text = speech_to_text(bytes=bytes)
        except SpeechException:
            return constants.ERROR_CANNOT_UNDERSTAND_VOICE
        else:
            return DataRetrieving.get_minfin_data(text)

    @staticmethod
    def make_voice_request(source, user_id, user_name, request_id, bytes=None, filename=None):
        """Универсальный API метод для обработки голосовых запросов

        Принимает на вход набор байтов записи (record_bytes), источник запроса (source),
        идентификатор пользователя (user_id).

        Возвращает объект класса M1Result."""

        try:
            if filename:
                text = speech_to_text(filename=filename)
            else:
                text = speech_to_text(bytes=bytes)
            logging.info(logging_str.format(request_id, __name__, user_id, user_name, source, text, 'voice'))
        except SpeechException:
            dsr = DrSolrResult()
            dsr.error = dsr.message = constants.ERROR_CANNOT_UNDERSTAND_VOICE
            return dsr
        else:

            return MessengerManager._querying(text, request_id)

    @staticmethod
    def greetings(text):
        """API метод для обработки приветствий от пользователя

        Принимает на вход сообщение (text). Возращает либо None, либо строку."""

        greets = MessengerManager._greetings(text)

        if greets is not None:
            return greets

    @staticmethod
    def log_data(_logging_str, level='info'):
        if level == 'info':
            logging.info(_logging_str)
        elif level == 'warning':
            logging.warning(_logging_str)

    @staticmethod
    def _querying(user_request_string, request_id):
        try:
            m2_result = DataRetrieving.get_data(user_request_string, request_id)
            if m2_result.status is True:
                m2_result.message = constants.MSG_WE_WILL_FORM_DATA_AND_SEND_YOU
            return m2_result
        except Exception as e:
            logging.warning('ID-запроса: {}\tМодуль: {}\tОшибка: {}'.format(request_id, __name__, e))
            print('MessengerManager: ' + str(e))
            return None

    @staticmethod
    def _simple_split(s):
        s = s.lower()
        s = re.sub(r'[^\w\s]', '', s)
        return s.split()

    @staticmethod
    def _greetings(text):
        text = text.lower()
        for word in MessengerManager._simple_split(text):
            if word in constants.HELLO:
                return constants.HELLO_ANSWER[rnd.randint(0, len(constants.HELLO_ANSWER) - 1)]
            elif word in constants.HOW_ARE_YOU:
                return constants.HOW_ARE_YOU_ANSWER[rnd.randint(0, len(constants.HOW_ARE_YOU_ANSWER) - 1)]
