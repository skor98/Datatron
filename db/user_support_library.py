from config import SETTINGS
from peewee import *

database = SqliteDatabase(SETTINGS.PATH_TO_USER_DB)


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
    database.connect()
    database.create_tables(
        [User, Feedback])


def drop_tables():
    database.drop_tables(
        [User, Feedback])

# create_tables()
# drop_tables()
