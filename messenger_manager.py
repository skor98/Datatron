import logging
import constants
from speechkit_library import speech_to_text
from speechkit_library import SpeechException
from data_retrieving import DataRetrieving
import re
import random as rnd

logging.basicConfig(handlers=[logging.FileHandler('logs.log', 'a', 'utf-8')], level=20,
                    format='%(asctime)s\t%(message)s', datefmt='%Y-%m-%d %H:%M')


class MessengerManager:
    """Класс MessengerManager имеет API из 5 методов. Подробнее в документации к ним"""

    @staticmethod
    def make_request(text, source):
        """Самый универсальный API метод для текстовых запросов.

        Принимает на вход запрос (text), источник запроса (source).

        Возвращает объект класса M1Result."""

        logging.info("{}\t{}\t{}".format(__name__, source, text))

        return MessengerManager._querying(text)

    @staticmethod
    def make_request_directly_to_m2(text, source):
        """API метод, используемый на данный момент только в inline-режиме

        Принимает на вход запрос (text), источник запроса (source). Данный
        метод позволяет получить ответ исключительно от второго модуля.

        В inline-режиме используется для проверки может ли система обработать
        запрос пользователя или нет.

        Возвращает объект класса M2Result."""

        logging.info("{}\t{}\t{}".format(__name__, source, text))

        return DataRetrieving.get_data(text)

    @staticmethod
    def make_voice_request(record_bytes, source):
        """Универсальный API метод для обработки голосовых запросов

        Принимает на вход набор байтов записи (record_bytes), источник запроса (source).

        Возвращает объект класса M1Result."""

        try:
            text = speech_to_text(bytes=record_bytes)
            logging.info("{}\t{}\t{}".format(__name__, source, text))
        except SpeechException:
            return constants.ERROR_CANNOT_UNDERSTAND_VOICE
        else:
            return MessengerManager._querying(text)

    @staticmethod
    def greetings(text):
        """API метод для обработки приветствий от пользователя

        Принимает на вход сообщение (text). Возращает либо None, либо строку."""

        greets = MessengerManager._greetings(text)

        if greets is not None:
            return greets

    @staticmethod
    def _querying(user_request_string):
        general_result = M1Result()
        messages = []
        try:
            m2_result = DataRetrieving.get_data(user_request_string)
            if m2_result.status is False:
                messages.append(m2_result.message)
            else:
                messages.append(constants.MSG_WE_WILL_FORM_DATA_AND_SEND_YOU)
                messages.append(m2_result.message)
                messages.append('Ответ: ' + m2_result.response)

        except Exception as e:
            logging.info('{}\t{}'.format(e))
            print(e)
            messages.append(constants.ERROR_SERVER_DOES_NOT_RESPONSE)

        general_result.messages = messages
        return general_result

    @staticmethod
    def _simple_split(s):
        s = s.lower()
        s = re.sub(r'[^\w\s]', '', s)
        return s.split()

    @staticmethod
    def _greetings(text):
        for word in MessengerManager._simple_split(text):
            if word in constants.HELLO:
                return constants.HELLO_ANSWER[rnd.randint(0, len(constants.HELLO_ANSWER) - 1)]
            elif word in constants.HOW_ARE_YOU:
                return constants.HOW_ARE_YOU_ANSWER[rnd.randint(0, len(constants.HOW_ARE_YOU_ANSWER) - 1)]


class M1Result:
    def __init__(self, messages=None):
        self.messages = messages  # Variable, which storage all messages from _querying
