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
    """Класс, который идет взаимодействие с сердцем системы (DataRetrieving). Этот класс имеет API из 5 методов"""

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
        logging.info(logging_str.format(request_id, __name__, user_id, user_name, source, text, 'text'))

        return MessengerManager._querying(text, request_id)

    @staticmethod
    def make_request_directly_to_m2(text, source, user_id, user_name, request_id):
        """API метод, используемый на данный момент только в inline-режиме и обращается напрямую к DataRetrieving

        :param text: запрос
        :param source: источник (web, cmd, telegram, unity)
        :param user_id: идетификатор пользователя
        :param user_name: имя пользователя
        :param request_id: идентификатор запроса
        :return: объект класса DrSolrResult()
        """

        text = ' '.join(text.split())  # Удаление переносов, табуляций и пр.
        logging.info(logging_str.format(request_id, __name__, user_id, user_name, source, text, 'text'))

        return DataRetrieving.get_data(text, request_id)

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
        except Exception as e:
            logging.warning('ID-запроса: {}\tМодуль: {}\tОшибка: {}'.format(request_id, __name__, e))
            print('MessengerManager: ' + str(e))
            dsr = DrSolrResult()
            dsr.message = dsr.error = str(e)
            return dsr

    @staticmethod
    def _simple_split(s):
        """Простая токенизация"""

        s = s.lower()
        s = re.sub(r'[^\w\s]', '', s)
        return s.split()

    @staticmethod
    def _greetings(text):
        """Обработка приветов и вопрос из серии 'как дела?'"""

        text = text.lower()
        for word in MessengerManager._simple_split(text):
            if word in constants.HELLO:
                return constants.HELLO_ANSWER[rnd.randint(0, len(constants.HELLO_ANSWER) - 1)]
            elif word in constants.HOW_ARE_YOU:
                return constants.HOW_ARE_YOU_ANSWER[rnd.randint(0, len(constants.HOW_ARE_YOU_ANSWER) - 1)]
