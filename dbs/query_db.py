#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
База данных с запросами
"""

import datetime
import pandas as pd
import os

from peewee import SqliteDatabase, DateTimeField, CharField, Model, fn

from config import QUERY_DB_PATH, TEST_PATH_RESULTS
from model_manager import MODEL_CONFIG
from kb.kb_support_library import read_minfin_data

_database = SqliteDatabase(QUERY_DB_PATH)


class UserQuery(Model):
    """
    Модель для сохранения пользовательских запросов
    """
    date = DateTimeField()
    request_id = CharField()
    user_id = CharField()
    user_name = CharField()
    platform = CharField()
    query = CharField()
    query_type = CharField()

    class Meta:
        database = _database


def _init_db():
    """
    Создаёт таблицы, если ещё не были созданы
    """
    global _is_inited
    _database.connect()
    _database.create_table(UserQuery, safe=True)
    _is_inited = True


def log_query_to_db(request_id, user_id, user_name, platform, query, query_type):
    """
    Выполняет сохранение запроса в БД.
    Предполгается, что они приосходят не слишком часто.
    """
    if not _is_inited:
        _init_db()
    query_to_save = UserQuery(
        date=datetime.datetime.now(),
        request_id=request_id,
        user_id=user_id,
        user_name=user_name,
        platform=platform,
        query=query,
        query_type=query_type
    )
    query_to_save.save()


def get_queries(user_id, time_delta):
    """
    Возвращает последние запросы
    Если user_id пустой, то возвращает по всем
    """
    if not _is_inited:
        _init_db()
    select = UserQuery.select(
        UserQuery.date,
        UserQuery.user_id,
        UserQuery.query
    )
    if user_id:
        db_res = select.where(
            (UserQuery.user_id == str(user_id)) &
            (UserQuery.date >= datetime.datetime.now() - time_delta)
        )
    else:
        db_res = select.where((UserQuery.date >= datetime.datetime.now() - time_delta))

    if user_id:
        return tuple(["{} {}".format(row.date, row.query) for row in db_res])

    return tuple(["{} {}: {}".format(row.date, row.user_id, row.query) for row in db_res])


def get_random_requests(num=5):
    """N рандомных запросов по кубам и Минфину"""

    def get_queries_from_db():
        """Чтение 5 рандобных запросов из БД"""

        user_requests = []
        query = (UserQuery
                 .select(UserQuery.query)
                 .order_by(fn.Random())
                 .distinct()
                 .limit(num))

        for elem in query:
            user_requests.append(elem.query)
        return user_requests

    def get_queries_from_files():
        """Чтение всех вопросов по Минфину"""

        # чтение данных по минфину
        _, dfs = read_minfin_data()
        minfin_data = pd.concat(dfs)
        data = minfin_data['question'].tolist()

        # чтение данных по минфину
        files = [elem for elem in os.listdir(TEST_PATH_RESULTS) if
            (
                elem.endswith('.txt') and elem.startswith('cube')
            )]

        with open(os.path.join(TEST_PATH_RESULTS, max(files)), 'r', encoding='utf-8') as file:
            for line in file:
                line = line.split('\t')
                if len(line) > 1:
                    if line[1] == '+':
                        data.append(line[2].strip()+'?')

        return pd.DataFrame(data)

    if get_random_requests.data is None:
        if MODEL_CONFIG["enable_idea_command_from_db"]:
            return get_queries_from_db()
        else:
            get_random_requests.data = get_queries_from_files()
            return get_random_requests.data[0].sample(num).tolist()

    return get_random_requests.data[0].sample(num).tolist()


get_random_requests.data = None
_is_inited = False
