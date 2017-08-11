#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Взаимодействие с Yandex SpeechKit
"""

import uuid
import subprocess
import logging

import xml.etree.ElementTree as XmlElementTree
from urllib.parse import quote
import httplib2
import requests
from ffmpy import FFmpeg

from config import SETTINGS

import logs_helper  # pylint: disable=unused-import

# Yandex URL для API
YANDEX_ASR_HOST = 'asr.yandex.net'
YANDEX_ASR_PATH = '/asr_xml'

# Размер блоков для передачи текста/голоса по кускам
CHUNK_SIZE = 1024 ** 2

# Путь к ffmpeg.exe с помощью которого идет конвертация
PATH_TO_FFMPEG = SETTINGS.PATH_TO_FFMPEG
TTS_URL = 'https://tts.voicetech.yandex.net/generate'


def run_ffmpeg(ff_inputs, ff_outputs, in_filename: str = None, in_content: bytes = None):
    """Обобщённый метод для вызова ffmpeg"""
    ff = FFmpeg(
        executable=PATH_TO_FFMPEG,
        inputs=ff_inputs,
        outputs=ff_outputs
    )
    if in_filename:
        in_content = open(in_filename, 'br').read()
    else:
        in_filename = "No file, just bytes"

    if not in_content:
        raise Exception("Не могу получить контент из {}".format(in_filename))

    stdout = ff.run(
        input_data=in_content,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )[0]

    return stdout


def convert_to_ogg(in_filename: str = None, in_content: bytes = None):
    """Конвертирование файл/байтов в OOG кодировку (необходимую для Telegram)"""

    return run_ffmpeg(
        {'pipe:0': None},
        {'pipe:1': ['-f', 'ogg', '-acodec', 'libopus']},
        in_filename,
        in_content
    )


def convert_to_mp3(in_filename: str = None, in_content: bytes = None):
    """Конвертирование файл/байтов в mp3 кодировку (необходимую для Telegram)"""

    return run_ffmpeg(
        {'pipe:0': None},
        {'pipe:1': ['-f', 'mp3', '-acodec', 'libmp3lame']},
        in_filename,
        in_content
    )


def convert_to_pcm16b16000r(in_filename=None, in_content=None):
    """
    Конвертирование файл/байтов в PCM 160000 Гц 16 бит –
    наилучшую кодировку для распознавания Speechkit-ом
    """
    return run_ffmpeg(
        {'pipe:0': None},
        {'pipe:1': ['-f', 's16le', '-acodec', 'pcm_s16le', '-ar', '16000']},
        in_filename,
        in_content
    )


def read_chunks(chunk_size, bin_data):
    """Реализация отправки файла по блокам, чтобы передовать объекты весом более 1 мб"""
    while True:
        chunk = bin_data[:chunk_size]
        bin_data = bin_data[chunk_size:]

        yield chunk

        if not bin_data:
            break


def text_to_speech(text, lang='ru-RU', filename=None, file_like=None, convert=True, as_audio=False):
    """Преобразования текста в речь"""

    # Если ответ имеет процентный формат, то замени процент
    text = text.replace('%', 'процентов')

    # Если используется + (экранированный для Solr)
    # для указания ударения
    text = text.replace('\\+', '+')

    url = TTS_URL + '?text={}&format={}&lang={}&speaker={}&key={}&emotion={}&speed={}'.format(
        quote(text), 'mp3', lang, 'oksana', SETTINGS.YANDEX_API_KEY, 'neutral', '1.0')

    req = requests.get(url)
    if req.status_code == 200:
        response_content = req.content
    else:
        logging.error("При запросе к TTS получили не 200 код")
        raise Exception('{}: {}'.format(__name__, req.text))

    # Для телеграма файл конвертируется в OGG формат, а не возвращается аудио записью
    if not as_audio and convert:
        response_content = convert_to_ogg(in_content=response_content)

    if filename:
        with open(filename, 'wb') as file:
            file.write(response_content)
    elif file_like:
        file_like.write(response_content)

    return response_content


def speech_to_text(
        filename=None,
        bin_audio=None,
        request_id=uuid.uuid4().hex,
        topic='notes',
        lang='ru-RU'
):
    """Преобразования речи в текст"""

    if filename:
        with open(filename, 'br') as file:
            bin_audio = file.read()
    if not bin_audio:
        raise Exception('Neither file name nor bytes provided.')

    # Конвертирование в лучший формат для обработки
    bin_audio = convert_to_pcm16b16000r(in_content=bin_audio)

    # Доопределения URL
    url = YANDEX_ASR_PATH + '?uuid=%s&key=%s&topic=%s&lang=%s' % (
        request_id,
        SETTINGS.YANDEX_API_KEY,
        topic,
        lang
    )

    # Получение блоков аудиозаписи
    chunks = read_chunks(CHUNK_SIZE, bin_audio)

    # Настройка подключения
    connection = httplib2.HTTPConnectionWithTimeout(YANDEX_ASR_HOST)
    connection.connect()
    connection.putrequest('POST', url)

    # Указания необходимых для Яндекса заголовков
    connection.putheader('Transfer-Encoding', 'chunked')
    connection.putheader('Content-Type', 'audio/x-pcm;bit=16;rate=16000')
    connection.endheaders()

    # Передача аудиозаписи по блокам
    for chunk in chunks:
        connection.send(('%s\r\n' % hex(len(chunk))[2:]).encode())
        connection.send(chunk)
        connection.send('\r\n'.encode())

    connection.send('0\r\n\r\n'.encode())
    response = connection.getresponse()

    # Парсинг ответа
    if response.code != 200:
        raise SpeechException('При обращении к YANDEX_ASR не 200 код \tCode: {}\tТело:\n{}'.format(
            response.code,
            response.read()
        ))

    response_text = response.read()
    xml = XmlElementTree.fromstring(response_text)

    if int(xml.attrib['success']) != 1:
        exception_string = 'No text found.\n\nResponse:\n{}\n\nRequest id: {}'
        raise SpeechException(exception_string.format(
            response_text,
            request_id
        ))

    max_confidence = - float("inf")
    text = ''

    for child in xml:
        if float(child.attrib['confidence']) > max_confidence:
            text = child.text
            max_confidence = float(child.attrib['confidence'])

    if max_confidence == - float("inf"):
        exception_string = (
            'No text found.\n\n' +
            'Response:\n{}\n\n' +
            'Request id: {}'
        )
        raise SpeechException(exception_string.format(
            response_text,
            request_id
        ))

    return text


class SpeechException(Exception):
    pass
