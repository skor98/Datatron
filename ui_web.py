#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Web интерфейс для взаимодействия с Datatron.
Предназначен для разработки, не является основнымю
"""

import logging
import codecs
from os import path, makedirs
from random import choice
from string import ascii_lowercase, digits

from bottle import Bottle, request, run, BaseRequest

from messenger_manager import MessengerManager
from config import SETTINGS
import logs_helper  # pylint: disable=unused-import

# pylint: disable=no-member

# увеличения допустимого размера файла до 3мб для избежания 413 ошибки
BaseRequest.MEMFILE_MAX = 1024 * 3
app = Bottle()  # pylint: disable=invalid-name


@app.get('/')
def main():
    """Чтобы что-то выводило при GET запросе - простая проверка рабочего состояния серевера"""

    return '<center><h1>Welcome to Datatron Home API page</h1></center>'


@app.post('/text')
def post_basic():
    """POST запрос для текстовых запросов к системе"""

    # Получение полей
    request_text = request.forms.get('Request')
    source = request.forms.get('Source')
    user_id = request.forms.get('UserId')
    user_name = request.forms.get('UserName')
    request_id = request.forms.get('RequestId')

    # Исправление кодировки для кириллицы
    request_text = codecs.decode(bytes(request_text, 'iso-8859-1'), 'utf-8')

    # если все поля заполнены
    if request_text and source and user_id and user_name and request_id:
        return MessengerManager.make_request(
            request_text,
            source,
            user_id,
            user_name,
            request_id
        ).toJSON()


@app.post('/audio')
def post_audio_file():
    """POST запрос для голосовых запросов с помощью передачи файла запроса"""

    # Получение файла
    file = request.files.get('File')

    # Определение его формата
    file_extension = file.filename.rsplit('.', 1)[-1]

    # Определение дериктории для сохранения файла
    save_path = 'tmp'
    if not path.exists(save_path):
        makedirs(save_path)

    # Генерация случайного имени файла
    new_file_name = ''.join(choice(ascii_lowercase + digits) for _ in range(10))
    logging.debug("Создали новый временный файл {}".format(new_file_name))

    # Сохранения полученного файла под новым именем в папку для хранения временных файлов
    file_path = path.join(save_path, '{}.{}'.format(new_file_name, file_extension))
    file.save(file_path)

    source = request.forms.get('Source')
    user_id = request.forms.get('UserId')
    user_name = request.forms.get('UserName')
    request_id = request.forms.get('RequestId')

    # если все поля заполнены
    if file and source and user_id and user_name and request_id:
        return MessengerManager.make_voice_request(
            source,
            user_id,
            user_name,
            request_id,
            filename=file_path
        ).toJSON()


@app.error(404)
def error404(error):
    """Чтобы выводилась ошибка, если файл не найден"""

    return '<center><h1>Nothing here sorry: %s</h1></center>' % error


if __name__ == "__main__":
    run(app, host=SETTINGS.HOST, port=8019, debug=True)
