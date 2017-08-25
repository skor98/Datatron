#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Генерация документов по Минфину
"""

import json
import logging
import math
from os import listdir, path
import subprocess
import sys
from uuid import uuid4

from config import SETTINGS, TEST_PATH_MINFIN, TECH_MINFIN_DOCS_FILE
from kb.kb_support_library import read_minfin_data
from model_manager import MODEL_CONFIG
import pandas as pd
import pycurl
from text_preprocessing import TextPreprocessing

import logs_helper  # pylint: disable=unused-import

# Название файла с готовой структурой данных
# по вопросам Минфина для последующей индексации в Apache Solr
OUTPUT_FILE = 'minfin_data_for_indexing.json'
SEARCH_OUTPUT_FILE = 'search_minfin_data_for_indexing.json'

# Путь к папке с исходными вопросами и приложениями от Минфина
path_to_folder_file = SETTINGS.PATH_TO_MINFIN_ATTACHMENTS


def set_up_minfin_data(index_way='curl'):
    """
    Метод для создания и индексации в Apache Solr
    документов для ответа на вопросы Минфина
    """

    logging.info('Начата работа с документами для Министерства Финансов')

    # чтение данные по минфину
    files, dfs = read_minfin_data()

    # Автоматическая генерация тестов
    _create_tests(files, dfs)

    minfin_docs = _refactor_data(pd.concat(dfs))

    if MODEL_CONFIG["enable_minfin_tf_idf_key_words_calculation"]:
        _add_automatic_key_words(minfin_docs)

    _write_data(minfin_docs)
    if index_way == 'curl':
        _index_data_via_curl()
    else:
        _index_data_via_jar_file()


def _refactor_data(data):
    """
    Преобразование датафрейма в список объектов типа
    MinfinDocument
    """

    request_id = uuid4().hex

    docs = []
    for row in data.itertuples():
        doc = MinfinDocument()
        doc.number = row.id

        doc.question = row.question

        # индексируемое поле
        doc.lem_question = _refactor_data.TPP(row.question, request_id)

        doc.lem_question_len = len(doc.lem_question.split())

        doc.short_answer = row.short_answer
        # индексируемое поле
        doc.lem_short_answer = _refactor_data.TPP(row.short_answer, request_id)

        doc.full_answer = row.full_answer

        lem_key_words = _refactor_data.TPP(row.key_words, request_id)

        # индексируемое поле
        doc.lem_key_words = ' '.join(
            [lem_key_words] * MODEL_CONFIG["minfin_manual_key_words_repetition"]
        )

        synonym_questions = _get_manual_synonym_questions(doc.number)
        if synonym_questions:
            lem_synonym_questions = [
                _refactor_data.TPP(question, request_id)
                for question in synonym_questions
                ]

        lem_full_answer = TextPreprocessing()(row.full_answer)

        # добавление уникальных слов и длинного ответа
        lem_extra_key_words = (
            set(' '.join(lem_synonym_questions).split()) |
            set(lem_full_answer.split())
        )

        # удаление уже используемых слов lem_key_words, lem_short_answer
        lem_extra_key_words -= set(doc.lem_short_answer.split())
        lem_extra_key_words -= set(lem_key_words.split())
        lem_extra_key_words = ' '.join(lem_extra_key_words)

        # индексируемое поле
        doc.lem_extra_key_words = ' '.join([lem_extra_key_words] * 5)

        # Может быть несколько
        if row.link_name:
            if ';' in row.link_name:
                doc.link_name = [elem.strip() for elem in row.link_name.split(';')]
                doc.link = [elem.strip() for elem in row.link.split(';')]
            else:
                doc.link_name = row.link_name.strip()
                doc.link = row.link.strip()

        # Может быть несколько
        if row.picture_caption:
            if ';' in row.picture_caption:
                doc.picture_caption = [elem.strip() for elem in row.picture_caption.split(';')]
                doc.picture = [elem.strip() for elem in row.picture.split(';')]
            else:
                doc.picture_caption = row.picture_caption.strip()
                doc.picture = row.picture.strip()

        # Может быть несколько
        if row.document_caption:
            if ';' in row.document_caption:
                doc.document_caption = [
                    elem.strip() for elem in row.document_caption.split(';')
                    ]
                doc.document = [elem.strip() for elem in row.document.split(';')]
            else:
                doc.document_caption = row.document_caption.strip()
                doc.document = row.document.strip()
        docs.append(doc)

    return docs


_refactor_data.TPP = TextPreprocessing(label='MFDG', delete_question_words=False)


def _write_data(data):
    """
    Преобразование списка объектов типа MinfinDocument
    в JSON-строку и ее запись в файл
    """

    if MODEL_CONFIG['enable_searching_and_tech_info_separation']:
        tech_docs_file = path.join(path_to_folder_file, TECH_MINFIN_DOCS_FILE)
        search_docs_file = path.join(path_to_folder_file, SEARCH_OUTPUT_FILE)

        with open(tech_docs_file, 'w', encoding='utf-8') as file:
            file.write(
                '[{}]'.format(
                    ','.join([element.to_tech_json_object() for element in data])
                )
            )

        with open(search_docs_file, 'w', encoding='utf-8') as file:
            file.write(
                '[{}]'.format(
                    ','.join([element.to_search_json_object() for element in data])
                )
            )

    else:
        indexed_file = path.join(path_to_folder_file, OUTPUT_FILE)
        with open(indexed_file, 'w', encoding='utf-8') as file:
            file.write(
                '[{}]'.format(
                    ','.join([element.to_json() for element in data])
                )
            )


def _get_manual_synonym_questions(question_number):
    """
    Получение списка вопросов из minfin_test_manual документов
    для конктертного вопроса (т.е. списка синонимичных запросов
    к данному, прописанных вручную)
    """

    extra_requests = []

    # Номер партии
    port_num = question_number.split('.')[0]

    def is_portion_func(f):
        """
        Выбор вручную прописанных тестов
        для определенной партии вопросов
        """

        return f.endswith('.txt') and port_num in f and 'manual' in f

    file_with_portion = [f for f in listdir(TEST_PATH_MINFIN) if is_portion_func(f)]

    # Если такого файла еще нет, так как его не успели написать
    if not file_with_portion:
        return None

    # Добавление синонимичных запросов
    with open(path.join(TEST_PATH_MINFIN, file_with_portion[0]), 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()  # очистим от всего, на случай если это пустая строчка
            if not line:
                continue

            line_splitted = line.split(':')

            if len(line_splitted) == 1:
                # Нет ответа, это плохо!!
                logging.error("На вопрос {} в файле {} нет ответа!".format(
                    line_splitted[0],
                    path.join(TEST_PATH_MINFIN, file_with_portion[0])
                ))
                sys.exit(0)

            if line_splitted[1].strip() == question_number:
                extra_requests.append(line_splitted[0])

    return extra_requests


def _index_data_via_curl():
    """
    Отправа JSON файла с документами по кубам
    на индексацию в Apache Solr через cURL
    """

    indexed_file = OUTPUT_FILE
    if MODEL_CONFIG['enable_searching_and_tech_info_separation']:
        indexed_file = SEARCH_OUTPUT_FILE

    curl_instance = pycurl.Curl()
    curl_instance.setopt(
        curl_instance.URL,
        'http://{}:8983/solr/{}/update?commit=true'.format(
            SETTINGS.SOLR_HOST,
            SETTINGS.SOLR_MAIN_CORE
        )
    )

    curl_instance.setopt(curl_instance.HTTPPOST, [(
        'fileupload',
        (
            curl_instance.FORM_FILE,
            path.join(path_to_folder_file, indexed_file),
            curl_instance.FORM_CONTENTTYPE, 'application/json'
        )
    ), ])
    curl_instance.perform()

    logging.info('Документ {} проиндексирован через CURL'.format(
        indexed_file
    ))


def _index_data_via_jar_file():
    """
    Отправа JSON файла с документами по кубам
    на индексацию в Apache Solr через файл
    встроенный инструмент от Apache Solr – файл post.jar
    из папки /example/exampledocs
    """

    path_to_json_data_file = path.join(
        path_to_folder_file,
        OUTPUT_FILE
    )

    if MODEL_CONFIG['enable_searching_and_tech_info_separation']:
        path_to_json_data_file = path.join(
            path_to_folder_file,
            SEARCH_OUTPUT_FILE
        )

    command = r'java -Dauto -Dc={} -Dfiletypes=json -jar {} {}'.format(
        SETTINGS.SOLR_MAIN_CORE,
        SETTINGS.PATH_TO_SOLR_POST_JAR_FILE,
        path_to_json_data_file
    )
    subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).wait()

    logging.info('Документ {} проиндексирован через JAR файл'.format(
        SEARCH_OUTPUT_FILE
    ))


def _add_automatic_key_words(documents):
    """
    Добавление автоматических ключевых слов с помощью TF-IDF
    """

    # Количество повторений ключевых слов, созданных с помощью TF-IDF метода
    tf_idf_key_words_repetition = MODEL_CONFIG["minfin_tf_idf_key_words_repetition"]

    matrix = _calculate_matrix(documents)

    for idx, doc in enumerate(documents):
        extra_key_words = _key_words_for_doc(idx, matrix)
        extra_key_words *= tf_idf_key_words_repetition
        doc.lem_key_words += ' {}'.format(' '.join(extra_key_words))


def _create_tests(files_names, data_frames):
    """
    Создание автоматических тестов по Минфину формата:
    <запрос по шаблону из .xlsx>: <номер запроса>
    """

    for file_name, df in zip(files_names, data_frames):
        file_path = path.join(
            TEST_PATH_MINFIN,
            'minfin_test_auto_for_{}.txt'.format(file_name.rsplit('.', 1)[0])
        )

        with open(file_path, 'w', encoding='utf-8') as file_out:
            for row in df[['id', 'question']].itertuples():
                file_out.write('{}:{}\n'.format(row.question, row.id))
                # ToDo обработка ошибок открытия файлов


def _calculate_matrix(documents):
    """
    Расчет матрицы TF-IDF по всем входных документами
    """

    # Словарь с рассчетами
    score = {}
    for idx, doc in enumerate(documents):
        # получение строкового предстваления документа Минфина
        # результат алгоритма зависит от определения строкового представления
        doc_string_representation = doc.get_string_representation()

        # токенизация с удалением повторяющихся слов
        tokens = set(doc_string_representation.split())

        score[idx] = []
        for token in tokens:
            score[idx].append(
                {
                    'term': token,
                    'tf': _tf(token, doc_string_representation),
                    'idf': _idf(token, documents),
                    'tfidf': _tfidf(token, doc_string_representation, documents)
                }
            )

    # сортировка элементов в словаре в порядке убывания индекса TF-IDF
    for document_id in score:
        score[document_id] = sorted(score[document_id], key=lambda d: d['tfidf'], reverse=True)

    return score


def _key_words_for_doc(document_id, score, top=5):
    key_words = []
    for word in score[document_id][:top]:
        resulting_patternt = 'Doc: {} word: {} TF: {} IDF: {} TF-IDF: {}'
        print(resulting_patternt.format(
            document_id,
            word['term'],
            word['tf'],
            word['idf'],
            word['tfidf']
        ))
        key_words.append(word['term'])
    return key_words


def _tf(word, doc):
    """TF: частота слова в документе"""

    return doc.count(word)


def _documents_contain_word(word, doc_list):
    """количество документов, в которых встречается слово"""

    return 1 + sum(1 for document in doc_list if word in document.get_string_representation())


def _idf(word, doc_list):
    """
    IDF: логарифм от общего количества документов, деленного
    на количество документов, в которых встречается данное слово
    """

    return math.log(len(doc_list) / float(_documents_contain_word(word, doc_list)))


def _tfidf(word, doc, doc_list):
    """Подсчет метрики TF-IDF"""

    return _tf(word, doc) * _idf(word, doc_list)


class MinfinDocument:
    """
    Класс для хранения структуры документа
    для ответа по вопросам от Минфина
    """

    def __init__(self):
        self.type = 'minfin'
        self.number = 0
        self.question = ''
        self.short_answer = ''
        self.full_answer = None
        self.lem_question = ''
        self.lem_question_len = 0
        self.lem_extra_key_words = None
        self.lem_short_answer = ''
        self.lem_key_words = ''
        self.link_name = None
        self.link = None
        self.picture_caption = None
        self.picture = None
        self.document_caption = None
        self.document = None
        self.inner_id = uuid4().hex

    def to_json(self):
        """Перевод класса в JSON-строку"""

        return json.dumps(
            self,
            default=lambda obj: obj.__dict__,
            ensure_ascii=False,
            sort_keys=True,
            indent=4
        )

    def to_tech_json_object(self):
        """
        Перевод в объект с исключительно технической информацией
        """

        keys_to_return = (
            'number', 'question', 'short_answer', 'full_answer',
            'link_name', 'link',
            'picture_caption', 'picture',
            'document_caption', 'document',
            'inner_id'
        )

        return json.dumps(
            {key: getattr(self, key, None) for key in keys_to_return},
            ensure_ascii=False,
            sort_keys=True,
            indent=4
        )

    def to_search_json_object(self):
        """
        Перевод в объект с исключительно поисковыми полями
        """

        keys_to_return = (
            'type',
            'lem_question',
            'lem_question_len',
            'lem_extra_key_words',
            'lem_short_answer',
            'lem_key_words',
            'inner_id'
        )

        return json.dumps(
            {key: getattr(self, key, None) for key in keys_to_return},
            ensure_ascii=False,
            sort_keys=True,
            indent=4
        )

    def get_string_representation(self):
        """Cтроковое представление документа"""

        # Здесь есть над чем подумать, так как в зависимости
        # от того, данные из каких полей берутся, результат
        # может как улучшаться, так и ухудшаться
        lem_synonym_questions = []

        # Ручные нормализованные ключевые слова по одному разу
        # Плюс нормализованный запрос
        # Плюс синонимичные запросы, если прописаны
        return ('{} {} {}'.format(
            set(self.lem_key_words),
            self.lem_question,
            ' '.join(lem_synonym_questions)))
