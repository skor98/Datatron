#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Создание базы данных с пользователями
"""

import sys
import argparse

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
    # pylint: disable=invalid-name
    parser = argparse.ArgumentParser(
        description="Пересоздание базы с пользователями"
    )

    parser.add_argument(
        "--create",
        action='store_true',
        help='Создаёт таблицы (но не удаляет старое!)',
    )

    parser.add_argument(
        "--drop",
        action='store_true',
        help='Удаляет таблицы',
    )

    parser.add_argument(
        "--recreate",
        action='store_true',
        help='Пересоздаёт таблицы',
    )

    args = parser.parse_args()
    # pylint: enable=invalid-name
    if not args.recreate and not args.create and not args.drop:
        print("Ничего не делаю. Если вы хотите иного, вызовите {} --help".format(
            sys.argv[0]
        ))
        sys.exit(0)

    if args.recreate:
        drop_tables()
        create_tables()
    elif args.create:
        create_tables()
    elif args.drop:
        drop_tables()
    else:
        assert False
        sys.exit(1)
    print("Complete")
