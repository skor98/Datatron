import json
import math
from text_preprocessing import TextPreprocessing
import uuid
import subprocess
from os import getcwd
from config import SETTINGS
import requests
import pycurl
import pandas as pd

input_data_file_name = 'data.xlsx'
output_file = 'minfin_data_for_indexing_in_solr.json'
solr_clear_req = 'http://localhost:8983/solr/{}/update?stream.body=%3Cdelete%3E%3Cquery%3E*:*%3C/query%3E%3C/delete%3E&commit=true'
path_to_folder_file = r'{}\{}'.format(SETTINGS.PATH_TO_MINFIN_ATTACHMENTS, {})


def set_up_minfin_core(index_way='curl'):
    minfin_docs = _refactor_data(_read_data())
    _add_automatic_key_words(minfin_docs)
    _write_data(minfin_docs)
    if index_way == 'curl':
        _index_data_via_curl()
    elif index_way == 'jar_file':
        _index_data_via_cmd()


def _read_data():
    data = pd.read_excel(open(path_to_folder_file.format(input_data_file_name), 'rb'), sheetname='questions')
    data = data.fillna(0)
    return data


def _write_data(data):
    with open(path_to_folder_file.format(output_file), 'w') as file:
        data_to_str = '[{}]'.format(','.join([element.toJSON() for element in data]))
        file.write(data_to_str)


def _refactor_data(data):
    tp = TextPreprocessing(uuid.uuid4())
    docs = []
    for index, row in data.iterrows():
        if not row.parameterized:
            doc = ClassicMinfinDocument()
            doc.question = row.question
            doc.lem_question = tp.normalization(row.question)
            doc.short_answer = row.short_answer
            doc.lem_short_answer = tp.normalization(row.short_answer)
            if row.full_answer:
                doc.full_answer = row.full_answer
                doc.lem_full_answer = tp.normalization(row.full_answer, delete_repeating_tokens=False)
            doc.lem_key_words = tp.normalization(row.key_words)
            if row.link_name:
                doc.link_name = row.link_name
                doc.link = row.link
            if row.picture:
                doc.picture = row.picture
            if row.document:
                doc.document = row.document
        # TODO: обработка параметризованного случая
        docs.append(doc)
    return docs


def _index_data_via_cmd():
    core = SETTINGS.SOLR_MINFIN_CORE
    path_to_json_data_file = path_to_folder_file.format(output_file)
    path_to_solr_jar_file = SETTINGS.PATH_TO_SOLR_POST_JAR_FILE

    requests.get(solr_clear_req.format(core))

    command = r'java -Dauto -Dc={} -Dfiletypes=json -jar {} {}'.format(core, path_to_solr_jar_file,
                                                                       path_to_json_data_file)
    subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).wait()
    print('Минфин-документы проиндексированы через JAR файл')


def _index_data_via_curl():
    core = SETTINGS.SOLR_MINFIN_CORE
    requests.get(solr_clear_req.format(core))

    c = pycurl.Curl()
    c.setopt(c.URL, 'http://localhost:8983/solr/{}/update?commit=true'.format(core))
    c.setopt(c.HTTPPOST,
             [
                 ('fileupload',
                  (c.FORM_FILE, path_to_folder_file.format(output_file),
                   c.FORM_CONTENTTYPE, 'application/json')
                  ),
             ])
    c.perform()
    print('Минфин-документы проиндексированы через CURL')


def _add_automatic_key_words(documents):
    matrix = _calculate_matrix(documents)
    for idx, doc in enumerate(documents):
        extra_key_words = _key_words_for_doc(idx, matrix)
        doc.lem_key_words += ' '.join(extra_key_words)


def _tf(word, doc):
    # TF: частота слова в документе
    return doc.count(word)


def _documents_contain_word(word, doc_list):
    # количество документов, в которых встречается слово
    return 1 + sum(1 for document in doc_list if word in document.get_string_representation())


def _idf(word, doc_list):
    # IDF: логарифм от общего количества документов деленного на количество документов, в которых встречается слово
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
        resulting_str = 'Doc: {} word: {} TF: {} IDF: {} TF-IDF: {}'
        print(resulting_str.format(document_id, word['term'], word['tf'], word['idf'], word['tfidf']))
        key_words.append(word['term'])
    return key_words


class ClassicMinfinDocument:
    def __init__(self):
        self.question = ''
        self.short_answer = ''
        self.full_answer = None
        self.lem_question = ''
        self.lem_short_answer = ''
        self.lem_full_answer = None
        self.lem_key_words = ''
        self.link_name = None
        self.link = None
        self.picture = None
        self.document = None

    def toJSON(self):
        return json.dumps(self, default=lambda obj: obj.__dict__, sort_keys=True, indent=4)

    def get_string_representation(self):
        if self.lem_full_answer:
            return self.lem_question + self.lem_full_answer
        else:
            return self.lem_question + self.lem_short_answer


class ParameterizedMinfinDocument:
    # TODO: доработать поля класса
    def __init__(self):
        self.question = ''
        self.short_answer = {}
        self.full_answer = {}
        self.lem_question = ''
        self.lem_short_answer = {}
        self.lem_full_answer = {}
        self.lem_key_words = ''
        self.link_name = None
        self.link = None
        self.picture = None
        self.document = None

    def toJSON(self):
        return json.dumps(self, default=lambda obj: obj.__dict__, sort_keys=True, indent=4)

    def get_string_representation(self):
        pass
