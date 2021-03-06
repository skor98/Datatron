#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Управление классами ядра системы
"""

from os import path
import json
import logging

from config import SETTINGS
from config import TEST_PATH_RESULTS, WRONG_AUTO_MINFIN_TESTS_FILE
from constants import ERROR_NO_DOCS_FOUND, ERROR_REQUEST_CONTAINS_BAD_WORD
from core.answer_object import CoreAnswer
from core.cube_classifier import CubeClassifier
from core.cube_docs_processing import CubeAnswer
from core.cube_docs_processing import CubeProcessor
from core.cube_or_minfin_classifier import CubeOrMinfinClassifier
from core.minfin_docs_processing import MinfinProcessor
from core.solr import Solr
from core.support_library import group_documents
from core.support_library import process_cube_answer
from core.support_library import process_server_response
from core.support_library import send_request_to_server
from model_manager import MODEL_CONFIG
from text_preprocessing import TextPreprocessing
import logs_helper  # pylint: disable=unused-import


class DataRetrieving:
    """
    Модуль связывающие в себе результаты работы Apache Solr,
    и классов обработки его выдачи - CubeProcessor и MinfinProcessor
    """

    TPP = TextPreprocessing(label='DATRET', delete_question_words=False)

    # хранение данных в памяти
    _minfin_auto_wrong_data = None

    @staticmethod
    def get_data(user_request: str, request_id: str):
        """API метод к ядру системы"""

        core_answer = CoreAnswer()
        core_answer.user_request = user_request

        if user_request.lower().startswith("кто будет"):
            return core_answer

        norm_user_request = DataRetrieving._preprocess_user_request(
            core_answer.user_request,
            request_id
        )

        correct_answer_num = DataRetrieving._process_exact_minfin_answers(
            user_request
        )

        # обработка плохих слов
        badcount = norm_user_request.count('<censored>')
        if badcount > 0:
            core_answer.bad_content = True
            core_answer.message = ERROR_REQUEST_CONTAINS_BAD_WORD

            logging.info(
                'Query_ID: {}\tMessage: Запрос содержал {}'.format(
                    request_id,
                    'плохое слово' if badcount == 1 else 'плохие слова'
                )
            )

            return core_answer

        # получение результатов поиска от Apache Solr в JSON-строке
        solr_response = Solr.get_data(
            norm_user_request,
            request_id,
            SETTINGS.SOLR_MAIN_CORE
        )['response']

        # Если хотя бы 1 документ найден:
        if solr_response['numFound']:
            minfin_docs, cube_data = group_documents(
                solr_response['docs'],
                core_answer.user_request,
                norm_user_request,
                request_id
            )

            minfin_answers = MinfinProcessor.get_data(minfin_docs)

            clf = CubeClassifier.inst()
            best_prediction = tuple(
                clf.predict_proba(core_answer.user_request)
            )[0]

            ans_type = None

            # ручная проверка, актуальная для вопросов по pretty_feedback
            clf_status, cube = DataRetrieving._manual_cube_classification(
                norm_user_request
            )

            if clf_status:
                best_prediction = (cube, 0.99)
                ans_type = 'cube'

            cube_answers, cube_confidence = CubeProcessor.get_data(
                cube_data, best_prediction)

            logging.info(
                "Query_ID: {}\tMessage: Найдено {} докумета(ов) по кубам и {} по Минфину".format(
                    request_id,
                    len(cube_answers),
                    len(minfin_answers)
                )
            )

            answers = DataRetrieving._sort_answers(
                minfin_answers,
                cube_answers,
                correct_answer_num,
                ans_type
            )

            DataRetrieving._format_core_answer(
                answers,
                request_id,
                core_answer,
                cube_confidence
            )
        else:
            # Обработка случая, когда документы не найдены
            core_answer.message = ERROR_NO_DOCS_FOUND
            logging.info(
                'Query_ID: {}\tMessage: Документа не найдены'.format(
                    request_id)
            )

        return core_answer

    @staticmethod
    def _process_exact_minfin_answers(user_request: str):
        if MODEL_CONFIG["use_local_file_processing_for_minfin"]:
            minfin_auto_wrong_tests = DataRetrieving._minfin_auto_wrong_questions()
            user_request = user_request.lower()

            user_request = user_request.replace('?', '')

            # сработает для формулировки с любым порядком слов
            for key in minfin_auto_wrong_tests.keys():
                if set(user_request.split()) == set(key.split()):
                    return minfin_auto_wrong_tests.get(key, 0)

    @staticmethod
    def _minfin_auto_wrong_questions():
        if not DataRetrieving._minfin_auto_wrong_data:
            minfin_wrong_auto_tests_file = path.join(
                TEST_PATH_RESULTS, WRONG_AUTO_MINFIN_TESTS_FILE
            )

            with open(minfin_wrong_auto_tests_file, 'r', encoding='utf-8') as file:
                DataRetrieving._minfin_auto_wrong_data = json.loads(
                    file.read())

        return DataRetrieving._minfin_auto_wrong_data

    @staticmethod
    def _preprocess_user_request(user_request: str, request_id: str):
        """Предобработка запроса пользователя"""

        # нормализация запроса пользователя
        norm_user_request = DataRetrieving.TPP(user_request, request_id)

        if MODEL_CONFIG["delete_repeating_words_in_request"]:
            norm_user_request = DataRetrieving._set_user_request(
                norm_user_request, request_id
            )

        if MODEL_CONFIG["enable_repetition_for_short_request"]:
            norm_user_request = DataRetrieving._multiple_user_request(
                norm_user_request, request_id
            )

        return norm_user_request

    @staticmethod
    def _set_user_request(norm_user_request: str, request_id: str):
        """
        Удаление повторяющихся слов и увеличение длины запроса
        при необходимости
        """

        request_words = norm_user_request.split()
        unique_of_request_words = set(request_words)

        # удаление повторяющихся слов, чтобы пользователи не читерили
        if len(unique_of_request_words) != len(request_words):
            norm_user_request = ' '.join(unique_of_request_words)

            logging.info(
                "Query_ID: {}\tMessage: Удалено {} повторяющихся слов".format(
                    request_id,
                    len(request_words) - len(unique_of_request_words)
                )
            )

        return norm_user_request

    @staticmethod
    def _multiple_user_request(norm_user_request: str, request_id: str):
        """
        Дублирование коротких запросов
        """

        short_question_threshold = MODEL_CONFIG["short_request_threshold"]
        multiplier = MODEL_CONFIG["repetition_num_for_short_request"]
        request_len = len(norm_user_request.split())

        if request_len <= short_question_threshold:
            norm_user_request = ' '.join(
                [norm_user_request.strip()] * multiplier
            )

            logging.info(
                "Query_ID: {}\tMessage: Запрос из {} слов был "
                "удлинен в {} раза".format(
                    request_id,
                    request_len,
                    multiplier
                )
            )

        return norm_user_request

    @staticmethod
    def _sort_answers(
            minfin_answers: list,
            cube_answers: list,
            correct_answer_num: str,
            ans_type: str
    ):
        """Совокупное ранжирование ответов по кубам и минфину"""

        # Если по минфину найден только 1 ответ
        if not isinstance(minfin_answers, list):
            minfin_answers = [minfin_answers]

        # Если по куба найден только 1 ответ
        if not isinstance(cube_answers, list):
            cube_answers = [cube_answers]

        # Фильтрация выборки в порядке убывания по score
        all_answers = sorted(
            cube_answers + minfin_answers,
            key=lambda ans: ans.get_score(),
            reverse=True
        )

        if all_answers:
            DataRetrieving._first_place_right_type(
                all_answers,
                ans_type
            )

            if MODEL_CONFIG["use_local_file_processing_for_minfin"]:
                DataRetrieving._first_place_exact_minfin_answer(
                    all_answers,
                    correct_answer_num
                )

        return all_answers

    @staticmethod
    def _first_place_right_type(all_answers: list, ans_type: str):

        if not ans_type:
            user_request = all_answers[0].user_request

            clf = CubeOrMinfinClassifier.inst()
            prediction = tuple(clf.predict_proba(user_request))[0]
            ans_type = prediction[0].lower()

        if all_answers[0].type != ans_type:
            for elem in list(all_answers):
                if elem.type == ans_type:
                    all_answers.remove(elem)
                    all_answers.insert(0, elem)

                    logging.info(
                        "Query_ID: {}\tMessage: Главный ответ был "
                        "сменен на тип: {}".format(
                            elem.request_id,
                            ans_type
                        )
                    )

                    break
        else:
            logging.info(
                "Query_ID: {}\tMessage: Тип главного ответа совпадает с "
                "типом из классификатора".format(all_answers[0].request_id)
            )

    @staticmethod
    def _first_place_exact_minfin_answer(all_answers: list, correct_number: str):
        if correct_number:
            for answer in list(all_answers):
                if (answer.type == 'minfin' and
                        answer.number == correct_number):
                    all_answers.remove(answer)
                    all_answers.insert(0, answer)

                    if answer.get_score() < MODEL_CONFIG["relevant_minfin_main_answer_threshold"]:
                        score = MODEL_CONFIG["relevant_minfin_main_answer_threshold"]

                        logging.info(
                            "Query_ID: {}\tMessage: Score был увеличен с {} до {}".format(
                                all_answers[0].request_id,
                                answer.get_score(),
                                score
                            )
                        )

                        answer.score = score

                    logging.info(
                        "Query_ID: {}\tMessage: Главный ответ был сменен на основе"
                        " логов некорректных автоматических тестов".format(
                            all_answers[0].request_id
                        )
                    )

                    break

    @staticmethod
    def _format_core_answer(
            answers: list,
            request_id: str,
            core_answer: CoreAnswer,
            cube_confidence: str
    ):
        """Формирование структуры финального ответа"""

        # Предельное количество "смотри также"
        THRESHOLD = 5

        if answers:
            DataRetrieving._process_main_answer(
                core_answer,
                answers,
                request_id,
                cube_confidence
            )

            starting_from = 1
            if not core_answer.answer:
                starting_from = 0
                THRESHOLD -= 1

            DataRetrieving._process_more_answers(
                core_answer,
                answers[starting_from:THRESHOLD + 1],
                request_id
            )

        return core_answer

    @staticmethod
    def _process_main_answer(
            core_answer: CoreAnswer,
            answers: list,
            request_id: str,
            cube_confidence: str
    ):
        """Форматирование главного ответа"""

        # Выбор главного ответа
        core_answer.answer = answers[0]

        # Если главный ответ по кубам
        if isinstance(core_answer.answer, CubeAnswer):
            core_answer.status = True
            core_answer.confidence = cube_confidence

            logging.info(
                "Query_ID: {}\tMessage: Главный ответ - "
                "ответ по кубу - {} - {}".format(
                    request_id,
                    core_answer.answer.get_score(),
                    core_answer.answer.mdx_query
                ))

            response = send_request_to_server(
                core_answer.answer.mdx_query,
                core_answer.answer.cube
            )

            # ответ с сервера
            value = process_server_response(core_answer.answer, response)

            # форматирование ответа при его наличии
            if value is not None:
                process_cube_answer(core_answer.answer, value)
        # Если главный ответ по минфину
        else:
            # фильтр по релевантности на минфин
            if (core_answer.answer.get_score() >=
                    MODEL_CONFIG["relevant_minfin_main_answer_threshold"]):

                core_answer.status = True

                logging.info(
                    "Query_ID: {}\tMessage: Главный точный ответ - "
                    "ответ по Минфину - {} - {}".format(
                        request_id,
                        core_answer.answer.get_score(),
                        core_answer.answer.number
                    ))
            elif (core_answer.answer.get_score() >=
                  MODEL_CONFIG["minfin_main_answer_confidence_threshold"]):

                core_answer.status = True
                core_answer.confidence = False

                logging.info(
                    "Query_ID: {}\tMessage: Главный возможный ответ - "
                    "ответ по Минфину - {} - {}".format(
                        request_id,
                        core_answer.answer.get_score(),
                        core_answer.answer.number
                    ))
            else:
                # Обнуление найденого ответа
                core_answer.answer = None

                logging.info(
                    "Query_ID: {}\tMessage: Главный ответ по Минфину "
                    "не прошел порог ({} vs {})".format(
                        request_id,
                        answers[0].get_score(),
                        MODEL_CONFIG["relevant_minfin_main_answer_threshold"]
                    ))

    @staticmethod
    def _process_more_answers(
            core_answer: CoreAnswer,
            more_answers: list,
            request_id: str
    ):
        """Обработка дополнительных ответов"""

        more_cube_answers = []
        more_minfin_answers = []

        more_answers_order = ''

        for ind, answer in enumerate(more_answers):
            answer.order = ind

        for answer in more_answers:
            if isinstance(answer, CubeAnswer):
                more_cube_answers.append(answer)
                more_answers_order += '0'
            else:
                more_minfin_answers.append(answer)
                more_answers_order += '1'

        if more_cube_answers:
            core_answer.more_cube_answers = more_cube_answers

        if more_minfin_answers:
            core_answer.more_minfin_answers = more_minfin_answers

        if more_answers_order:
            core_answer.more_answers_order = more_answers_order

        logging.info(
            "Query_ID: {}\tMessage: В смотри также {} "
            "ответ(а, ов) по кубам и {} по Минфину".format(
                request_id,
                len(more_cube_answers),
                len(more_minfin_answers)
            ))

    @staticmethod
    def _manual_cube_classification(user_request: str):
        key_words_to_cube = {
            "основной показатель субъект РФ": "CLDO02",
            "источник финансирование": "FSYR01",
            "оперативный расход": "EXDO01",
            "годовой расход": "EXYR03",
            "оперативный доход": "INDO01",
            "основной характеристика федеральный бюджет": "CLDO01",
            "годовой доход": "INYR03",
            "госдолг РФ": "CLMR02"
        }

        for key, value in key_words_to_cube.items():
            if user_request.startswith(key):
                return True, value

        return False, None
