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
from kb.docs_generating import DocsGeneration
from kb.minfin_docs_generation import set_up_minfin_data
from config import SETTINGS
from manual_testing import cube_testing
import logs_helper  # pylint: disable=unused-import


def set_up_db(overwrite=True):
    """
    Создание и заполнение БД

    :param overwrite: если True, то БД будет создана полностью заново,
    если False - то будет дополнена
    :return:
    """
    # 1. Создание и заполнение БД
    kb_path = SETTINGS.PATH_TO_KNOWLEDGEBASE

    db_file = path.basename(kb_path)

    kbs = KnowledgeBaseSupport('knowledge_base.db.sql', db_file)
    kbs.set_up_db(overwrite=overwrite)


def set_up_solr_cube_data(index_way='curl'):
    """
    Создание и индексирование документов по кубам

    :param index_way: если curl, то индексирование документов в Solr Apache будет черз сURL,
    если jar_file, то средствами java скрипта от Solr
    :return:
    """
    # 2. Генерация и индексация документов
    dga = DocsGeneration()
    dga.clear_index()  # Удаление документов из ядра
    dga.generate_docs()  # Генерация документов
    if index_way == 'curl':
        dga.index_created_documents_via_curl()
    else:
        dga.index_created_documents_via_jar_file()


def set_up_all_together():
    """
    Настройка БД, документов по кубам и минфину одним методом.
    Если какой-то функционал не нужен, то он комметируется перед выполнением
    """
    set_up_db()
    set_up_solr_cube_data('jar')
    # pylint: disable=no-member
    set_up_minfin_data('jar')


if __name__ == '__main__':
    # set_up_all_together()
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
        "--solr",
        action='store_true',
        help='Создание и индексирование документов по кубам',
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
        "--minfin",
        action='store_true',
        help='Создание и индексирование документов по минфину',
    )

    parser.add_argument(
        "--disable-testing",
        action='store_true',
        help='Отключает тестирование после инициализации кубов',
    )

    args = parser.parse_args()
    # pylint: enable=invalid-name

    if not args.db and not args.solr and not args.minfin:
        print("Ничего не делаю. Если вы хотите иного, вызовите {} --help".format(
            sys.argv[0]
        ))
        sys.exit(0)

    if args.db:
        set_up_db()
    if args.solr:
        set_up_solr_cube_data(args.solr_index)
        if not args.disable_testing:
            cube_testing(test_sphere='cube')
    if args.minfin:
        set_up_minfin_data(args.solr_index)
        if not args.disable_testing:
            cube_testing(test_sphere='minfin')

    logging.info("Setting system up complete")


# Команда переключение в нужну дерикторию и запуска Solr для Димы
# cd C:\Users\User\Desktop\solr\solr-6.3.0\solr-6.3.0\bin
# solr.cmd start -f
