from config import SETTINGS
from peewee import *

database = SqliteDatabase(SETTINGS.PATH_TO_KNOWLEDGEBASE)


class BaseModel(Model):
    class Meta:
        database = SqliteDatabase(SETTINGS.PATH_TO_KNOWLEDGEBASE)


class Value(BaseModel):
    full_value = CharField()
    synonyms = CharField(null=True)
    lem_index_value = CharField()
    lem_synonyms = CharField(null=True)
    cube_value = CharField()
    hierarchy_level = CharField(null=True)
    connected_value = CharField(ForeignKeyField(Value, null=True))


class Measure(BaseModel):
    full_value = CharField()
    lem_index_value = CharField()
    cube_value = CharField()
    format = CharField()


class Dimension(BaseModel):
    label = CharField()
    default_value = ForeignKeyField(Value, null=True)


class Dimension_Value(BaseModel):
    value = ForeignKeyField(Value)
    dimension = ForeignKeyField(Dimension)

    class Meta:
        primary_key = CompositeKey('value', 'dimension')


class Cube(BaseModel):
    name = CharField()
    auto_lem_description = CharField()
    manual_description = CharField(null=True)
    manual_lem_description = CharField(null=True)
    default_measure = ForeignKeyField(Measure)


class Cube_Dimension(BaseModel):
    dimension = ForeignKeyField(Dimension)
    cube = ForeignKeyField(Cube)

    class Meta:
        primary_key = CompositeKey('dimension', 'cube')


class Cube_Measure(BaseModel):
    measure = ForeignKeyField(Measure)
    cube = ForeignKeyField(Cube)

    class Meta:
        primary_key = CompositeKey('measure', 'cube')


def create_tables():
    database.connect()
    database.create_tables(
        [Dimension, Cube, Measure, Cube_Measure, Cube_Dimension, Dimension_Value, Value])


def drop_tables():
    database.drop_tables(
        [Dimension, Cube, Measure, Cube_Measure, Cube_Dimension, Dimension_Value, Value])
