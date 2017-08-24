#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Инициализация системы
"""

import argparse
import datetime
import json
import logging
from math import isnan
from os import path
import sys

from config import SETTINGS, TEST_PATH_RESULTS, DATETIME_FORMAT
from core.cube_classifier import train_and_save_cube_clf, select_best_cube_clf
from core.cube_or_minfin_classifier import select_best_cube_or_minfin_clf, train_and_save_cube_or_minfin_clf
from kb.db_filling import KnowledgeBaseSupport
from kb.docs_generation_for_cubes import CubeDocsGeneration
from kb.docs_generation_for_minfin import set_up_minfin_data
import logs_helper
from manual_testing import get_results


CURRENT_DATETIME_FORMAT = DATETIME_FORMAT.replace(' ', '_').replace(':', '-').replace('.', '-')

@logs_helper.time_with_message("set_up_db", "info")
def set_up_db():
    """Создание и заполнение БД"""

    # 1. Создание и заполнение БД
    kb_path = SETTINGS.PATH_TO_KNOWLEDGEBASE  # pylint: disable=no-member

    db_file = path.basename(kb_path)

    kbs = KnowledgeBaseSupport('knowledge_base.db.sql', db_file)
    kbs.set_up_db()


@logs_helper.time_with_message("set_up_cube_data", "info")
def set_up_cube_data(index_way='curl'):
    """
    Создание и индексирование документов по кубам. Если
    index_way=curl, то индексирование документов
    в Solr Apache будет осуществляться через сURL,
    иначе средствами java скрипта от Solr
    """

    # 2. Генерация и индексация документов
    dga = CubeDocsGeneration()
    dga.clear_index()  # Удаление документов из ядра
    dga.generate_docs()  # Генерация документов
    if index_way == 'curl':
        dga.index_created_documents_via_curl()
    else:
        dga.index_created_documents_via_jar_file()


if __name__ == '__main__':
    # pylint: disable=invalid-name
    parser = argparse.ArgumentParser(
        description="Иниициализация системы"
    )

    parser.add_argument(
        "--db",
        action='store_true',
        help='Создание и заполнение БД',
    )

    parser.add_argument(
        "--clf-select",
        action='store_true',
        help='Выбор лучшей модели для классификатора по кубам. Может быть долгим!',
    )

    parser.add_argument(
        "--clf",
        action='store_true',
        help='Тренировка классификатора по кубам и его сохранение',
    )

    parser.add_argument(
        "--cube",
        action='store_true',
        help='Создание и индексирование документов по кубам',
    )

    parser.add_argument(
        "--minfin",
        action='store_true',
        help='Создание и индексирование документов по минфину',
    )

    parser.add_argument(
        "--solr-index", nargs='?', choices=['curl', 'jar'],
        help=(
            'если curl, то индексирование документов в Solr Apache ' +
            'будет черз сURL, если jar, ' +
            'то средствами java скрипта от Solr'
        ), default='curl', const='curl'
    )

    parser.add_argument(
        "--disable-testing",
        action='store_true',
        help='Отключает тестирование после инициализации кубов',
    )

    args = parser.parse_args()
    # pylint: enable=invalid-name

    if args.clf_select:
        # Если потратили столько времени на выбор модели, то можно её и обучить
        select_best_cube_clf()
        select_best_cube_or_minfin_clf()
        args.clf = True

    if not args.clf and not args.db and not args.cube and not args.minfin:
        print("Ничего не делаю. Если вы хотите иного, вызовите {} --help".format(
            sys.argv[0]
        ))
        sys.exit(0)

    if args.clf:
        train_and_save_cube_clf()
        train_and_save_cube_or_minfin_clf()
    if args.db:
        set_up_db()
    if args.cube:
        set_up_cube_data(args.solr_index)
    if args.minfin:
        set_up_minfin_data(args.solr_index)
    if not args.disable_testing and args.cube and args.minfin:
        score, results = get_results(write_logs=True)

        current_datetime = datetime.datetime.now().strftime(CURRENT_DATETIME_FORMAT)
        result_file_name = "results_{}.json".format(current_datetime)
        with open(path.join(TEST_PATH_RESULTS, result_file_name), 'w') as f_out:
            json.dump(results, f_out, indent=4)

        print("Results: {}".format(json.dumps(results, indent=4)))

        if not isnan(score):
            print("Score: {:.4f}".format(score))

    logging.info("Setting system up complete")
