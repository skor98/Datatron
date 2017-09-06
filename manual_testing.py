#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Содержит в себе CUI и классы для получения качества работы текущий алгоритмов.
Причём, это качество дОлжно быть легко узнаваемым из внешнего кода.

Сами тесты имеют вид:
Запрос1:Результат1
Запрос2:Результат2
для кубов Результат -- MDX запрос, а для минфина -- номер документа
Если Результат = idk, то считается, что система не должна что-либо возвращать
"""

import argparse
import datetime
import json
import logging
from math import isnan
from os import path, listdir, makedirs
import re
from statistics import mean, StatisticsError
import time

import uuid

from config import DATETIME_FORMAT, LOG_LEVEL
from config import TEST_PATH_CUBE, TEST_PATH_MINFIN, TEST_PATH_RESULTS
from config import WRONG_AUTO_MINFIN_TESTS_FILE
from data_retrieving import DataRetrieving
from logs_helper import string_to_log_level
import logs_helper
from model_manager import MODEL_CONFIG
from model_manager import set_default_model, restore_default_model

# Иначе много мусора по соединениям
logging.getLogger("requests").setLevel(logging.WARNING)

CURRENT_DATETIME_FORMAT = DATETIME_FORMAT.replace(' ', '_').replace(':', '-').replace('.', '-')

# Если система не должна выдавать ответа, "я не знаю"
IDK_STRING = "idk"


def safe_mean(values):
    """
    Аналогичен statistics.mean, но возвращает NaN в случае пустого входа
    """
    try:
        return mean(values)
    except StatisticsError:
        logging.warning("подсчёт среднего ПУСТОГО массива")
        return float("NaN")


def get_jaccard(s1: set, s2: set):
    """
    Возвращает меру Жаккара между множествами a и b \in [0,1]
    Много -- хорошо.
    """
    return len(s1.intersection(s2)) / len(s1.union(s2))


class AccuracyScoreHelper:
    """Инкапсулирует вычисление точности (accuracy)."""

    def __init__(self):
        self._trues = 0
        self._falses = 0

    def add_true(self):
        self._trues += 1

    def add_false(self):
        self._falses += 1

    def add(self, val: bool):
        """Добавляет True или False в заивисимости от значения val"""
        if val:
            self.add_true()
        else:
            self.add_false()

    def get_score(self):
        total = self._trues + self._falses
        return float(self._trues) / total


class QualityTester:
    """
    Содержит в себе логику запуска непосредственно тестов и вычисления общих метрик.
    Является основным классом, которого должно быть достаточно для внешних нужд.
    """

    def __init__(
            self,
            is_need_cube=True,
            is_need_minfin=True,
            is_need_logging=False
    ):
        if not is_need_cube and not is_need_minfin:
            raise Exception("Пустое тестирование! Нужно указать хотя бы чтот-то")

        self._testers = {}
        if is_need_cube:
            self._testers["cube"] = CubeTester(is_need_logging=is_need_logging)
        if is_need_minfin:
            self._testers["minfin"] = MinfinTester(is_need_logging=is_need_logging)
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
            percentiles=tuple([25, 50, 75, 90, 95]),
            is_need_logging=False
    ):
        self._percentiles = percentiles
        self._is_need_logging = is_need_logging

        self._trues = 0
        self._wrongs = 0
        self._errors = 0
        self._scores = []
        self._seconds = []
        self._text_results = []
        self._abs_confidences = []

        self._threshold = MODEL_CONFIG["relevant_minfin_main_answer_threshold"]

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
        """
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
            "MAC": safe_mean(self.get_absolute_confidences()),
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

    def write_log(self):
        """
        Записывает логи в файл. Используется старая реализация
        """
        if not self._is_need_logging:
            return

        file_name = self.get_log_filename_pattern()

        file_name = file_name.format(
            datetime.datetime.now().strftime(CURRENT_DATETIME_FORMAT),
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
        system_answer = None соответствует idk результату
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
        Переорпределяет MODEL_CONFIG["relevant_minfin_main_answer_threshold"]
        на время тестирования в 0
        Переопределение не нужно
        """
        MODEL_CONFIG["relevant_minfin_main_answer_threshold"] = 0
        set_default_model(MODEL_CONFIG)

        self.before_test_run()
        start_time = time.time()

        for test_path in self.get_test_files_paths():
            with open(test_path, 'r', encoding='utf-8') as file_in:
                doc_name_output_str = 'Файл: ' + path.basename(test_path)
                self.add_text_result(doc_name_output_str)
                logging.info(doc_name_output_str)

                for idx, line in enumerate(file_in):
                    line = line.strip()

                    if not line or line.startswith('*'):
                        continue

                    line = ' '.join(line.split())
                    logging.info(line)

                    req, answer = line.split(':')

                    if answer.lower() == IDK_STRING:
                        # если это idk строка, то дальше передаём None
                        answer = None

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

        time_delta = time.time() - start_time
        self.write_log()

        # Честное тестирование - тестирование с выключенным параметром
        # При нем также будут записываться вопросы, которые не работают

        # При включенном параметре результаты тестов будут всегда выше,
        # так как автоматические тесты всегда буду работать
        # При включенном параметре файл с неработающими автомат. тестами
        # по минфину обновляться не будут
        if not MODEL_CONFIG["use_local_file_processing_for_minfin"]:
            if isinstance(self, MinfinTester):
                bad_mifin_query = re.compile(r'Запрос\s*"(.+)"\s*отрабатывает некорректно')
                should_get_number = re.compile(r'должны получать:(\d+(\.\d+)+)')

                type_of_test = 0
                only_wrong_manual_tests = {}

                for res in self._text_results:
                    if 'manual' in res:
                        type_of_test = 0
                    elif any(test_type in res for test_type in ('auto', 'extra')):
                        type_of_test = 1
                    else:
                        if type_of_test:
                            questions = bad_mifin_query.findall(res)
                            if questions:
                                question = questions[0].lower().replace('?', '')
                                only_wrong_manual_tests[question] = should_get_number.search(res).group(1)

                log_filename = path.join(TEST_PATH_RESULTS, WRONG_AUTO_MINFIN_TESTS_FILE)
                with open(log_filename, 'w', encoding='utf-8') as file_out:
                    file_out.write(json.dumps(
                        only_wrong_manual_tests,
                        ensure_ascii=False,
                        indent=4
                    ))

        logging.info("{} takes {} seconds".format(self.__class__.__name__, time_delta))

        restore_default_model()  # Возвращаем данные модели

        return self.get_results()


class CubeTester(BaseTester):
    """
    Реализует логику и метрики, специфичные для кубов
    """

    def __init__(
            self,
            percentiles=tuple([25, 50, 75, 90, 95]),
            is_need_logging=False
    ):
        super().__init__(percentiles, is_need_logging)

        self._only_cube = AccuracyScoreHelper()
        self._only_measure = AccuracyScoreHelper()

        self._members_jaccard = 0

        self._wrong_minfins = 0

    def _add_wrong_minfin(self):
        """Добавляет результат, когда мы нашли минфин вместо куба"""
        self._wrong_minfins += 1

    def get_wrong_minfins(self):
        """Возвращает число результатов, когда мы нашли минфин вместо куба"""
        return self._wrong_minfins

    def _add_members_jackard(self, val):
        """Добавляет ещё одно расстояние Жаккара у внутренней сумме по измерениям"""
        self._members_jaccard += val

    def get_members_jaccard(self):
        """Возвращает среднюю меру Жаккара по измерениям"""
        return self._members_jaccard / (self.get_trues() + self.get_wrongs())

    def get_test_files_paths(self):
        return get_test_files(TEST_PATH_CUBE, "cubes_test_mdx")

    def get_log_filename_pattern(self):
        return 'cube_{}.txt'

    def before_test_run(self):
        logging.info('Идет тестирование по вопросам к кубам')

    def process_wrong(self, idx, req, question_id, system_answer):
        """
        Добавляет число неверных результатов, когда минфин вместо куба
        """
        super().process_wrong(idx, req, question_id, system_answer)

        try:
            if system_answer["answer"]["type"] == "minfin":
                self._add_wrong_minfin()
        except KeyError:
            # результата может не быть вовсе
            pass
        except TypeError:
            pass

    def process_true(self, idx, req, question_id, system_answer):
        """
        Добавляет Absolute Confidence, т.к. скор специфичен для минфина и кубов
        """
        super().process_true(idx, req, question_id, system_answer)

        score_model = MODEL_CONFIG["cube_answers_scoring_model"]

        nearest_result = self._get_nearest_result(system_answer)
        absolute_confidence = system_answer['answer']['score'][score_model] - nearest_result
        self._add_absolute_confidence(absolute_confidence)

    def get_results(self):
        """
        Добавляет дополнительно точность ТОЛЬКО по определению куба из запроса
        """
        res = super().get_results()

        # Точность ТОЛЬКО по определению куба
        res["onlycubeAcc"] = self._only_cube.get_score()

        # Точность ТОЛЬКО по определению МЕРЫ
        res["onlymeasureAcc"] = self._only_measure.get_score()

        # Средняя мера Жаккарда по измерениям. Чем ближе к 1, тем лучше
        res["onlymembersJacc"] = self.get_members_jaccard()

        # Какая часть неверных результатов из-за того, что ответ по минфину
        res["wrongMinfin"] = self.get_wrong_minfins() / self.get_wrongs()

        return res

    def _check_result(self, idx, req, answer, system_answer):
        response = system_answer['answer']

        if not response:
            ars = '{}.\t-\t{}\tОтвет не был найден'
            self.add_text_result(ars)
            self.process_wrong(idx, req, answer, system_answer)
            return

        response = response.get('mdx_query')
        if not response:
            ars = '{}\t-\t{}\t\tГлавный ответ по Минфину'.format(idx, req)
            self.add_text_result(ars)
            self.process_wrong(idx, req, answer, system_answer)
            return

        if self._mdx_queries_equality(answer, response):
            ars = '{}.\t+\t{}'.format(idx, req)
            self.add_text_result(ars)
            self.process_true(idx, req, answer, system_answer)
        else:
            ars = (
                '{}.\t-\t{}\tВместо {} получаем: {}'
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
        members_p = re.compile(r'(\[\w+(?<!MEASURES)\]\.(?:\[[0-9-]*\]|\[\w+\]))')

        def get_measure(mdx_query):
            """Получение регуляркой меры"""
            return measure_p.search(mdx_query).group()

        def get_cube(mdx_query):
            """Получение регуляркой куба"""
            return cube_p.search(mdx_query).group()

        def get_members(mdx_query):
            """Получение регуляркой элементов измерений"""
            return set(members_p.findall(mdx_query))

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
        self._only_measure.add(measure_equal)

        cube_equal = (q1_cube == q2_cube)
        self._only_cube.add(cube_equal)

        # игнорирование порядка элементов измерений
        members_equal = (q1_members == q2_members)

        self._add_members_jackard(get_jaccard(q1_members, q2_members))

        return bool(measure_equal and cube_equal and members_equal)


class MinfinTester(BaseTester):
    """
    Реализует логику и метрики, специфичные для минфина.
    """

    def __init__(
            self,
            percentiles=tuple([25, 50, 75, 90, 95]),
            is_need_logging=False
    ):
        super().__init__(percentiles, is_need_logging)

        # Только для не idk запросов, т.е. тех, которые возвращают что-то
        # для них порог не учитывается, т.к. не имеет смысла
        self._known = AccuracyScoreHelper()

        # Результаты, в которых не учитывается скор, что позволит
        # отложить его выбор
        self._no_score = AccuracyScoreHelper()

        self._threshold_confidences = []

        self._wrong_cubes = 0

    def _add_wrong_cube(self):
        """Добавляет результат, когда мы нашли куб вместо минфина"""
        self._wrong_cubes += 1

    def get_wrong_cubes(self):
        """Возвращает число результатов, когда мы нашли куб вместо минфина"""
        return self._wrong_cubes

    def _add_threshold_confidence(self, val: float):
        self._threshold_confidences.append(val)

    def get_threshold_confidences(self):
        """
        Гарантируются, что результирующий tuple не пуст
        """
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
        res["MTC"] = safe_mean(self.get_threshold_confidences())

        # Точность без учёта скора
        res["noscoreAcc"] = self._no_score.get_score()

        # Точность без учёта idk тестов
        res["noIdkAcc"] = self._known.get_score()

        # Какая часть неверных результатов из-за того, что ответ по кубу
        res["wrongCube"] = self.get_wrong_cubes() / self.get_wrongs()

        return res

    def process_error(self, idx, req, question_id, system_answer):
        super().process_error(idx, req, question_id, system_answer)

        if question_id:
            # не idk запрос
            self._known.add_false()

    def process_wrong(self, idx, req, question_id, system_answer):
        super().process_wrong(idx, req, question_id, system_answer)

        if question_id:
            # не idk запрос
            self._known.add_false()

        try:
            if system_answer["answer"]["type"] == "cube":
                self._add_wrong_cube()
        except KeyError:
            # результата может не быть вовсе
            pass
        except TypeError:
            pass

    def process_true(self, idx, req, question_id, system_answer):
        """
        Добавляет Absolute Confidence, т.к. скор специфичен для минфина и кубов
        Также добавляет Threshold Confidence
        """
        super().process_true(idx, req, question_id, system_answer)

        try:
            nearest_result = self._get_nearest_result(system_answer)
            absolute_confidence = system_answer['answer']['score'] - nearest_result
            self._add_absolute_confidence(absolute_confidence)

            self._add_threshold_confidence(
                system_answer['answer']['score'] - MODEL_CONFIG["relevant_minfin_main_answer_threshold"]
            )
        except:
            # Для Idk запросов это абсолютно нормально, что у них нет скора
            pass

        if question_id:
            # не idk запрос
            self._known.add_true()

    def _check_result(self, idx, req, question_id, system_answer):
        response = system_answer['answer']
        if not response and not question_id:
            # idk-запрос
            ars = 'IDK Запрос "{req}" отрабатывает корректно'.format(req=req)
            self.add_text_result(ars)
            self.process_true(idx, req, question_id, system_answer)
            return
        elif not response:
            ars = '{q_id} - Запрос "{req}" вызвал ошибку: {msg}'.format(
                q_id=question_id,
                req=req,
                msg='Не определена'
            )

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

        if not question_id:
            ars = (
                '{score} Запрос "{req}" отрабатывает некорректно, ' +
                'должны получать IDK'
            )
            ars = ars.format(score=system_answer['answer']['score'], req=req)
            self.add_text_result(ars)
            self.process_wrong(idx, req, question_id, system_answer)
            return

        if question_id == str(response):
            # получили совпадение, при этом
            # в таком случае, мы не могли получить idk,
            # значит варианты, когда должны были вернуть idk не учитываются
            self._no_score.add_true()

            if self._threshold < system_answer['answer']['score']:
                ars = '{q_id} + {score} Запрос "{req}" отрабатывает корректно'
                ars = ars.format(q_id=question_id,
                                 score=system_answer['answer']['score'],
                                 req=req)
                self.add_text_result(ars)
                self.process_true(idx, req, question_id, system_answer)
            else:
                ars = '{q_id} + {score} Запрос "{req}" не проходит по порогу'
                ars = ars.format(q_id=question_id,
                                 score=system_answer['answer']['score'],
                                 req=req)
                self.add_text_result(ars)
                self.process_wrong(idx, req, question_id, system_answer)
        else:
            self._no_score.add_false()
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
        "--turn-on-mwat",
        action='store_true',
        help='Включает тестирование с учетом неверных авто-тестов по минфину'
    )

    args = parser.parse_args()

    # Если аргументов не было, то тестируем как обычно
    if not args.cube and not args.minfin:
        args.cube = True
        args.minfin = True

    if args.turn_on_mwat:
        MODEL_CONFIG["use_local_file_processing_for_minfin"] = True
        set_default_model(MODEL_CONFIG)
    else:
        MODEL_CONFIG["use_local_file_processing_for_minfin"] = False
        set_default_model(MODEL_CONFIG)

    score, results = get_results(
        need_cube=args.cube,
        need_minfin=args.minfin,
        write_logs=not args.no_logs
    )

    restore_default_model()

    current_datetime = datetime.datetime.now().strftime(CURRENT_DATETIME_FORMAT)
    result_file_name = "results_{}.json".format(current_datetime)
    with open(path.join(TEST_PATH_RESULTS, result_file_name), 'w') as f_out:
        json.dump(results, f_out, indent=4, sort_keys=True)
    print("Results: {}".format(json.dumps(results, indent=4)))
    if not isnan(score):
        print("Score: {:.4f}".format(score))


if __name__ == "__main__":
    _main()
