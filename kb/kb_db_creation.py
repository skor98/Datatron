#!/usr/bin/python3
# -*- coding: utf-8 -*-

from peewee import Model, SqliteDatabase, CharField, ForeignKeyField, CompositeKey

from config import SETTINGS


_database = SqliteDatabase(SETTINGS.PATH_TO_KNOWLEDGEBASE)


class BaseModel(Model):
    class Meta:
        _database = SqliteDatabase(SETTINGS.PATH_TO_KNOWLEDGEBASE)


class Value(BaseModel):
    full_value = CharField()
    lem_index_value = CharField()
    lem_synonyms = CharField(null=True)
    cube_value = CharField()
    hierarchy_level = CharField(null=True)
    connected_value = CharField(null=True)


class Measure(BaseModel):
    full_value = CharField()
    lem_index_value = CharField()
    cube_value = CharField()
    format = CharField()


class Dimension(BaseModel):
    label = CharField()
    full_value = CharField()
    default_value = ForeignKeyField(Value, null=True)


class DimensionValue(BaseModel):
    value = ForeignKeyField(Value)
    dimension = ForeignKeyField(Dimension)

    class Meta:
        primary_key = CompositeKey('value', 'dimension')


class Cube(BaseModel):
    name = CharField()
    description = CharField()
    auto_lem_description = CharField()
    manual_description = CharField(null=True)
    manual_lem_description = CharField(null=True)
    default_measure = ForeignKeyField(Measure)


class CubeDimension(BaseModel):
    dimension = ForeignKeyField(Dimension)
    cube = ForeignKeyField(Cube)

    class Meta:
        primary_key = CompositeKey('dimension', 'cube')


class CubeMeasure(BaseModel):
    measure = ForeignKeyField(Measure)
    cube = ForeignKeyField(Cube)

    class Meta:
        primary_key = CompositeKey('measure', 'cube')


def create_tables():
    """Создаёт таблицы с базой знаний"""
    _database.connect()
    _database.create_tables([
        Dimension,
        Cube,
        Measure,
        CubeMeasure,
        CubeDimension,
        DimensionValue,
        Value
    ])


def drop_tables():
    """Удаляет таблицы с базой знаний"""
    _database.drop_tables([
        Dimension,
        Cube,
        Measure,
        CubeMeasure,
        CubeDimension,
        DimensionValue,
        Value
    ])

if __name__ == "__main__":
    pass
