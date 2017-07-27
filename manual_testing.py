#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Содержит в себе CUI и классы для получения качества работы текущий алгоритмов.
Причём, это качество дОлжно быть легко узнаваемым из внешнего кода.
"""

import argparse
import json
import uuid
import datetime
import time
import logging
import re
from os import path, listdir, makedirs
from math import isnan
from statistics import mean

from data_retrieving import DataRetrieving
from config import DATETIME_FORMAT, LOG_LEVEL
from config import TEST_PATH_CUBE, TEST_PATH_MINFIN, TEST_PATH_RESULTS
import logs_helper
from logs_helper import string_to_log_level
from model_manager import MODEL_CONFIG

# Иначе много мусора по соединениям
logging.getLogger("requests").setLevel(logging.WARNING)

CURRENT_DATETIME_FORMAT = DATETIME_FORMAT.replace(' ', '_').replace(':', '-').replace('.', '-')


class QualityTester:
    """
    Содержит в себе логику запуска непосредственно тестов и вычисления общих метрик.
    Является основным классом, которого должно быть достаточно для внешних нужд.
    """

    def __init__(
            self,
            minimal_score=20,
            is_need_cube=True,
            is_need_minfin=True,
            is_need_logging=False
    ):
        if not is_need_cube and not is_need_minfin:
            raise Exception("Пустое тестирование! Нужно указать хотя бы чтот-то")

        self._testers = {}
        if is_need_cube:
            self._testers["cube"] = CubeTester(minimal_score, is_need_logging=is_need_logging)
        if is_need_minfin:
            self._testers["minfin"] = MinfinTester(minimal_score, is_need_logging=is_need_logging)
        self._is_need_logging = is_need_logging

    def run(self):
        """
        Главный метод взаимодействия с тестером
        """
        if not self._is_need_logging:
            # Временно отключаем логи
            logging.getLogger().setLevel(logging.ERROR)

        if "cube" in self._testers:
            cube_res = self._testers["cube"].run()
            cube_total = cube_res["true"] + cube_res["wrong"] + cube_res["error"]
            cube_score = float(cube_res["true"]) / cube_total
            cube_res["score"] = cube_score

        if "minfin" in self._testers:
            minfin_res = self._testers["minfin"].run()
            minfin_total = minfin_res["true"] + minfin_res["wrong"] + minfin_res["error"]
            minfin_score = float(minfin_res["true"]) / minfin_total
            minfin_res["score"] = minfin_score

        if not self._is_need_logging:
            # Возвращаем логи обратно
            logging.getLogger().setLevel(string_to_log_level(LOG_LEVEL))

        if "cube" not in self._testers:
            # только минфин; нормальный скоринг неприменим, поэтому возвращаем nan
            return float('nan'), {"minfin": minfin_res}
        elif "minfin" not in self._testers:
            # только кубы; нормальный скоринг неприменим, поэтому возвращаем nan
            return float('nan'), {"cube": cube_res}

        # Accuracy по всем результатам
        total_trues = cube_res["true"] + minfin_res["true"]
        total_tests = cube_total + minfin_total
        total_score = float(total_trues) / total_tests

        return total_score, {"cube": cube_res, "minfin": minfin_res}


class BaseTester:
    """
    Обеспечивает общие примитивы для тестирования кубов и минифина.
    Общие метрики и логики должны реализовываться именно здесь
    """

    def __init__(
            self,
            minimal_score,
            percentiles=tuple([25, 50, 75, 90, 95]),
            is_need_logging=False
    ):
        self._minimal_score = minimal_score
        self._percentiles = percentiles
        self._is_need_logging = is_need_logging

        self._trues = 0
        self._wrongs = 0
        self._errors = 0
        self._scores = []
        self._seconds = []
        self._text_results = []
        self._abs_confidences = []

    def get_minimal_score(self):
        """Возвращает пороговый score"""
        return self._minimal_score

    def _add_true(self):
        """Добавляет ещё один истинный результат"""
        self._trues += 1

    def get_trues(self):
        """Возвращает число истинных результатов"""
        return self._trues

    def _add_wrong(self):
        """Добавляет результат, ответ которого был неправильный"""
        self._wrongs += 1

    def get_wrongs(self):
        """Возвращает число ошибочных результатов"""
        return self._wrongs

    def _add_error(self):
        """Добавляет результат, при получении котрого была ошибка"""
        self._errors += 1

    def get_errors(self):
        """Возвращает число результатов, при обработке которых был ошибка"""
        return self._errors

    def _add_score(self, score: float):
        self._scores.append(score)

    def get_scores(self):
        return tuple(self._scores)

    def _add_absolute_confidence(self, val: float):
        self._abs_confidences.append(val)

    def get_absolute_confidences(self):
        """
        Возвращает разницы между правильным ответом и ближайшим к нему.
        Разница абсолютная!
        Гарантируются, что результирующий tuple не пуст
        """
        if not self._abs_confidences:
            # Вернём хоть что-то, иначе среднее не посчитать
            return tuple([0])
        return tuple(self._abs_confidences)

    def add_time(self, seconds: float):
        """Добавляет время, затраченное на получения результата"""
        self._seconds.append(seconds)

    def add_text_result(self, text: str):
        """Добавляет строчку для записи в логи"""
        self._text_results.append(text)

    def get_test_files_paths(self):
        """
        Возвращает последовательность путей к тестовым файлам.
        Должно быть переопределено.
        """
        raise NotImplementedError

    def get_results(self):
        """
        Считает все базовые статистики. Может быть переопределён для добавления новых
        """
        self._seconds.sort()
        return {
            "true": self.get_trues(),
            "wrong": self.get_wrongs(),
            "error": self.get_errors(),
            "MAC": mean(self.get_absolute_confidences()),
            "time": {
                per: self._seconds[round(len(self._seconds) * per / 100.)] for per in self._percentiles
            }
        }

    def get_log_filename_pattern(self):
        """
        Предполагается, что разные тесты могут писать в разные файлы
        Должен быть переопределён
        """
        raise NotImplementedError

    def before_test_run(self):
        """
        Нужно, чтобы что-то вывести в логи, подготовить какой-то кэш и т.д.
        Должен быть переопределён
        """
        raise NotImplementedError

    def write_log(self, time_to_write):
        """
        Записывает логи в файл. Используется старая реализация
        """
        if not self._is_need_logging:
            return

        file_name = self.get_log_filename_pattern()

        file_name = file_name.format(
            datetime.datetime.now().strftime(CURRENT_DATETIME_FORMAT),
            self.get_trues(),
            self.get_wrongs(),
            self.get_errors(),
            time_to_write
        )

        if not path.exists(TEST_PATH_RESULTS):
            makedirs(TEST_PATH_RESULTS)

        log_filename = path.join(TEST_PATH_RESULTS, file_name)
        with open(log_filename, 'w', encoding='utf-8') as file_out:
            file_out.write('\n'.join(self._text_results))

        logging.info('Тестирование завершено')
        logging.info('Лог прогона записан в файл {}'.format(file_name))

    def _check_result(self, idx, req, question_id, system_answer):
        """
        Проверяет результат теста.
        Должен быть переопределён
        """
        raise NotImplementedError

    def process_all(self, idx, req, question_id, system_answer):
        """
        Нужен для обработки статистик, общих для всех тестов,
        независимо от их результата.
        Может быть переопределён.
        """
        pass

    def process_true(self, idx, req, question_id, system_answer):
        """
        Нужен для обработки статистик, только по истинным тестам.
        Может быть переопределён.
        """
        # pylint: disable=unused-argument
        self._add_true()

        # self._add_score(system_answer['answer']['score'])

    def _get_nearest_result(self, system_answer):
        """
        Возвращает скор ближайшего результата или 0, если его нет
        """
        nearest_result = 0
        if system_answer["more_cube_answers"]:
            score_model = MODEL_CONFIG["cube_answers_scoring_model"]
            nearest_result = max(
                nearest_result,
                system_answer["more_cube_answers"][0]["score"][score_model]
            )
        if system_answer["more_minfin_answers"]:
            nearest_result = max(
                nearest_result,
                system_answer["more_minfin_answers"][0]["score"]
            )
        return nearest_result

    def process_wrong(self, idx, req, question_id, system_answer):
        """
        Нужен для обработки статистик, только по неверным тестам.
        Может быть переопределён.
        """
        # pylint: disable=unused-argument
        self._add_wrong()

    def process_error(self, idx, req, question_id, system_answer):
        """
        Нужен для обработки статистик, только по ошибочным запросам.
        Может быть переопределён.
        """
        # pylint: disable=unused-argument
        self._add_error()

    def run(self):
        """
        Запускает тестирование. Метод общий, но вызывает специфические
        для каждого тестирования методы, что позволяет реализовывать
        разное поведение.
        Переопределение не нужно
        """
        self.before_test_run()
        start_time = time.time()

        for test_path in self.get_test_files_paths():
            with open(test_path, 'r', encoding='utf-8') as file_in:
                doc_name_output_str = 'Файл: ' + path.basename(test_path)
                self.add_text_result(doc_name_output_str)
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

                    self._check_result(
                        idx,
                        req,
                        answer,
                        system_answer,
                    )

                    time_for_request = datetime.datetime.now() - dt_now
                    self.add_time(time_for_request.total_seconds())

        self.write_log(int(time.time() - start_time))
        return self.get_results()


class CubeTester(BaseTester):
    """
    Реализует логику и метрики, специфичные для кубов
    """
    def __init__(
            self,
            minimal_score,
            percentiles=tuple([25, 50, 75, 90, 95]),
            is_need_logging=False
    ):
        super().__init__(minimal_score, percentiles, is_need_logging)

    def get_test_files_paths(self):
        return get_test_files(TEST_PATH_CUBE, "cubes_test_mdx")

    def get_log_filename_pattern(self):
        return 'cube_{}.txt'

    def before_test_run(self):
        logging.info('Идет тестирование по вопросам к кубам')

    def process_true(self, idx, req, question_id, system_answer):
        """
        Добавляет Absolute Confidence, т.к. скор специфичен для минфина и кубов
        """
        super().process_true(idx, req, question_id, system_answer)

        score_model = MODEL_CONFIG["cube_answers_scoring_model"]

        nearest_result = self._get_nearest_result(system_answer)
        absolute_confidence = system_answer['answer']['score'][score_model] - nearest_result
        self._add_absolute_confidence(absolute_confidence)

    def _check_result(self, idx, req, answer, system_answer):
        response = system_answer['answer']

        if not response:
            ars = '{}. - Ответ на запрос "{}" не был найден'
            self.add_text_result(ars)
            self.process_wrong(idx, req, answer, system_answer)
            return

        response = response.get('mdx_query')
        if not response:
            ars = '{}. - Главный ответ на запрос "{}" - ответ по Минфину'.format(idx, req)
            self.add_text_result(ars)
            self.process_wrong(idx, req, answer, system_answer)
            return

        if self._mdx_queries_equality(answer, response):
            ars = '{}. + Запрос "{}" отрабатывает корректно'.format(idx, req)
            self.add_text_result(ars)
            self.process_true(idx, req, answer, system_answer)
        else:
            ars = (
                '{}. - Запрос "{}" отрабатывает некорректно' +
                '(должны получать: {}, получаем: {})'
            )
            ars = ars.format(
                idx,
                req,
                answer,
                response
            )

            self.add_text_result(ars)
            self.process_wrong(idx, req, answer, system_answer)

    def _mdx_queries_equality(self, mdx_query1, mdx_query2):
        """Проверка равенства двух MDX-запросов"""

        measure_p = re.compile(r'(?<=\[MEASURES\]\.\[)\w*')
        cube_p = re.compile(r'(?<=FROM \[)\w*')
        members_p = re.compile(r'(\[\w+\]\.\[[0-9-]*\])')

        def get_measure(mdx_query):
            """Получение регуляркой меры"""
            return measure_p.search(mdx_query).group()

        def get_cube(mdx_query):
            """Получение регуляркой куба"""
            return cube_p.search(mdx_query).group()

        def get_members(mdx_query):
            """Получение регуляркой элементов измерений"""
            return members_p.findall(mdx_query)

        mdx_query1 = mdx_query1.upper()
        mdx_query2 = mdx_query2.upper()

        q1_measure, q1_cube, q1_members = (
            get_measure(mdx_query1),
            get_cube(mdx_query1),
            get_members(mdx_query1)
        )

        q2_measure, q2_cube, q2_members = (
            get_measure(mdx_query2),
            get_cube(mdx_query2),
            get_members(mdx_query2)
        )

        measure_equal = (q1_measure == q2_measure)
        cube_equal = (q1_cube == q2_cube)

        # игнорирование порядка элементов измерений
        members_equal = (set(q1_members) == set(q2_members))

        return bool(measure_equal and cube_equal and members_equal)


class MinfinTester(BaseTester):
    """
    Реализует логику и метрики, специфичные для минфина.
    """

    def __init__(
            self,
            minimal_score,
            percentiles=tuple([25, 50, 75, 90, 95]),
            is_need_logging=False
    ):
        super().__init__(minimal_score, percentiles, is_need_logging)
        self._threshold_confidences = []

    def _add_threshold_confidence(self, val: float):
        self._threshold_confidences.append(val)

    def get_threshold_confidences(self):
        return tuple(self._threshold_confidences)

    def get_test_files_paths(self):
        return get_test_files(TEST_PATH_MINFIN, "minfin_test")

    def get_log_filename_pattern(self):
        return 'minfin_{}.txt'

    def before_test_run(self):
        logging.info('Идет тестирование по вопросам для Министерства Финансов')

    def get_results(self):
        """
        Добавляет дополнительно Mean Threshold Confidence к статистикам
        """
        res = super().get_results()

        # Mean Threshold Confidence
        res["MTC"] = mean(self.get_threshold_confidences())

        return res

    def process_true(self, idx, req, question_id, system_answer):
        """
        Добавляет Absolute Confidence, т.к. скор специфичен для минфина и кубов
        Также добавляет Threshold Confidence
        """
        super().process_true(idx, req, question_id, system_answer)

        nearest_result = self._get_nearest_result(system_answer)
        absolute_confidence = system_answer['answer']['score'] - nearest_result
        self._add_absolute_confidence(absolute_confidence)

        self._add_threshold_confidence(system_answer['answer']['score'] - self._minimal_score)

    def _check_result(self, idx, req, question_id, system_answer):
        response = system_answer['answer']
        if not response:
            ars = '{q_id} - Запрос "{req}" вызвал ошибку: {msg}'.format(
                q_id=question_id,
                req=req,
                msg='Не определена'
            )

            self.add_text_result(ars)
            self.process_error(idx, req, question_id, system_answer)
            return

        if not response:
            ars = (
                '{q_id} - На запрос "{req}" ответ не был найден ' +
                'или, он не прошел по порогу'
            )
            ars = ars.format(q_id=question_id, req=req)
            self.add_text_result(ars)
            self.process_error(idx, req, question_id, system_answer)
            return

        response = response.get('number')
        if not response:
            ars = '{q_id} - Запрос "{req}" вызвал ошибку: {msg}'.format(
                q_id=question_id,
                req=req,
                msg='Не определена'
            )
            self.add_text_result(ars)
            self.process_error(idx, req, question_id, system_answer)
            return

        if question_id == str(response) and self._minimal_score < system_answer['answer']['score']:
            ars = '{q_id} + {score} Запрос "{req}" отрабатывает корректно'
            ars = ars.format(q_id=question_id,
                             score=system_answer['answer']['score'],
                             req=req)
            self.add_text_result(ars)
            self.process_true(idx, req, question_id, system_answer)
        else:
            ars = (
                '{q_id} - {score} Запрос "{req}" отрабатывает некорректно ' +
                '(должны получать:{q_id}, получаем:{fl})'
            )
            ars = ars.format(q_id=question_id,
                             score=system_answer['answer']['score'],
                             req=req, fl=response)
            self.add_text_result(ars)
            self.process_wrong(idx, req, question_id, system_answer)


def get_test_files(test_path, prefix):
    """
    Генератор путей к файлам с указанымм префиксом
    """
    for file_name in listdir(test_path):
        if file_name.startswith(prefix):
            yield path.join(test_path, file_name)


@logs_helper.time_with_message("get_results")
def get_results(
        minimal_score=20,
        need_cube=True,
        need_minfin=True,
        write_logs=False
):
    """
    Возвращает результаты по всем тестам.
    Сначала общий скор, потом детальный скор
    На данный момент, общий скор -- accuracy
    Если write_logs=False, то логи не пишутся
    :return: score, {"cube": cube_results,"minfin":minfin_results}
    """

    tester = QualityTester(
        minimal_score=minimal_score,
        is_need_cube=need_cube,
        is_need_minfin=need_minfin,
        is_need_logging=write_logs
    )

    return tester.run()


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

    parser.add_argument(
        "--threshold", help='Score для отсева ответов.',
        default=20., type=float
    )

    args = parser.parse_args()

    # Если аргументов не было, то тестируем как обычно
    if not args.cube and not args.minfin:
        args.cube = True
        args.minfin = True

    score, results = get_results(
        minimal_score=args.threshold,
        need_cube=args.cube,
        need_minfin=args.minfin,
        write_logs=not args.no_logs
    )
    current_datetime = datetime.datetime.now().strftime(CURRENT_DATETIME_FORMAT)
    result_file_name = "results_{}.json".format(current_datetime)
    with open(path.join(TEST_PATH_RESULTS, result_file_name), 'w') as f_out:
        json.dump(results, f_out, indent=4)
    print("Results: {}".format(json.dumps(results, indent=4)))
    if not isnan(score):
        print("Score: {:.4f}".format(score))


if __name__ == "__main__":
    _main()
