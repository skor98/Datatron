#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import uuid
import datetime
from os import getcwd, listdir

import requests

from data_retrieving import DataRetrieving


def post_request_to_server(request):
    return requests.post('http://api.datatron.ru/test', {"Request": request})


def cube_testing(local=True, test_sphere='cube'):
    """Метод для тестирования работы системы по кубам.
    Тесты находятся в папке tests и имеют следующую структуру названия
    cube_<local/server>_<имя куба>

    :param local: если True, то тестируется локальная система, если False, то стоящая на сервере
    :return: None
    """
    test_path = r'{}\{}'.format(getcwd(), 'tests')
    testing_results = []
    true_answers = []

    if test_sphere == 'cube':
        test_files_paths = get_test_files(test_path, "cubes_test")
    else:
        test_files_paths = get_test_files(test_path, "minfin_test")

    for tf in test_files_paths:
        with open(r'{}'.format(tf), 'r', encoding='utf-8') as file_in:
            doc_name_output_str = 'Файл: {}'.format(tf.split('\\')[-1])
            testing_results.append(doc_name_output_str)
            print(doc_name_output_str)

            for idx, line in enumerate(file_in):
                line = ' '.join(line.split())

                if line.startswith('*'):
                    continue

                req, answer = line.split(':')
                if local:
                    system_answer = json.loads(DataRetrieving.get_data(
                        req, uuid.uuid4(),
                        formatted=False
                    ).toJSON())
                else:
                    system_answer = post_request_to_server(req).json()

                if test_sphere == 'cube':
                    assert_cube_requests(idx, req, answer, system_answer, testing_results, true_answers)
                else:
                    assert_minfin_requests(answer, req, system_answer, testing_results, true_answers)

    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    true_answers = sum(true_answers)
    false_answers = len(testing_results) - true_answers - len(test_files_paths)

    if test_sphere == 'cube':
        file_name = 'cube_{}_{}_OK_{}_Fail_{}.txt'
    else:
        file_name = 'minfin_{}_{}_OK_{}_Fail_{}.txt'

    if local:
        file_name = file_name.format('local', current_datetime, true_answers, false_answers)
    else:
        file_name = file_name.format('server', current_datetime, true_answers, false_answers)

    with open(r'{}\{}'.format(test_path, file_name), 'w', encoding='utf-8') as file_out:
        file_out.write('\n'.join(testing_results))

    print('Лог прогона записан в файл {}'.format(file_name))


def assert_cube_requests(idx, req, answer, system_answer, testing_results, true_answers):
    response = system_answer['cube_documents']['response']
    if response:
        try:
            assert int(answer) == response
            ars = '{}. + Запрос "{}" отрабатывает корректно'.format(idx, req)
            testing_results.append(ars)
            true_answers.append(1)
            print(ars)
        except AssertionError:
            ars = (
                '{}. - Запрос "{}" отрабатывает некорректно' +
                '(должны получать: {}, получаем: {})'
            )
            ars = ars.format(idx, req, int(answer), response)
            testing_results.append(ars)
            print(ars)
    else:
        ars = '{}. - Запрос "{}" вызвал ошибку: {}'
        ars = ars.format(idx, req, system_answer['message'])
        testing_results.append(ars)
        print(ars)


def assert_minfin_requests(question_id, req, system_answer, testing_results, true_answers):
    response = system_answer['minfin_documents']['number']
    if response:
        try:
            assert question_id == str(response)
            ars = '{q_id}  + Запрос "{req}" отрабатывает корректно'
            ars = ars.format(q_id=question_id, req=req)
            testing_results.append(ars)
            true_answers.append(1)
        except AssertionError:
            ars = (
                '{q_id} - Запрос "{req}" отрабатывает некорректно ' +
                '(должны получать:{q_id}, получаем:{fl})'
            )
            ars = ars.format(q_id=question_id, req=req, fl=response)
            testing_results.append(ars)
    else:
        # TODO: подправить MSG
        ars = '{q_id}  - Запрос "{req}" вызвал ошибку: {msg}'.format(
            q_id=question_id,
            req=req,
            msg='Не определена'
        )
        testing_results.append(ars)
        print(ars)


def get_test_files(test_path, prefix):
    test_files_paths = []
    for file in listdir(test_path):
        if file.startswith(prefix):
            test_files_paths.append(r'{}\{}'.format(test_path, file))
    return test_files_paths


if __name__ == "__main__":
    cube_testing(test_sphere='cube')
    cube_testing(test_sphere='minfin')
