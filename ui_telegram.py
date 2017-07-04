#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Бот телеграма для Datatron
"""

import uuid
import datetime
import random
import string
import os

import telebot
from telebot import types
from logs_retriever import LogsRetriever
from db.user_support_library import check_user_existence
from db.user_support_library import create_user
from db.user_support_library import create_feedback
from db.user_support_library import get_feedbacks
from kb.kb_support_library import get_classification_for_dimension
from speechkit import text_to_speech
from messenger_manager import MessengerManager

from config import SETTINGS

import requests
import constants

API_TOKEN = SETTINGS.TELEGRAM_API_TOKEN
bot = telebot.TeleBot(API_TOKEN)

logsRetriever = LogsRetriever('logs.log')

user_name_str = '{} {}'


def get_random_id(id_len=4):
    """
    Генерируем случайную буквенно-цифровую последовательность из id_len символов
    """
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(random.choice(alphabet) for ind in range(id_len))


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработки команды /start"""

    bot.send_message(message.chat.id, constants.TELEGRAM_START_MSG, parse_mode='HTML')
    if not check_user_existence(message.chat.id):
        try:
            full_name = ' '.join([message.chat.first_name, message.chat.last_name])
        except TypeError:
            full_name = None

        create_user(
            message.chat.id,
            message.chat.username,
            full_name
        )


# /help command handler; send hello-message to the user
@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(
        message.chat.id,
        constants.HELP_MSG,
        parse_mode='HTML',
        reply_markup=constants.HELP_KEYBOARD,
        disable_web_page_preview=True
    )


@bot.message_handler(commands=['getlog'])
def get_all_logs(message):
    with open('logs.log', 'rb') as log_file:
        bot.send_document(message.chat.id, data=log_file)


@bot.message_handler(commands=['getsessionlog'])
def get_session_logs(message):
    try:
        time_span = None
        try:
            time_span = int(message.text.split()[1])
        except IndexError:
            pass
        except ValueError:
            # Элемент 1 существует, но не число
            error_message_pattern = (
                'Не могу перевести {} в число. ' +
                'Буду использовать значение по умолчанию'
            )
            bot.send_message(
                message.chat.id,
                error_message_pattern.format(message.text.split()[1])
            )
        if time_span:
            logs = logsRetriever.get_log(
                kind='session',
                user_id=message.chat.id,
                time_delta=time_span
            )
        else:
            logs = logsRetriever.get_log(kind='session', user_id=message.chat.id)

        if logs:
            bot.send_message(message.chat.id, logs)
        else:
            bot.send_message(message.chat.id, constants.MSG_LOG_HISTORY_IS_EMPTY)
    except:
        bot.send_message(message.chat.id, 'Данная функция временно не работает')
        MessengerManager.log_data('Команда /getsessionlog не сработала', level='warning')


@bot.message_handler(commands=['getrequestlog'])
def get_request_logs(message):
    try:
        logs = logsRetriever.get_log(kind='request', user_id=message.chat.id)
        if logs:
            bot.send_message(message.chat.id, logs)
        else:
            bot.send_message(message.chat.id, constants.MSG_LOG_HISTORY_IS_EMPTY)
    except:
        bot.send_message(message.chat.id, 'Данная функция временно не работает')
        MessengerManager.log_data('Команда /getrequestlog не сработала', level='warning')


@bot.message_handler(commands=['getinfolog'])
def get_all_info_logs(message):
    try:
        logs = logsRetriever.get_log(kind='info')
        path_to_log_file = r'tmp\{}'
        if logs:
            rnd_str = get_random_id(4)
            file_name = '{}_{}_{}_{}.log'.format(
                'info',
                rnd_str,
                message.chat.username,
                datetime.datetime.now().strftime("%d-%m-%Y")
            )

            path_to_log_file = path_to_log_file.format(file_name)
            with open(path_to_log_file, 'w', encoding='utf-8') as file:
                file.write(logs)
            try:
                with open(path_to_log_file, 'rb') as log_file:
                    bot.send_document(message.chat.id, data=log_file)
            finally:
                os.remove(path_to_log_file)
        else:
            bot.send_message(message.chat.id, constants.MSG_LOG_HISTORY_IS_EMPTY)
    except:
        bot.send_message(message.chat.id, 'Данная функция временно не работает')
        MessengerManager.log_data('Команда /getinfolog не сработала', level='warning')


@bot.message_handler(commands=['getwarninglog'])
def get_all_warning_logs(message):
    try:
        logs = logsRetriever.get_log(kind='warning')
        if logs:
            rnd_str = get_random_id(4)
            file_name = '{}_{}_{}_{}.log'.format('warning',
                                                 rnd_str,
                                                 message.chat.username,
                                                 datetime.datetime.now().strftime("%d-%m-%Y"))
            with open(file_name, 'w') as file:
                file.write(logs)
            try:
                log_file = open(file_name, 'rb')
                bot.send_document(message.chat.id, data=log_file)
            finally:
                log_file.close()
                os.remove(file_name)
        else:
            bot.send_message(message.chat.id, constants.MSG_LOG_HISTORY_IS_EMPTY)
    except:
        bot.send_message(message.chat.id, 'Данная функция временно не работает')
        MessengerManager.log_data('Команда /getwarninglog не сработала', level='warning')


