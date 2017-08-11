#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Поднимает сервис с API.
Поддерживает голос, текст и возвращает список документов по минфину
"""

from os import path, makedirs
import logging
from uuid import uuid4
import json


from flask import send_file
import pandas as pd
from flask import Flask, request, make_response
from flask_restful import reqparse, abort, Api, Resource

from messenger_manager import MessengerManager
from kb.kb_support_library import read_minfin_data
import logs_helper  # pylint: disable=unused-import
from logs_helper import time_with_message
from config import SETTINGS

from core.answer_object import CoreAnswer
from core.cube_docs_processing import CubeAnswer
from core.minfin_docs_processing import MinfinAnswer
from models.responses.link_model import LinkModel
from models.responses.question_model import QuestionModel
from models.responses.text_response_model import TextResponseModel

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

        # Можно сразу привести к байтам, чтобы не делать это каждый раз
        get_minfin_data.data = json.dumps(
            get_minfin_data.data,
            ensure_ascii=False,
            indent=4
        ).encode("utf-8")
    return get_minfin_data.data


get_minfin_data.data = None


@time_with_message("_read_minfin_data", "debug", 10)
def _read_minfin_data():
    """
    Читает xlsx данные, соединяет в один документ и возвращает словарь с соотв. полями.
    Возвращает массив из словарей с вопросами
    Почти повторяет _read_data из kb/minfin_docs_generation.py
    """

    # чтение данные по минфину
    _, dfs = read_minfin_data()

    # Объединение все датафреймов в один
    data = pd.concat(dfs)
    logging.info("Прочитано {} записей минфина".format(data.shape[0]))
    return tuple(
        {
            "id": item[0],
            "question": item[1]
        } for item in zip(
            data["id"].tolist(),
            data["question"].tolist()
        )
    )


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


# API v2
class VoiceQueryV2(Resource):
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


class TextQueryV2(Resource):
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

        response = MessengerManager.make_request(
            request_text,
            "API v2",
            args["apikey"],
            "",
            request_id
        )

        result = TextQueryV2.to_text_response(response)

        return result.toJSON_API()

    @staticmethod
    def to_text_response(response: CoreAnswer):
        text_response = TextResponseModel()
        text_response.status = response.status
        if response.answer is None:
            return text_response

        if isinstance(response.answer, CubeAnswer):
            logging.info('ответ по кубу')
            TextQueryV2.from_cube_answer(response, text_response)

        if isinstance(response.answer, MinfinAnswer):
            logging.info('ответ по минфину')
            TextQueryV2.from_minfin_answer(response, text_response)

        text_response.see_more = TextQueryV2.get_see_more(
            response.more_answers_order,
            response.more_cube_answers,
            response.more_minfin_answers
        )

        return text_response

    @staticmethod
    def from_cube_answer(response: CubeAnswer, text_response: TextResponseModel):
        text_response.short_answer = response.answer.message
        text_response.full_answer = response.answer.message

        return text_response

    @staticmethod
    def from_minfin_answer(response: CubeAnswer, text_response: TextResponseModel):
        if response.answer is not None:
            text_response.question = response.answer.question
            text_response.full_answer = response.answer.full_answer
            text_response.short_answer = response.answer.short_answer
            text_response.document_links = TextQueryV2.get_document_links(response)
            text_response.image_links = TextQueryV2.get_image_links(response)
            text_response.http_ref_links = TextQueryV2.get_gttp_ref_links(response)

        return text_response

    @staticmethod
    def get_see_more(answer_order: str, cube_answer_list: list, minfin_answer_list: list):
        see_more_items = []
        minfin_answer_counter = 0
        cube_answer_counter = 0
        for mask in list(answer_order):
            if mask == '1':
                question = minfin_answer_list[minfin_answer_counter].question
                minfin_answer_counter += 1
            else:
                question = cube_answer_list[cube_answer_counter].feedback.get('pretty_feedback')
                cube_answer_counter += 1

            see_more_items.append(QuestionModel(question))

            for item in see_more_items:
                logging.info("{}".format(item.question))

        return see_more_items

    @staticmethod
    def get_document_links(response: CoreAnswer):
        if response.answer.document is not None:
            document_links = []
            document_link = LinkModel('document', response.answer.document_caption, response.answer.document)
            document_links.append(document_link)
        else:
            return None

    @staticmethod
    def get_image_links(response: CoreAnswer):
        if response.answer.picture is not None:
            image_links = []
            image_link = LinkModel('image', response.answer.picture_caption, response.answer.picture)
            image_links.append(image_link)
            return image_links
        else:
            return None

    @staticmethod
    def get_gttp_ref_links(response: CoreAnswer):
        if response.answer.link is not None:
            http_ref_links = []
            http_ref_link = LinkModel('http_ref', response.answer.link_name, response.answer.link)
            http_ref_links.append(http_ref_link)
        else:
            return None

class MinfinListV2(Resource):
    """Возвращает весь список минфин вопросов. Актуально, пока их мало"""

    @time_with_message("MinfinList API Get", "info", 1)
    def get(self):
        return get_minfin_data()


app = Flask(__name__)  # pylint: disable=invalid-name
api = Api(app)  # pylint: disable=invalid-name
API_VERSION = getattr(SETTINGS.WEB_SERVER, 'VERSION', 'na')

parser = reqparse.RequestParser()  # pylint: disable=invalid-name
parser.add_argument('apikey', type=str, required=True, help="You need API key")
parser.add_argument('query', type=str)


@api.representation('application/json')
def output_json(data, code, headers=None):
    """
    Переопределим кодирование, чтобы не кодировать уже закодированное
    И отправлять юникод
    """
    if isinstance(data, bytes):
        resp = make_response(data, code)
    else:
        resp = make_response(json.dumps(data).encode("utf-8"), code)
    resp.headers.extend(headers or {})
    return resp


api.add_resource(VoiceQuery, '/{}/voice'.format(API_VERSION))
api.add_resource(TextQuery, '/{}/text'.format(API_VERSION))
api.add_resource(MinfinList, '/{}/minfin_docs'.format(API_VERSION))

# Реализуем API v2
api.add_resource(VoiceQueryV2, '/v2/voice')
api.add_resource(TextQueryV2, '/v2/text')
api.add_resource(MinfinListV2, '/v2/minfin_docs')


@app.route('/')
def main():
    """Чтобы что-то выводило при GET запросе - простая проверка рабочего состояния серевера"""
    return '<center><h1>Welcome to Datatron Home API page</h1></center>'


@app.route('/v1/resources/image')
def get_image():
    """
    Получение картинки. Пока они все отдаются как jpeg. Это не вечно
    ToDo: фиксить один тип
    """
    img_name = request.args.get('path')
    if not img_name:
        abort(404)
    img_path = path.join(SETTINGS.DATATRON_FOLDER, "data", "minfin", "img", img_name)
    if not path.isfile(img_path):
        abort(404, message="Resource {} is NOT valid".format(img_name))
    return send_file(img_path, mimetype='image/jpeg')


@app.route('/v1/resources/document')
def get_document():
    """
    Получение документа. Пока они все отдаются как pdf. Это не вечно
    ToDo: фиксить один тип
    """
    img_name = request.args.get('path')
    if not img_name:
        abort(404)
    img_path = path.join(SETTINGS.DATATRON_FOLDER, "data", "minfin", "doc", img_name)
    if not path.isfile(img_path):
        abort(404, message="Resource {} is NOT valid".format(img_name))
    return send_file(img_path, mimetype='application/pdf')
