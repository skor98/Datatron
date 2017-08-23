#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
База данных с запросами
"""

import datetime

from peewee import SqliteDatabase, DateTimeField, CharField, Model, fn

from config import QUERY_DB_PATH
from model_manager import MODEL_CONFIG

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


_is_inited = False
