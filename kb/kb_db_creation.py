#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Определение структуры базы знаний по OLAP-кубам
"""

from peewee import Model, SqliteDatabase, CharField, ForeignKeyField, CompositeKey

from config import SETTINGS


database = SqliteDatabase(SETTINGS.PATH_TO_KNOWLEDGEBASE)


class BaseModel(Model):
    class Meta:
        database = SqliteDatabase(SETTINGS.PATH_TO_KNOWLEDGEBASE)


class Member(BaseModel):
    """Значение измерения куба"""

    # Полное вербальное значение
    caption = CharField()

    # Нормализованное вербальное значение
    lem_caption = CharField()

    # Нормализованные синонимы
    lem_synonyms = CharField(null=True)

    # Формальное значение для куба
    cube_value = CharField()

    # Уровень значения измерения в иерархии измерения
    hierarchy_level = CharField(null=True)

    # Значение измерения, которое также должно быть
    # в запросе, если указано данное
    with_member = CharField(null=True)


class Measure(BaseModel):
    """Мера куба"""

    # Полное вербальное значение
    caption = CharField()

    # Нормализованное вербальное значение
    lem_caption = CharField()

    # Ключевые слова для меры от методологов
    key_words = CharField(null=True)

    # Ключевые слова для меры от методологов
    lem_key_words = CharField(null=True)

    # Формальное значение для куба
    cube_value = CharField()

    # Формат, в котором предоставляются данные из этой меры
    # Если 0 - то данные в рублях
    # Если 1 - то данные в процентах
    # Если 2 – то данные в штуках (сейчас кубов с такими мерами в БД нет)
    format = CharField()


class Dimension(BaseModel):
    """Измерение куба"""

    # Название измерения
    cube_value = CharField()

    # Полное вербальное значение
    caption = CharField()

    # Ключевые слова для измерения от методологов
    key_words = CharField(null=True)

    # Нормализованные ключевые слова для измерения от методологов
    lem_key_words = CharField(null=True)

    # Значение измерения по умолчанию
    default_value = ForeignKeyField(Member, null=True)


class DimensionMember(BaseModel):
    """
    Перекрестная сущность между измерением и значением для
    реализации соотношения many-to-many. Зачем нужно M:M?
    Для упрощения жизни. Например, многие кубы имеют
    измерение территория, но иногда куб поддерживает не
    все значения измерения. Именно поэтому в БД в таблице Value
    много одинаковых строк. Это также сделано, возможно,
    ради упрощения дальнейшего обновления данных в базе знаний
    по API Кристы.
    """

    member = ForeignKeyField(Member)
    dimension = ForeignKeyField(Dimension)

    class Meta:
        primary_key = CompositeKey('member', 'dimension')


class Cube(BaseModel):
    """Данные по кубу"""

    # Формальное название куба, например, "CLMR02"
    name = CharField()

    # Тема куба, например, "Госдолг РФ"
    caption = CharField()

    # Наиболее часто встречающиеся слова в значениях
    # измерения куба в нормализованном виде с повторениями
    auto_lem_key_words = CharField()

    # Ключевые слова, составленные методологом
    key_words = CharField(null=True)

    # Нормализованые ключевые слова от методолога
    lem_key_words = CharField(null=True)

    # Мера для куба по умолчанию
    default_measure = ForeignKeyField(Measure)


class CubeDimension(BaseModel):
    """
    Перекрестная сущность между кубом и измерением.
    Уместно все, что сказано выше для перекрестной таблицы.
    """

    dimension = ForeignKeyField(Dimension)
    cube = ForeignKeyField(Cube)

    class Meta:
        primary_key = CompositeKey('dimension', 'cube')


class CubeMeasure(BaseModel):
    """
    Перекрестная сущность между кубом и мерой.
    Уместно все, что сказано выше для перекрестной таблицы.
    """

    measure = ForeignKeyField(Measure)
    cube = ForeignKeyField(Cube)

    class Meta:
        primary_key = CompositeKey('measure', 'cube')


def create_tables():
    """Создание таблиц базы знаний по кубам"""

    database.connect()
    database.create_tables([
        Dimension,
        Cube,
        Measure,
        CubeMeasure,
        CubeDimension,
        DimensionMember,
        Member
    ])


def drop_tables():
    """Удаление таблиц базы знаний"""

    database.drop_tables([
        Dimension,
        Cube,
        Measure,
        CubeMeasure,
        CubeDimension,
        DimensionMember,
        Member
    ])

if __name__ == "__main__":
    pass
