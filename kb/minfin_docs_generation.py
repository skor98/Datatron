#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import math
import uuid
import subprocess
from os import getcwd, listdir, path

import requests
import pycurl
import pandas as pd

from text_preprocessing import TextPreprocessing
from config import SETTINGS

input_data_file_name = 'data.xlsx'
output_file = 'minfin_data_for_indexing_in_solr.json'
solr_clear_req = (
    'http://' + SETTINGS.SOLR_HOST + ':8983/solr/{}/' +
    'update?stream.body=%3Cdelete%3E%3Cquery%3E*:*%3C/' +
    'query%3E%3C/delete%3E&commit=true'
)
path_to_folder_file = r'{}\{}'.format(SETTINGS.PATH_TO_MINFIN_ATTACHMENTS, {})


def set_up_minfin_core(index_way='curl', clear=False, core=SETTINGS.SOLR_MAIN_CORE):
    """Главный API метод к этому модулю"""

    minfin_docs = _refactor_data(_read_data())
    _add_automatic_key_words(minfin_docs)
    _write_data(minfin_docs)
    if index_way == 'curl':
        _index_data_via_curl(clear=clear, core=core)
    elif index_way == 'jar_file':
        _index_data_via_cmd(clear=clear, core=core)


def _read_data():
    """Чтение данных из xlsx с помощью pandas и их очистка"""

    files = []
    file_paths = []

    # Сохранение имеющихся в дериктории xlsx файлов
    for file in listdir(SETTINGS.PATH_TO_MINFIN_ATTACHMENTS):
        if file.endswith(".xlsx"):
            file_paths.append(path.join(SETTINGS.PATH_TO_MINFIN_ATTACHMENTS, file))
            files.append(file)

    # Создания листа dataframe по документам
    dfs = []
    for file_path in file_paths:
        # id документа имеет структуру {партия}.{порядковый номер}
        # если не переводить id к строке, то pandas воспринимает их как float и 3.10 становится 3.1
        # что приводит к ошибкам в тестировании
        df = pd.read_excel(open(file_path, 'rb'), sheetname='questions', converters={'id': str})
        df = df.fillna(0)
        dfs.append(df)

    # Автоматическая генерация тестов
    _create_tests(files, dfs)

    # Объединение все датафреймов в один
    data = pd.concat(dfs)
    return data


def _write_data(data):
    """Запись всех документов в файл"""

    with open(path_to_folder_file.format(output_file), 'w', encoding='utf-8') as file:
        data_to_str = '[{}]'.format(','.join([element.toJSON() for element in data]))
        file.write(data_to_str)


def _refactor_data(data):
    tp = TextPreprocessing(uuid.uuid4())

    docs = []
    for index, row in data.iterrows():
        # Если запрос не параметризованных
        # Я хз, будут ли параметризованные запросу для минфин доков, но на всякий случай
        if not row.parameterized:
            doc = ClassicMinfinDocument()
            doc.number = str(row.id)
            doc.question = row.question
            lem_question = tp.normalization(
                row.question,
                delete_digits=True
            )
            doc.lem_question = ' '.join([lem_question] * 3)

            synonym_questions = _get_manual_synonym_questions(doc.number)

            if synonym_questions:
                lem_synonym_questions = [
                    tp.normalization(q, delete_digits=True) for q in synonym_questions
                ]
                doc.lem_synonym_questions = lem_synonym_questions

            doc.short_answer = row.short_answer
            doc.lem_short_answer = tp.normalization(
                row.short_answer,
                delete_digits=True
            )
            if row.full_answer:
                doc.full_answer = row.full_answer
                doc.lem_full_answer = tp.normalization(
                    row.full_answer,
                    delete_digits=True
                )
            kw = tp.normalization(row.key_words)

            # Ключевые слова записываются трижды, для увеличения качества поиска документа
            doc.lem_key_words = ' '.join([kw] * 3)

            # Может быть несколько
            if row.link_name:
                if ';' in row.link_name:
                    doc.link_name = [elem.strip() for elem in row.link_name.split(';')]
                    doc.link = [elem.strip() for elem in row.link.split(';')]
                else:
                    doc.link_name = row.link_name
                    doc.link = row.link

            # Может быть несколько
            if row.picture_caption:
                if ';' in row.picture_caption:
                    doc.picture_caption = [elem.strip() for elem in row.picture_caption.split(';')]
                    doc.picture = [elem.strip() for elem in row.picture.split(';')]
                else:
                    doc.picture_caption = row.picture_caption
                    doc.picture = row.picture

            # Может быть несколько
            if row.document_caption:
                if ';' in row.document_caption:
                    doc.document_caption = [
                        elem.strip() for elem in row.document_caption.split(';')
                    ]
                    doc.document = [elem.strip() for elem in row.document.split(';')]
                else:
                    doc.document_caption = row.document_caption
                    doc.document = row.document

        docs.append(doc)
    return docs


