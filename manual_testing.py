#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import uuid
import datetime
import time
import logging
from os import path, listdir

from data_retrieving import DataRetrieving
from config import DATETIME_FORMAT
import logs_helper

CURRENT_DATETIME_FORMAT = DATETIME_FORMAT.replace(' ', '_').replace(':', '-').replace('.', '-')


def cube_testing(test_sphere='cube'):
    """Метод для тестирования работы системы по кубам.
    Тесты находятся в папке tests и имеют следующую структуру названия
    cube_<local/server>_<имя куба>

    :param local: если True, то тестируется локальная система, если False, то стоящая на сервере
    :return: None
    """
    test_path = 'tests'
    testing_results = []
    true_answers = []
    wrong_answers = []
    error_answers = []
    start_time = time.time()

    if test_sphere == 'cube':
        test_files_paths = get_test_files(test_path, "cubes_test")
        logging.info('Идет тестирование по вопросам к кубам')
    else:
        test_files_paths = get_test_files(test_path, "minfin_test")
        logging.info('Идет тестирование по вопросам для Министерства Финансов')

    for tf in test_files_paths:
        with open(tf, 'r', encoding='utf-8') as file_in:
            doc_name_output_str = 'Файл: ' + path.basename(tf)
            testing_results.append(doc_name_output_str)
            logging.info(doc_name_output_str)

            for idx, line in enumerate(file_in):
                line = ' '.join(line.split())

                if line.startswith('*'):
                    continue

                logging.info(line)
                req, answer = line.split(':')

                system_answer = json.loads(DataRetrieving.get_data(
                    req, uuid.uuid4(),
                    formatted=False
                ).toJSON())

                if test_sphere == 'cube':
                    assert_cube_requests(
                        idx,
                        req,
                        answer,
                        system_answer,
                        testing_results,
                        true_answers,
                        wrong_answers,
                        error_answers
                    )
                else:
                    assert_minfin_requests(
                        answer,
                        req,
                        system_answer,
                        testing_results,
                        true_answers,
                        wrong_answers,
                        error_answers
                    )

    current_datetime = datetime.datetime.now().strftime(CURRENT_DATETIME_FORMAT)

    true_answers = sum(true_answers)
    wrong_answers = sum(wrong_answers)
    error_answers = sum(error_answers)

    if test_sphere == 'cube':
        file_name = 'cube_{}_OK_{}_Wrong_{}_Error_{}_Time_{}.txt'
    else:
        file_name = 'minfin_{}_OK_{}_Wrong_{}_Error_{}_Time_{}.txt'

    file_name = file_name.format(current_datetime,
                                 true_answers,
                                 wrong_answers,
                                 error_answers,
                                 int(time.time() - start_time))

    with open(path.join(test_path, 'results', file_name), 'w', encoding='utf-8') as file_out:
        file_out.write('\n'.join(testing_results))

    logging.info('Тестирование завершено')
    logging.info('Лог прогона записан в файл {}'.format(file_name))


def assert_cube_requests(idx, req, answer, system_answer, testing_results, true_answers, wrong_answers, error_answers):
    response = system_answer['cube_documents']['response']
    if response:
        try:
            assert int(answer) == response
            ars = '{}. + Запрос "{}" отрабатывает корректно |'.format(idx, req)
            testing_results.append(ars)
            true_answers.append(1)
        except AssertionError:
            ars = (
                '{}. - Запрос "{}" отрабатывает некорректно' +
                '(должны получать: {}, получаем: {}) | {}'
            )
            ars = ars.format(idx,
                             req, int(answer),
                             response,
                             system_answer['cube_documents']['mdx_query'])

            testing_results.append(ars)
            wrong_answers.append(1)
    else:
        ars = '{}. - Запрос "{}" вызвал ошибку: {} | {}'
        ars = ars.format(idx,
                         req,
                         system_answer['cube_documents']['message'],
                         system_answer['cube_documents']['mdx_query'])
        testing_results.append(ars)
        error_answers.append(1)


def assert_minfin_requests(question_id, req, system_answer, testing_results, true_answers, wrong_answers,
                           error_answers):
    response = system_answer['minfin_documents']['number']
    if response:
        try:
            assert question_id == str(response)
            ars = '{q_id} + {score} Запрос "{req}" отрабатывает корректно'
            ars = ars.format(q_id=question_id,
                             score=system_answer['minfin_documents']['score'],
                             req=req)
            testing_results.append(ars)
            true_answers.append(1)
        except AssertionError:
            ars = (
                '{q_id} - {score} Запрос "{req}" отрабатывает некорректно ' +
                '(должны получать:{q_id}, получаем:{fl})'
            )
            ars = ars.format(q_id=question_id,
                             score=system_answer['minfin_documents']['score'],
                             req=req, fl=response)
            testing_results.append(ars)
            wrong_answers.append(1)
    else:
        # TODO: подправить MSG
        ars = '{q_id} - Запрос "{req}" вызвал ошибку: {msg}'.format(
            q_id=question_id,
            req=req,
            msg='Не определена'
        )
        testing_results.append(ars)
        error_answers.append(1)


def get_test_files(test_path, prefix):
    test_files_paths = []
    for file in listdir(test_path):
        if file.startswith(prefix):
            test_files_paths.append(path.join(test_path, file))
    return test_files_paths


if __name__ == "__main__":
    cube_testing(test_sphere='cube')
    cube_testing(test_sphere='minfin')