@bot.message_handler(commands=['search'])
def repeat_all_messages(message):
    bot.send_message(message.chat.id, constants.MSG_NO_BUTTON_SUPPORT, parse_mode='HTML')


@bot.message_handler(commands=['fb'])
def leave_feedback(message):
    feedback = message.text[4:].strip()
    if feedback:
        create_feedback(message.chat.id,
                        datetime.datetime.fromtimestamp(message.date),
                        feedback)
        bot.send_message(message.chat.id, constants.MSG_WE_GOT_YOUR_FEEDBACK)
    else:
        bot.send_message(message.chat.id,
                         constants.MSG_LEAVE_YOUR_FEEDBACK,
                         parse_mode='HTML')


@bot.message_handler(commands=['getfeedback'])
def get_user_feedbacks(message):
    fbs = get_feedbacks()
    if fbs:
        bot.send_message(message.chat.id, fbs)
    else:
        bot.send_message(message.chat.id, 'Отзывов нет')


@bot.message_handler(commands=['class'])
def get_classification(message):
    msg = message.text[len('class') + 1:].split()
    print(msg)
    if msg:
        if len(msg) != 2:
            msg_str = 'Использовано {} параметр(ов). Введите куб, а затем измерение через пробел'
            bot.send_message(message.chat.id, msg_str.format(len(msg)))
        else:
            values = get_classification_for_dimension(msg[0].upper(), msg[1])
            if values:
                try:
                    proc_values = values[:15]
                except IndexError:
                    proc_values = values

                params = '\n'.join([
                                       '{}. {}'.format(idx + 1, val) for idx, val in enumerate(proc_values)
                                       ])
                bot.send_message(message.chat.id, params)
            else:
                bot.send_message(message.chat.id, 'Классификацию получить не удалось')
    else:
        bot.send_message(message.chat.id, 'Введите после команды куб и измерение через пробел')


# Text handler
@bot.message_handler(content_types=['text'])
def salute(message):
    greets = MessengerManager.greetings(message.text.strip())
    if greets:
        bot.send_message(message.chat.id, greets)
    else:
        process_response(message)


@bot.message_handler(content_types=['voice'])
def voice_processing(message):
    file_info = bot.get_file(message.voice.file_id)
    file_data = requests.get(
        'https://api.telegram.org/file/bot{0}/{1}'.format(
            API_TOKEN,
            file_info.file_path
        )
    )
    process_response(message, input_format='voice', file_content=file_data.content)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == 'intro_video':
        bot.send_message(call.message.chat.id, 'https://youtu.be/swok2pcFtNI')
    elif call.data == 'correct_response':
        request_id = call.message.text.split()[-1]
        MessengerManager.log_data('ID-запроса: {}\tМодуль: {}\tКорректность: {}'.format(
            request_id,
            __name__,
            '+'
        ))
    elif call.data == 'incorrect_response':
        request_id = call.message.text.split()[-1]
        MessengerManager.log_data('ID-запроса: {}\tМодуль: {}\tКорректность: {}'.format(
            request_id,
            __name__,
            '-'
        ))


def process_response(message, input_format='text', file_content=None):
    request_id = uuid.uuid4()
    user_name = user_name_str.format(message.chat.first_name, message.chat.last_name)

    bot.send_chat_action(message.chat.id, 'typing')
    if input_format == 'text':
        result = MessengerManager.make_request(
            message.text,
            'TG',
            message.chat.id,
            user_name,
            request_id
        )
    else:
        result = MessengerManager.make_voice_request(
            "TG",
            message.chat.id,
            user_name,
            request_id,
            bytes=file_content
        )

    if result.docs_found:
        process_cube_questions(
            message,
            result.cube_documents,
            request_id,
            input_format=input_format
        )
        process_minfin_questions(message, result.minfin_documents)
    else:
        bot.send_message(message.chat.id, constants.ERROR_NO_DOCS_FOUND)


def process_cube_questions(message, cube_result, request_id, input_format):
    if cube_result.status:
        is_input_text = (input_format == 'text')
        response_str = parse_feedback(cube_result.message, not is_input_text).format(
            cube_result.response,
            request_id
        )

        bot.send_message(
            message.chat.id,
            response_str,
            parse_mode='HTML',
            reply_markup=constants.RESPONSE_QUALITY
        )
        bot.send_chat_action(message.chat.id, 'upload_audio')
        bot.send_voice(message.chat.id, text_to_speech(cube_result.response))
        stats_pattern = (
            'Сред. score: {}\n' +
            'Мин. score: {}\n' +
            'Макс. score: {}\n' +
            'Score куба: {}\n' +
            'Суммарный score: {}'
        )
        stats = stats_pattern.format(
            cube_result.avg_score,
            cube_result.min_score,
            cube_result.max_score,
            cube_result.cube_score,
            cube_result.sum_score
        )
        bot.send_message(message.chat.id, stats)
    else:
        if cube_result.message:
            bot.send_message(message.chat.id, cube_result.message)