def _get_manual_synonym_questions(question_number):
    """Получение списка вопросов из minfin_test_manual документов для конктертного вопроса

    :param question_number: номер вопроса документа
    :return: list перефразированных запросов
    """
    extra_requests = []

    port_num = question_number.split('.')[0]

    path_to_tests = r'{}\tests'.format(getcwd())

    is_portion_func = lambda f: f.endswith('.txt') and port_num in f and 'manual' in f
    file_with_portion = [f for f in listdir(path_to_tests) if is_portion_func(f)]

    if not file_with_portion:
        return None

    with open(r'{}\{}'.format(path_to_tests, file_with_portion[0]), 'r', encoding='utf-8') as file:
        for line in file:
            line = line.split(':')
            if line[1].strip() == question_number:
                extra_requests.append(line[0])

    return extra_requests


def _index_data_via_cmd(clear, core):
    path_to_json_data_file = path_to_folder_file.format(output_file)
    path_to_solr_jar_file = SETTINGS.PATH_TO_SOLR_POST_JAR_FILE

    if clear:
        requests.get(solr_clear_req.format(core))

    command = r'java -Dauto -Dc={} -Dfiletypes=json -jar {} {}'.format(
        core,
        path_to_solr_jar_file,
        path_to_json_data_file
    )
    subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).wait()
    print('Минфин-документы проиндексированы через JAR файл')


def _index_data_via_curl(clear, core):
    if clear:
        requests.get(solr_clear_req.format(core))

    curl_instance = pycurl.Curl()
    curl_instance.setopt(
        curl_instance.URL,
        'http://' + SETTINGS.SOLR_HOST + ':8983/solr/{}/update?commit=true'.format(core)
    )
    curl_instance.setopt(curl_instance.HTTPPOST, [(
        'fileupload',
        (
            curl_instance.FORM_FILE,
            path_to_folder_file.format(output_file),
            curl_instance.FORM_CONTENTTYPE, 'application/json'
        )
    ),])
    curl_instance.perform()
    print('Минфин-документы проиндексированы через CURL')


def _add_automatic_key_words(documents):
    """Добавление автоматических ключевых слов с помощью TF-IDF"""

    matrix = _calculate_matrix(documents)
    for idx, doc in enumerate(documents):
        extra_key_words = _key_words_for_doc(idx, matrix)
        doc.lem_key_words += ' {}'.format(' '.join(extra_key_words))


def _tf(word, doc):
    """TF: частота слова в документе"""
    return doc.count(word)


def _documents_contain_word(word, doc_list):
    """количество документов, в которых встречается слово"""
    return 1 + sum(1 for document in doc_list if word in document.get_string_representation())


def _idf(word, doc_list):
    """
    IDF: логарифм от общего количества документов деленного
    на количество документов, в которых встречается слово
    """
    return math.log(len(doc_list) / float(_documents_contain_word(word, doc_list)))


def _tfidf(word, doc, doc_list):
    # TFхIDF
    return _tf(word, doc) * _idf(word, doc_list)


def _calculate_matrix(documents):
    # Словарь с рассчетами
    score = {}
    for idx, doc in enumerate(documents):
        doc_string_representation = doc.get_string_representation()
        tokens = set(doc_string_representation.split())
        score[idx] = []
        for token in tokens:
            score[idx].append({'term': token,
                               'tf': _tf(token, doc_string_representation),
                               'idf': _idf(token, documents),
                               'tfidf': _tfidf(token, doc_string_representation, documents)})

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


def _create_tests(files, data_frames):
    for file_name, df in zip(files, data_frames):
        file_path = r'tests\minfin_test_auto_for_{}.txt'.format(file_name.split('.')[0])
        with open(file_path, 'w', encoding='utf-8') as file_out:
            for index, row in df[['id', 'question']].iterrows():
                file_out.write('{}:{}\n'.format(row.question, row.id))
        #ToDo обработка ошибок открытия файлов


class ClassicMinfinDocument:
    def __init__(self):
        self.type = 'minfin'
        self.number = 0
        self.question = ''
        self.short_answer = ''
        self.full_answer = None
        self.lem_question = ''
        self.lem_synonym_questions = None
        self.lem_short_answer = ''
        self.lem_full_answer = None
        self.lem_key_words = ''
        self.link_name = None
        self.link = None
        self.picture_caption = None
        self.picture = None
        self.document_caption = None
        self.document = None

    def toJSON(self):
        return json.dumps(self, default=lambda obj: obj.__dict__, sort_keys=True, indent=4)

    def get_string_representation(self):
        # ToDo: WTF! Ветки if else идентичны
        if self.lem_full_answer:
            return self.lem_question + self.lem_full_answer
        else:
            return self.lem_question + self.lem_short_answer


_get_manual_synonym_questions('2.1')
