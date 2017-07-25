#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Инициализация системы
"""

import logging
import sys
import argparse

from os import path

from kb.db_filling import KnowledgeBaseSupport
from kb.docs_generation_for_cubes import CubeDocsGeneration
from kb.docs_generation_for_minfin import set_up_minfin_data
from config import SETTINGS
from manual_testing import testing
# не убирайте эту строчку, иначе логгирование не будет работать
import logs_helper  # pylint: disable=unused-import


def set_up_db():
    """Создание и заполнение БД"""

    # 1. Создание и заполнение БД
    kb_path = SETTINGS.PATH_TO_KNOWLEDGEBASE  # pylint: disable=no-member

    db_file = path.basename(kb_path)

    kbs = KnowledgeBaseSupport('knowledge_base.db.sql', db_file)
    kbs.set_up_db()


def set_up_solr_cube_data(index_way='curl'):
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

    if not args.db and not args.cube and not args.minfin:
        print("Ничего не делаю. Если вы хотите иного, вызовите {} --help".format(
            sys.argv[0]
        ))
        sys.exit(0)

    if args.db:
        set_up_db()
    if args.cube:
        set_up_solr_cube_data(args.solr_index)
    if args.minfin:
        set_up_minfin_data(args.solr_index)
    if not args.disable_testing:
        testing(test_sphere='cube')
        testing(test_sphere='minfin')

    logging.info("Setting system up complete")
