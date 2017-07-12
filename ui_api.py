#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Поднимает сервис с API.
Поддерживает голос, текст и возвращает список документов по минфину
"""

from os import listdir, path, makedirs
import logging
from uuid import uuid4

import pandas as pd
from flask import Flask, request
from flask_restful import reqparse, abort, Api, Resource

from messenger_manager import MessengerManager
import logs_helper  # pylint: disable=unused-import
from logs_helper import time_with_message
from config import SETTINGS, API_PORT


# pylint: disable=no-self-use
# pylint: disable=missing-docstring


def get_minfin_data():
    """
    Возвращает данные по минфину в виде, готовому для вывода.
    В данный момент, кеширует их в памяти при запуске.
    Предполагается, что данных не очень много.
    """
    if get_minfin_data.data is None:
        get_minfin_data.data = _read_minfin_data()
    return get_minfin_data.data


get_minfin_data.data = None


@time_with_message("_read_minfin_data", "debug", 10)
def _read_minfin_data():
    """
    Читает xlsx данные, соединяет в один документ и возвращает словарь с соотв. полями.
    Возвращает массив из словарей с вопросами
    Почти повторяет _read_data из kb/minfin_docs_generation.py
    """
    files = []
    file_paths = []

    files_dir = SETTINGS.PATH_TO_MINFIN_ATTACHMENTS  # pylint: disable=no-member
    # Сохранение имеющихся в дериктории xlsx файлов
    for file_name in listdir(files_dir):
        if file_name.endswith(".xlsx"):
            file_paths.append(path.join(files_dir, file_name))
            files.append(file_name)

    # Создания листа dataframe по документам
    dfs = []
    for file_path in file_paths:
        # id документа имеет структуру {партия}.{порядковый номер}
        # если не переводить id к строке, то pandas воспринимает их как float и 3.10 становится 3.1
        # что приводит к ошибкам в тестировании
        cur_df = pd.read_excel(
            open(file_path, 'rb'),
            sheetname='questions',
            converters={'id': str}
        )
        cur_df = cur_df.fillna(0)
        dfs.append(cur_df)

    # Объединение все датафреймов в один
    data = pd.concat(dfs)
    logging.info("Прочитано {} записей минфина".format(data.shape[0]))
    return tuple({
                     "id": item[0],
                     "question": item[1]
                 } for item in zip(
        data["id"].tolist(),
        data["question"].tolist()
    ))


def is_valid_api_key(api_key):
    """
    Проверяет на правльность ключи доступа к API. На данный момент, один ключ
    может всё, без ограничений
    """
    return api_key in SETTINGS.API_KEYS  # pylint: disable=no-member


class VoiceQuery(Resource):
    """Обрабатывает отправку файлов голосом"""

    @time_with_message("VoiceQuery API Get", "info", 7)
    def post(self):
        args = parser.parse_args()

        if not is_valid_api_key(args["apikey"]):
            abort(403, message="API key {} is NOT valid".format(args["apikey"]))

        if 'file' not in request.files:
            abort(400, message='You need "file" parameter"')

        # Получение файла
        voice_file = request.files['file']

        # Определение его формата
        file_extension = voice_file.filename.rsplit('.', 1)[-1]

        # Определение дериктории для сохранения файла
        save_path = 'tmp'
        if not path.exists(save_path):
            makedirs(save_path)

        # Генерация случайного имени файла
        new_file_name = uuid4().hex[:10]

        # Сохранения полученного файла под новым именем в папку для хранения временных файлов
        file_path = path.join(save_path, '{}.{}'.format(new_file_name, file_extension))

        logging.debug("Создали новый временный файл {}".format(file_path))
        voice_file.save(file_path)

        request_id = uuid4().hex

        return MessengerManager.make_voice_request(
            "API v1",
            args["apikey"],
            "",
            request_id,
            filename=file_path
        ).toJSON_API()


class TextQuery(Resource):
    """Обрабатывает простой текстовой зарос"""

    @time_with_message("TextQuery API Get", "info", 4)
    def get(self):
        args = parser.parse_args()
        logging.info(args)

        if not is_valid_api_key(args["apikey"]):
            abort(403, message="API key {} is NOT valid".format(args["apikey"]))

        request_text = args['query']
        request_id = uuid4().hex

        if len(args['query']) < 4:
            abort(400, message='You need "query" parameter"')

        return MessengerManager.make_request(
            request_text,
            "API v1",
            args["apikey"],
            "",
            request_id
        ).toJSON_API()


class MinfinList(Resource):
    """Возвращает весь список минфин вопросов. Актуально, пока их мало"""

    @time_with_message("MinfinList API Get", "info", 1)
    def get(self):
        return get_minfin_data()


app = Flask(__name__)  # pylint: disable=invalid-name
api = Api(app)  # pylint: disable=invalid-name

parser = reqparse.RequestParser()  # pylint: disable=invalid-name
parser.add_argument('apikey', type=str, required=True, help="You need API key")
parser.add_argument('query', type=str)

api.add_resource(VoiceQuery, '/v1/voice')
api.add_resource(TextQuery, '/v1/text')
api.add_resource(MinfinList, '/v1/minfin_docs')


@app.route('/')
def main():
    """Чтобы что-то выводило при GET запросе - простая проверка рабочего состояния серевера"""

    return '<center><h1>Welcome to Datatron Home API page</h1></center>'


if __name__ == '__main__':
    app.run(
        host=SETTINGS.HOST,
        port=API_PORT,
        debug=False
    )