def process_minfin_questions(message, minfin_result):
    if minfin_result.status:
        bot.send_message(message.chat.id,
                         'Datatron понял ваш вопрос как *"{}"*'.format(minfin_result.question),
                         parse_mode='Markdown')
        if minfin_result.score < 20:
            msg_str = (
                'Score найденного Минфин документа *({})* равен *{}*, ' +
                'что меньше порогового значений в *20*.'
            )
            bot.send_message(message.chat.id,
                             msg_str.format(minfin_result.number, minfin_result.score),
                             parse_mode='Markdown')
            return

        if minfin_result.full_answer:
            bot.send_message(message.chat.id,
                             '*Ответ:* {}'.format(minfin_result.full_answer),
                             parse_mode='Markdown', reply_to_message_id=message.message_id)
        # может быть несколько
        if minfin_result.link_name:
            if isinstance(minfin_result.link_name, list):
                link_output_str = []
                for idx, (ln, l) in enumerate(zip(minfin_result.link_name, minfin_result.link)):
                    link_output_str.append('{}. [{}]({})'.format(idx + 1, ln, l))
                link_output_str.insert(
                    0,
                    '*Дополнительные результаты* можно посмотреть по ссылкам:'
                )
                bot.send_message(message.chat.id, '\n'.join(link_output_str), parse_mode='Markdown')
            else:
                link_output_str = '*Дополнительные результаты* можно посмотреть по ссылке:'
                bot.send_message(
                    message.chat.id,
                    '{}\n[{}]({})'.format(
                        link_output_str,
                        minfin_result.link_name,
                        minfin_result.link
                    ),
                    parse_mode='Markdown'
                )
        # может быть несколько
        if minfin_result.picture_caption:
            if isinstance(minfin_result.picture_caption, list):
                for pc, p in zip(minfin_result.picture_caption, minfin_result.picture):
                    with open('data/minfin/img/{}'.format(p), 'rb') as picture:
                        bot.send_photo(message.chat.id, picture, caption=pc)
            else:
                with open('data/minfin/img/{}'.format(minfin_result.picture), 'rb') as picture:
                    bot.send_photo(message.chat.id, picture, caption=minfin_result.picture_caption)
        # может быть несколько
        if minfin_result.document_caption:
            if isinstance(minfin_result.document_caption, list):
                for dc, d in zip(minfin_result.document_caption, minfin_result.document):
                    with open('data/minfin/doc/{}'.format(d), 'rb') as document:
                        bot.send_document(message.chat.id, document, caption=dc)
            else:
                with open('data/minfin/doc/{}'.format(minfin_result.document), 'rb') as document:
                    bot.send_document(
                        message.chat.id,
                        document,
                        caption=minfin_result.document_caption
                    )

        bot.send_chat_action(message.chat.id, 'upload_audio')
        bot.send_voice(message.chat.id, text_to_speech(minfin_result.short_answer))
        bot.send_message(message.chat.id, 'Score: {}'.format(minfin_result.score))


def parse_feedback(fb, user_request_notification=False):
    fb_exp = fb['formal']
    fb_norm = fb['verbal']
    exp = '<b>Экспертная обратная связь</b>\nКуб: {}\nМера: {}\nИзмерения: {}'
    norm = '<b>Дататрон выделил следующие параметры (обычная обратная связь)</b>:\n{}'
    exp = exp.format(
        fb_exp['cube'], fb_exp['measure'],
        ', '.join([i['dim'] + ': ' + i['val'] for i in fb_exp['dims']])
    )
    norm = norm.format(
        '1. {}\n'.format(fb_norm['measure']) +
        '\n'.join([str(idx + 2) + '. ' + i for idx, i in enumerate(fb_norm['dims'])])
    )

    user_request = ''
    if user_request_notification:
        user_request = '<b>Ваш запрос</b>\nДататрон решил, что Вы его спросили следующее: "{}"\n\n'
        user_request = user_request.format(fb['user_request'])

    formatted_feedback = '{}{}\n\n{}'.format(user_request, exp, norm)
    formatted_feedback += '\n\n<b>Ответ: {}</b>\nID-запроса: {}'
    return formatted_feedback


# polling cycle
if __name__ == '__main__':
    for admin_id in SETTINGS.ADMIN_TELEGRAM_ID:
        bot.send_message(admin_id, "ADMIN_INFO: Бот запушен")

    bot.polling(none_stop=True)
