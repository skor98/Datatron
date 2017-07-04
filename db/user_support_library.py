#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Базовые функции для работы с базой пользователей и их фидбеками
"""

from db.user_db_creation import User, Feedback


def check_user_existence(user_id):
    """
    Проверяет, пользователь с таким user_id существует
    """
    return bool(User.select().where(User.user_id == user_id).count())


def create_user(user_id, user_name, full_user_name):
    """
    Создаёт нового пользователя с указанными данными
    """
    User.create(
        user_id=user_id,
        user_name=user_name,
        full_user_name=full_user_name,
        expert_mode=0,
        question_mode=0
    )


def create_feedback(user_id, time, feedback):
    """
    Записывает фидбек от указанного пользователя в базу
    """
    if not check_user_existence(user_id):
        # ToDo: может ли так быть?
        return
    user_in_db = User.select().where(User.user_id == user_id)
    Feedback.create(user=user_in_db, time=str(time), feedback=feedback)


def get_feedbacks():
    """
    Получаем все фидбеки от пользователей
    """
    # ToDo: если пользователей много, то мы помрём от памяти, возможно и от диска
    feedbacks = []
    for feedback in Feedback.select():
        for user in User.select().where(User.id == feedback.user_id):
            fb_string = '{} {} {}'.format(feedback.time, user.full_user_name, feedback.feedback)
            feedbacks.append(fb_string)
    return '\n'.join(feedbacks)
