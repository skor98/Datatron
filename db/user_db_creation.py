#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Создание базы данных с пользователями
"""

from config import SETTINGS
from peewee import Model, SqliteDatabase, IntegerField, CharField, ForeignKeyField

database = SqliteDatabase(SETTINGS.PATH_TO_USER_DB)  # pylint: disable=invalid-name


class BaseModel(Model):
    class Meta:
        database = SqliteDatabase(SETTINGS.PATH_TO_USER_DB)


class User(BaseModel):
    user_id = IntegerField()
    user_name = CharField(null=True)
    full_user_name = CharField()


class Feedback(BaseModel):
    user = ForeignKeyField(User)
    time = CharField()
    feedback = CharField()


def create_tables():
    """Создаёт таблицы с пользователями"""
    database.connect()
    database.create_tables([User, Feedback])


def drop_tables():
    """Удаляет таблицы с пользователями"""
    database.drop_tables([User, Feedback])

if __name__ == "__main__":
    pass
    # create_tables()
    # drop_tables()
