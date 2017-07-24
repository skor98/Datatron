#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import json
import uuid
import datetime
import time
import logging
from os import path, listdir, makedirs
from math import isnan

from data_retrieving import DataRetrieving
from config import DATETIME_FORMAT, LOG_LEVEL
import logs_helper
from logs_helper import string_to_log_level

logging.getLogger("requests").setLevel(logging.WARNING)

CURRENT_DATETIME_FORMAT = DATETIME_FORMAT.replace(' ', '_').replace(':', '-').replace('.', '-')
TEST_PATH = 'tests'
RESULTS_FOLDER = 'results'


@logs_helper.time_with_message("cube_testing")
def cube_testing(test_sphere='cube'):
    """Метод для тестирования работы системы по кубам.
    Тесты находятся в папке tests и имеют следующую структуру названия
    cube_<local/server>_<имя куба>

    :return: Словарь с ключами true, long, error и значениями -- количеством документов
    Также ключ time содержит перцентили по времени выполнения запроса
    """

    testing_results = []
    true_answers = []
    wrong_answers = []
    error_answers = []
    seconds = []
    start_time = time.time()

    if test_sphere == 'cube':
        test_files_paths = get_test_files(TEST_PATH, "cubes_test")
        logging.info('Идет тестирование по вопросам к кубам')
    else:
        test_files_paths = get_test_files(TEST_PATH, "minfin_test")
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

                # Посчитаем время
                dt_now = datetime.datetime.now()
                system_answer = json.loads(DataRetrieving.get_data(
                    req, uuid.uuid4()
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
                time_for_request = datetime.datetime.now() - dt_now
                seconds.append(time_for_request.total_seconds())

    current_datetime = datetime.datetime.now().strftime(CURRENT_DATETIME_FORMAT)

    true_answers = sum(true_answers)
    wrong_answers = sum(wrong_answers)
    error_answers = sum(error_answers)

    if test_sphere == 'cube':
        file_name = 'cube_{}_OK_{}_Wrong_{}_Error_{}_Time_{}.txt'
    else:
        file_name = 'minfin_{}_OK_{}_Wrong_{}_Error_{}_Time_{}.txt'

    file_name = file_name.format(
        current_datetime,
        true_answers,
        wrong_answers,
        error_answers,
        int(time.time() - start_time)
    )

    # создание папки для тестов
    if not path.exists(path.join(TEST_PATH, RESULTS_FOLDER)):
        makedirs(path.join(TEST_PATH, RESULTS_FOLDER))

    with open(path.join(TEST_PATH, RESULTS_FOLDER, file_name), 'w', encoding='utf-8') as file_out:
        file_out.write('\n'.join(testing_results))

    logging.info('Тестирование завершено')
    logging.info('Лог прогона записан в файл {}'.format(file_name))

    # Подготавливаемся для счёта перцентилей
    seconds.sort()

    return {
        "true": true_answers,
        "wrong": wrong_answers,
        "error": error_answers,
        "time": {
            "25": seconds[round(len(seconds) * 0.25)],
            "50": seconds[round(len(seconds) * 0.50)],
            "75": seconds[round(len(seconds) * 0.75)],
            "90": seconds[round(len(seconds) * 0.90)],
            "95": seconds[round(len(seconds) * 0.95)]
        }
    }


def assert_cube_requests(
        idx,
        req,
        answer,
        system_answer,
        testing_results,
        true_answers,
        wrong_answers,
        error_answers
):
    response = system_answer['answer'].get('response')
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
                             system_answer['answer']['mdx_query'])

            testing_results.append(ars)
            wrong_answers.append(1)
    else:
        if system_answer['doc_found']:
            ars = '{}. - Запрос "{}" выдал верхним ответ по Минфину'
            ars = ars.format(idx, req)
        else:
            ars = '{}. - Запрос "{}" вызвал ошибку: {} | {}'
            ars = ars.format(idx,
                             req,
                             system_answer['answer']['message'],
                             system_answer['answer']['mdx_query'])
        testing_results.append(ars)
        error_answers.append(1)


def assert_minfin_requests(
        question_id,
        req,
        system_answer,
        testing_results,
        true_answers,
        wrong_answers,
        error_answers
):
    response = system_answer['answer']
    if response:
        response = response.get('number')
        if response:
            try:
                assert question_id == str(response)
                ars = '{q_id} + {score} Запрос "{req}" отрабатывает корректно'
                ars = ars.format(q_id=question_id,
                                 score=system_answer['answer']['score'],
                                 req=req)
                testing_results.append(ars)
                true_answers.append(1)
            except AssertionError:
                ars = (
                    '{q_id} - {score} Запрос "{req}" отрабатывает некорректно ' +
                    '(должны получать:{q_id}, получаем:{fl})'
                )
                ars = ars.format(q_id=question_id,
                                 score=system_answer['answer']['score'],
                                 req=req, fl=response)
                testing_results.append(ars)
                wrong_answers.append(1)
        else:
            if system_answer['doc_found']:
                ars = '{q_id} - Запрос "{req}" вызвал ошибку: {msg}'.format(
                    q_id=question_id,
                    req=req,
                    msg='Вверхним документом был ответ по кубу'
                )
            else:
                ars = '{q_id} - Запрос "{req}" вызвал ошибку: {msg}'.format(
                    q_id=question_id,
                    req=req,
                    msg='Не определена'
                )
    else:
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


@logs_helper.time_with_message("get_results")
def get_results(need_cube=True, need_minfin=True, write_logs=False):
    """
    Возвращает результаты по всем тестам.
    Сначала общий скор, потом детальный скор
    На данный момент, общий скор -- accuracy
    Если write_logs=False, то логи не пишутся
    :return: score, {"cube": cube_results,"minfin":minfin_results}
    """
    if not write_logs:
        # Временно отключаем логи
        logging.getLogger().setLevel(logging.ERROR)

    if need_cube:
        cube_res = cube_testing(test_sphere='cube')
        cube_total = cube_res["true"] + cube_res["wrong"] + cube_res["error"]
        cube_score = float(cube_res["true"]) / cube_total
        cube_res["score"] = cube_score

    if need_minfin:
        minfin_res = cube_testing(test_sphere='minfin')
        minfin_total = minfin_res["true"] + minfin_res["wrong"] + minfin_res["error"]
        minfin_score = float(minfin_res["true"]) / minfin_total
        minfin_res["score"] = minfin_score

    if not write_logs:
        # Возвращаем логи обратно
        logging.getLogger().setLevel(string_to_log_level(LOG_LEVEL))

    if not need_cube:
        # только минфин; нормальный скоринг неприменим, поэтому возвращаем nan
        return float('nan'), {"minfin": minfin_res}
    elif not need_minfin:
        # только кубы; нормальный скоринг неприменим, поэтому возвращаем nan
        return float('nan'), {"cube": cube_res}
    else:
        # Accuracy по всем результатам
        total_trues = cube_res["true"] + minfin_res["true"]
        total_tests = cube_total + minfin_total
        total_score = float(total_trues) / total_tests

        return total_score, {"cube": cube_res, "minfin": minfin_res}


def _main():
    # pylint: disable=invalid-name
    parser = argparse.ArgumentParser(
        description="""Проводит тестирование качества системы.
        Если аргументов нет, то будет тестирование всего.
        """
    )

    parser.add_argument(
        "--cube",
        action='store_true',
        help='Проводит только тестирование по кубам',
    )

    parser.add_argument(
        "--minfin",
        action='store_true',
        help='Проводит только тестирование по минфину',
    )

    parser.add_argument(
        "--no-logs",
        action='store_true',
        help='Отключает логгирование во время тестирования',
    )

    args = parser.parse_args()

    # Если аргументов не было, то тестируем как обычно
    if not args.cube and not args.minfin:
        args.cube = True
        args.minfin = True

    score, results = get_results(
        need_cube=args.cube,
        need_minfin=args.minfin,
        write_logs=not args.no_logs
    )
    current_datetime = datetime.datetime.now().strftime(CURRENT_DATETIME_FORMAT)
    result_file_name = "results_{}.json".format(current_datetime)
    with open(path.join(TEST_PATH, RESULTS_FOLDER, result_file_name), 'w') as f_out:
        json.dump(results, f_out, indent=4)
    print("Results: {}".format(json.dumps(results, indent=4)))
    if not isnan(score):
        print("Score: {:.4f}".format(score))


if __name__ == "__main__":
    _main()
