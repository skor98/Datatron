#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Бот телеграма для Datatron
"""

from time import sleep
import datetime
import json
import logging
import os
import random
import string

from flask import Flask, request, abort
import requests
import telebot
import uuid

from config import DATE_FORMAT, LOGS_PATH
from config import SETTINGS
from core.cube_classifier import CubeClassifier
from core.cube_docs_processing import CubeProcessor
from core.cube_or_minfin_classifier import CubeOrMinfinClassifier
from dbs.user_support_library import check_user_existence
from dbs.user_support_library import create_feedback
from dbs.user_support_library import create_user
from dbs.user_support_library import get_feedbacks
from kb.kb_support_library import get_good_queries
from logs_helper import LogsRetriever
from messenger_manager import MessengerManager
from speechkit import SpeechException
from speechkit import text_to_speech, speech_to_text
import constants


# pylint: disable=broad-except
bot = telebot.TeleBot(SETTINGS.TELEGRAM.API_TOKEN)
app = None

logsRetriever = LogsRetriever(LOGS_PATH)

user_name_str = '{} {}'

def get_random_id(id_len=4):
    """
    Генерируем случайную буквенно-цифровую последовательность из id_len символов
    """
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(random.choice(alphabet) for _ in range(id_len))


def send_log(message, log_kind, command_name):
    """
    Помогает отправлять конкретный тип логов.
    Также занимается обработкой ввода
    """

    splitted_message = message.text.split()
    if len(splitted_message) == 2 and splitted_message[1] == 'help':
        bot.send_message(
            message.chat.id,
            "Для указания времени в минутах используйте " +
            "{} 15".format(command_name)
        )
        return
    else:
        try:
            time_delta = int(splitted_message[1])
        except (ValueError, IndexError):
            # Значение по умолчание: день
            time_delta = 60 * 24

    logs = logsRetriever.get_log(kind=log_kind, time_delta=time_delta)
    if logs:
        rnd_str = get_random_id()
        if not os.path.exists("tmp"):
            os.makedirs("tmp")
        path_to_log_file = os.path.join('tmp', '{}_{}_{}_{}.log'.format(
            log_kind,
            rnd_str,
            message.chat.username,
            datetime.datetime.now().strftime(DATE_FORMAT)
        ))

        with open(path_to_log_file, 'w', encoding='utf-8') as file:
            file.write(logs)
        try:
            with open(path_to_log_file, 'rb') as log_file:
                bot.send_document(message.chat.id, data=log_file)
        finally:
            os.remove(path_to_log_file)
    else:
        bot.send_message(message.chat.id, constants.MSG_LOG_HISTORY_IS_EMPTY)


def catch_bot_exception(message, command_name: str, err):
    """
    Обрабатывает исключения на самом верху обработчиков бота
    """

    bot.send_message(message.chat.id, 'Данная функция временно не работает')
    logging.exception(err)
    logging.warning('Команда {} не сработала'.format(command_name))


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Обработка команды /start"""

    try:
        bot.send_message(
            message.chat.id,
            constants.TELEGRAM_START_MSG,
            parse_mode='Markdown'
        )

        if not check_user_existence(message.chat.id):
            full_user_name = None
            if message.chat.first_name and message.chat.last_name:
                full_user_name = user_name_str.format(
                    message.chat.first_name,
                    message.chat.last_name
                )

            create_user(
                message.chat.id,
                message.chat.username,
                full_user_name
            )
    except Exception as err:
        catch_bot_exception(message, "/start", err)


@bot.message_handler(commands=['help'])
def send_help(message):
    try:
        bot.send_message(
            message.chat.id,
            constants.HELP_MSG,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    except Exception as err:
        catch_bot_exception(message, "/help", err)


@bot.message_handler(commands=['idea'])
def get_query_examples(message):
    try:
        possible_queries = get_good_queries(count=5)

        bot.send_message(
            message.chat.id,
            "Вы *можете спросить:*",
            parse_mode='Markdown',
            reply_markup=idea_dynamic_buttons(
                possible_queries
            )
        )
    except Exception as err:
        catch_bot_exception(message, "/idea", err)


@bot.message_handler(commands=['about'])
def send_about(message):
    try:
        bot.send_message(
            message.chat.id,
            constants.ABOUT_MSG,
            parse_mode='Markdown',
            reply_markup=constants.ABOUT_KEYBOARD,
            disable_web_page_preview=True
        )
    except Exception as err:
        catch_bot_exception(message, "/about", err)


@bot.message_handler(commands=['getqueries'])
def get_queries_logs(message):
    """
    Возвращает запросы к ядру текущего пользователя
    """
    if not is_has_admin_rights(message.chat.id):
        return
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
                kind='queries',
                user_id=message.chat.id,
                time_delta=time_span
            )
        else:
            logs = logsRetriever.get_log(kind='queries', user_id=message.chat.id)

        if logs:
            send_very_long_message(
                message.chat.id,
                'Ваши вопросы:\n' + logs
            )
        else:
            bot.send_message(message.chat.id, constants.MSG_LOG_HISTORY_IS_EMPTY)
    except Exception as err:
        catch_bot_exception(message, "/getqueries", err)


@bot.message_handler(commands=['getallqueries'])
def get_all_queries_logs(message):
    """
    Возвращает все запросы к ядру
    """
    if not is_has_admin_rights(message.chat.id):
        return
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
                kind='queries',
                user_id=message.chat.id,
                time_delta=time_span
            )
        else:
            logs = logsRetriever.get_log(kind='queries', user_id="all")

        if logs:
            send_very_long_message(
                message.chat.id,
                'Вопросы от всех пользователей:\n' + logs
            )
        else:
            bot.send_message(message.chat.id, constants.MSG_LOG_HISTORY_IS_EMPTY)
    except Exception as err:
        catch_bot_exception(message, "/getallqueries", err)


@bot.message_handler(commands=['getlog'])
def get_all_logs(message):
    """Отправляет файл с логами"""
    if not is_has_admin_rights(message.chat.id):
        return
    with open(LOGS_PATH, 'rb') as log_file:
        bot.send_document(message.chat.id, data=log_file)


@bot.message_handler(commands=['getsessionlog'])
def get_session_logs(message):
    if not is_has_admin_rights(message.chat.id):
        return
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
            send_very_long_message(
                message.chat.id,
                'Логи вашей сессии:\n' + logs
            )
        else:
            bot.send_message(message.chat.id, constants.MSG_LOG_HISTORY_IS_EMPTY)
    except Exception as err:
        catch_bot_exception(message, "/getsessionlog", err)


@bot.message_handler(commands=['getinfolog'])
def get_all_info_logs(message):
    if not is_has_admin_rights(message.chat.id):
        return
    try:
        send_log(message, "info", "/getinfolog")
    except Exception as err:
        catch_bot_exception(message, "/getinfolog", err)


@bot.message_handler(commands=['getwarninglog'])
def get_all_warning_logs(message):
    if not is_has_admin_rights(message.chat.id):
        return
    try:
        send_log(message, "warning", "/getwarninglog")
    except Exception as err:
        catch_bot_exception(message, "/getwarninglog", err)


@bot.message_handler(commands=['search'])
def repeat_all_messages(message):
    try:
        bot.send_message(
            message.chat.id,
            constants.MSG_NO_BUTTON_SUPPORT,
            parse_mode='Markdown'
        )
    except Exception as err:
        catch_bot_exception(message, "/search", err)


@bot.message_handler(commands=['fb'])
def leave_feedback(message):
    try:
        feedback = message.text[4:].strip()
        if feedback:
            create_feedback(
                message.chat.id,
                datetime.datetime.fromtimestamp(message.date),
                feedback
            )
            bot.send_message(message.chat.id, constants.MSG_WE_GOT_YOUR_FEEDBACK)
        else:
            bot.send_message(
                message.chat.id,
                constants.MSG_LEAVE_YOUR_FEEDBACK,
                parse_mode='Markdown'
            )
    except Exception as err:
        catch_bot_exception(message, "/fb", err)


@bot.message_handler(commands=['getfeedback'])
def get_user_feedbacks(message):
    if not is_has_admin_rights(message.chat.id):
        return
    try:
        fbs = get_feedbacks()
        if fbs:
            bot.send_message(message.chat.id, fbs)
        else:
            bot.send_message(message.chat.id, 'Отзывов нет')
    except Exception as err:
        catch_bot_exception(message, "/getfeedback", err)


@bot.message_handler(commands=['whatcube'])
def what_cube_handler(message):
    """
    Позволяет протестировать как ведёт себя классификатор типов кубов на сервере
    /whatcube Цели разработки бюджетного прогноза РФ
    """
    if not is_has_admin_rights(message.chat.id):
        return
    try:
        clf = CubeClassifier.inst()
        req = " ".join(message.text.split()[1:])
        text_to_send = "Бот думает, что это один из кубов: \n"
        for ind, elem in tuple(enumerate(clf.predict_proba(req)))[:3]:
            cube_name, proba = elem
            text_to_send += "{}. {} -> *{}%*\n".format(ind + 1, cube_name, round(proba * 100, 2))
        bot.send_message(message.chat.id, text_to_send, parse_mode='Markdown')
    except Exception as err:
        catch_bot_exception(message, "/whatcube", err)


@bot.message_handler(commands=['whattype'])
def what_type_handler(message):
    """
    Позволяет протестировать как ведёт себя классификатор куб/минфин на сервере
    /whattype Цели разработки бюджетного прогноза РФ
    """
    if not is_has_admin_rights(message.chat.id):
        return
    try:
        clf = CubeOrMinfinClassifier.inst()
        req = " ".join(message.text.split()[1:])
        text_to_send = "Возможные типы документа: \n"
        for ind, elem in tuple(enumerate(clf.predict_proba(req))):
            cube_name, proba = elem
            text_to_send += "{}. {} -> *{}%*\n".format(ind + 1, cube_name, round(proba * 100, 2))
        bot.send_message(message.chat.id, text_to_send, parse_mode='Markdown')
    except Exception as err:
        catch_bot_exception(message, "/whattype", err)


@bot.message_handler(content_types=['text'])
def main_search_function(message):
    try:
        pers_answer = MessengerManager.personalization(message.text)

        if pers_answer:
            bot.send_chat_action(message.chat.id, 'typing')
            bot.send_message(
                message.chat.id,
                pers_answer,
                parse_mode='Markdown'
            )
        else:
            process_response(message)
    except Exception as err:
        catch_bot_exception(message, "/text", err)


@bot.message_handler(content_types=['voice'])
def voice_processing(message):
    file_info = bot.get_file(message.voice.file_id)
    file_data = requests.get(
        'https://api.telegram.org/file/bot{0}/{1}'.format(
            SETTINGS.TELEGRAM.API_TOKEN,
            file_info.file_path
        )
    )

    try:
        if file_data.content:
            text = speech_to_text(bin_audio=file_data.content)
    except SpeechException:
        bot.send_message(message.chat.id, constants.ERROR_CANNOT_UNDERSTAND_VOICE)

    pers_answer = MessengerManager.personalization(text)
    if pers_answer:
        bot.send_chat_action(message.chat.id, 'upload_audio')
        bot.send_voice(
            message.chat.id,
            text_to_speech(pers_answer)
        )
    else:
        # TODO: подумать о том, как избежать двойной конвертации
        process_response(
            message, input_format='voice', file_content=file_data.content)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    """Обработка inline-кнопок"""

    if call.data == 'intro_video':
        bot.send_message(
            call.message.chat.id,
            'https://youtu.be/swok2pcFtNI'
        )
    elif call.data == 'correct_response':
        bot.answer_callback_query(
            callback_query_id=call.id,
            show_alert=False,
            text=constants.MSG_USER_SAID_CORRECT_ANSWER
        )

        logging.info('Корректность: {}'.format('+'))
    elif call.data == 'incorrect_response':
        bot.answer_callback_query(
            callback_query_id=call.id,
            show_alert=False,
            text=constants.MSG_USER_SAID_INCORRECT_ANSWER
        )

        logging.info('Корректность: {}'.format('-'))
    elif call.data == 'look_also_1':
        process_look_also_request(call, 1)
    elif call.data == 'look_also_2':
        process_look_also_request(call, 2)
    elif call.data == 'look_also_3':
        process_look_also_request(call, 3)
    elif call.data == 'look_also_4':
        process_look_also_request(call, 4)
    elif call.data == 'look_also_5':
        process_look_also_request(call, 5)


def send_admin_messages(text, crit=False):
    """Безопасная отправка уведомлений администраторам"""
    
    if crit:
        logging.critical("TG_ADMIN_ALERT:\t{}".format(text))
        msg = "ADMIN_ALERT: {}".format(text)
    else:
        logging.info("TG_ADMIN_INFO:\t{}".format(text))
        msg = "ADMIN_INFO: {}".format(text)

    for admin_id in SETTINGS.TELEGRAM.ADMIN_IDS:
        try:
            bot.send_message(admin_id, msg)
        except telebot.apihelper.ApiException:
            logging.critical("Админ {} недоступен для отправки сообщения!".format(admin_id))


def is_has_admin_rights(user_id):
    """Проверяет, что у пользователя есть права администратора"""
    return user_id in SETTINGS.TELEGRAM.ADMIN_IDS


def process_response(message, input_format='text', file_content=None):
    request_id = str(uuid.uuid4())

    full_user_name = None
    if message.chat.first_name and message.chat.last_name:
        full_user_name = user_name_str.format(
            message.chat.first_name,
            message.chat.last_name
        )

    bot.send_chat_action(message.chat.id, 'typing')

    if input_format == 'text':
        result = MessengerManager.make_request(
            message.text,
            'TG',
            message.chat.id,
            full_user_name,
            request_id
        )
    else:
        result = MessengerManager.make_voice_request(
            "TG",
            message.chat.id,
            full_user_name,
            request_id,
            bin_audio=file_content
        )

    # Если ответ найден
    if result.status:
        # Если ответ является ответом по кубам
        if result.answer.type == 'cube':
            process_cube_questions(
                message,
                result.answer,
                result.confidence,
                request_id,
                input_format
            )

        # Если ответ является ответом по минфину
        else:
            process_minfin_questions(
                message,
                result.answer,
                result.confidence,
                input_format,
            )

        extra_results = look_further(result)

        # адаптация количество смотри также в зависимости от его длины
        length = 0
        for idx, elem in enumerate(extra_results):
            if length + len(elem) <= 400:
                length += len(elem)
            else:
                extra_results = extra_results[:idx]
                break

        if extra_results:
            bot.send_message(
                message.chat.id,
                "*Смотри также:*\n" + ''.join(extra_results),
                parse_mode='Markdown',
                reply_markup=see_more_buttons_dynamic(
                    len(extra_results)
                )
            )
    else:
        user_request = ''
        if input_format != 'text':
            user_request = '*Ваш вопрос*\n"{}"\n\n'
            user_request = user_request.format(result.user_request)

        if result.bad_content:
            bot.send_message(
                message.chat.id,
                user_request + constants.ERROR_REQUEST_CONTAINS_BAD_WORD,
                parse_mode='Markdown'
            )
        else:
            bot.send_message(
                message.chat.id,
                user_request + constants.ERROR_NO_DOCS_FOUND,
                parse_mode='Markdown'
            )

        extra_results = look_further(result)
        if extra_results:
            bot.send_message(
                message.chat.id,
                "Вы *можете посмотреть:*\n" + ''.join(extra_results),
                parse_mode='Markdown',
                reply_markup=see_more_buttons_dynamic(
                    len(extra_results)
                )
            )


def process_cube_questions(
        message, cube_result, ans_confidence,
        request_id, input_format
):
    is_input_text = (input_format == 'text')

    if cube_result.status:
        form_feedback(
            message, request_id, cube_result,
            ans_confidence, not is_input_text
        )

        if SETTINGS.TELEGRAM.ENABLE_ADMIN_MESSAGES:
            stats_pattern = (
                'Суммарный score: {}'
            )

            stats = stats_pattern.format(
                cube_result.score['sum']
            )

            bot.send_message(message.chat.id, stats)
    else:
        user_request = ''
        if not is_input_text:
            user_request = '*Ваш вопрос*\n"{}"\n\n'
            user_request = user_request.format(cube_result.feedback['user_request'])

        feedback = '{}\n*Вопрос после обработки*\n{}\n\n'.format(
            verbal_feedback(cube_result),
            cube_result.feedback['pretty_feedback']
        )

        bot.send_message(
            message.chat.id,
            user_request + feedback + cube_result.message,
            parse_mode='Markdown'
        )


def process_minfin_questions(
        message, minfin_result, ans_confidence, input_format
):
    is_input_text = (input_format == 'text')

    feedback_str = '{user_request}{confidence}{feedback}*Ответ*\n{answer}'

    if is_input_text:
        user_request = ''
    else:
        user_request = '*Ваш вопрос*\n"{}"\n\n'.format(
            minfin_result.user_request
        )

    if ans_confidence:
        confidence = '*Вопрос после обработки*\n'
    else:
        confidence = '*Возможно, вы хотели спросить*\n'

    if request_equality(minfin_result):
        confidence = ''
        feedback = ''
    else:
        feedback = '{}\n\n'.format(minfin_result.question)

    bot.send_message(
        message.chat.id,
        feedback_str.format(
            user_request=user_request,
            confidence=confidence,
            feedback=feedback,
            answer=minfin_result.full_answer),
        parse_mode='Markdown',
        reply_markup=constants.RESPONSE_QUALITY
    )

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

            bot.send_message(
                message.chat.id,
                '\n'.join(link_output_str),
                parse_mode='Markdown'
            )
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

    # Отправлять голосовой ответ только в случае, если он отличается от полного
    if len(minfin_result.short_answer) != len(minfin_result.full_answer):
        bot.send_chat_action(message.chat.id, 'upload_audio')
        bot.send_voice(
            message.chat.id,
            text_to_speech(minfin_result.short_answer),
            caption="Краткий ответ"
        )

    if SETTINGS.TELEGRAM.ENABLE_ADMIN_MESSAGES:
        bot.send_message(message.chat.id, 'Score: {}'.format(minfin_result.score))


def request_equality(minfin_result):
    """
    Равенство заданного и найденного вопроса
    """

    chars_to_replace = {
        '?': '',
        ',': '',
        '"': '',
        '.': '',
        '!': '',
        'ё': 'е'
    }

    low_user_request = minfin_result.user_request.lower()
    low_minfin_question = minfin_result.question.lower()

    for key, value in chars_to_replace.items():
        low_user_request = low_user_request.replace(key, value)
        low_minfin_question = low_minfin_question.replace(key, value)

    return bool(low_user_request == low_minfin_question)


def form_feedback(
        message, request_id, cube_result,
        ans_confidence, user_request_notification=False
):
    feedback_str = (
        '{user_req}{expert_fb}{separator}{verbal_fb}{separator}'
        '{pretty_feed}\n\nОтвет: *{answer}*{time_data_relevance}'
    )
    separator = ''
    expert_str = ''
    verbal_str = ''

    confidence = '*Вопрос после обработки*\n{}'

    if not ans_confidence:
        confidence = 'Возможно, вы хотели спросить: {}'

    pretty_feed = confidence.format(
        cube_result.feedback['pretty_feedback']
    )

    user_request = ''
    if user_request_notification:
        user_request = '*Ваш вопрос*\n"{}"\n\n'
        user_request = user_request.format(cube_result.feedback['user_request'])

    if SETTINGS.TELEGRAM.ENABLE_ADMIN_MESSAGES:
        expert_str = expert_feedback(cube_result)
        separator = '\n'
        verbal_str = verbal_feedback(cube_result)

    data_relevance = CubeProcessor.get_time_data_relevance(cube_result)
    data_relevance = data_relevance if data_relevance else ''
    if data_relevance:
        data_relevance = '\nАктуальность данных: {}'.format(
            data_relevance
        )

    feedback = feedback_str.format(
        user_req=user_request,
        expert_fb=expert_str,
        separator=separator,
        verbal_fb=verbal_str,
        answer=cube_result.formatted_response,
        time_data_relevance=data_relevance,
        pretty_feed=pretty_feed
    )

    bot.send_message(
        message.chat.id,
        feedback,
        parse_mode='Markdown',
        reply_markup=constants.RESPONSE_QUALITY
    )


def expert_feedback(cube_result):
    expert_fb = cube_result.feedback['formal']

    expert_str = '*Экспертная обратная связь*\n' \
                 '- Куб: {}\n- Мера: {}\n- Измерения: {}\n'

    expert_str = expert_str.format(
        expert_fb['cube'],
        expert_fb['measure'].replace('_', '\_'),
        ', '.join([i['dim'] + ': ' + i['val'] for i in expert_fb['dims']])
    )

    return expert_str


def verbal_feedback(cube_result, title='Найдено в базе данных'):
    """Переработка найденного докумнета по куб для выдачи в 'смотри также'"""

    verbal_fb_list = []
    verbal_fb = cube_result.feedback['verbal']

    verbal_fb_list.append(verbal_fb['domain'])

    if verbal_fb['measure'] != 'значение':
        verbal_fb_list.append('Мера: ' + verbal_fb['measure'].lower())

    verbal_fb_list.extend('{}: {}'.format(
        item['dimension_caption'],
        item['member_caption']) for item in verbal_fb['dims'])

    verbal_str = '{}\n'.format(verbal_fb_list[0])
    verbal_str += ''.join(['- {}\n'.format(elem) for elem in verbal_fb_list[1:]])
    return '*{}*\n{}'.format(title, verbal_str)


def look_also_for_cube(cube_result):
    feedback = cube_result.feedback.get('pretty_feedback', '...')

    if SETTINGS.TELEGRAM.ENABLE_ADMIN_MESSAGES:
        look_also_str = '{} ({}: {})'.format(
            feedback,
            '*База знаний*',
            cube_result.get_score()
        )
    else:
        look_also_str = '{}'.format(feedback)

    return look_also_str


def answer_to_look_also_format(answer):
    if answer.type == 'cube':
        return look_also_for_cube(answer)
    else:
        if SETTINGS.TELEGRAM.ENABLE_ADMIN_MESSAGES:
            return '{} ({}: {})'.format(
                answer.question,
                "*Минфин*",
                answer.score
            )
        else:
            return '{}'.format(answer.question)


def see_more_buttons_dynamic(number_of_questions):
    """Динамическая клавиатура для смотри также"""

    buttons = []
    for i in range(1, number_of_questions + 1):
        buttons.append(
            {
                'text': str(i),
                'callback_data': 'look_also_' + str(i)
            }
        )

    return json.dumps({
        'inline_keyboard': [buttons]
    })


def idea_dynamic_buttons(questions: list):
    """Динамическая клавиатура для смотри также"""

    buttons = []
    for idx, question in enumerate(questions):
        buttons.append(
            [{
                'text': question
            }]
        )

    buttons.append([{'text': '/idea'}])

    return json.dumps({
        'keyboard': buttons
    })


def get_look_also_question_by_num(message: str, num: int):
    """
    Возвращает запрос из смотри также под заданным номером
    """
    message = [msg[msg.find('.') + 1:msg.rfind('(')].strip('\t ')
               for msg in message.split('\n')]

    return message[num]


def process_look_also_request(call, num: int):
    """
    Обработка см.также запросов по нажатию инлайн-кнопки
    """

    look_also_req = get_look_also_question_by_num(
        call.message.text, num)

    call.message.text = look_also_req

    main_search_function(call.message)


def look_further(result):
    """Смотри также/Вы можете посмотреть"""

    # Если "смотри также" есть
    if result.more_answers_order:
        # Формирование общего массива c ответами
        more_answers = []

        if result.more_cube_answers:
            for cube_answer in result.more_cube_answers:
                more_answers.append(cube_answer)

        if result.more_minfin_answers:
            for minfin_answer in result.more_minfin_answers:
                more_answers.append(minfin_answer)

        # Сортировка ответов
        more_answers = sorted(
            more_answers,
            key=lambda elem: elem.order
        )

        # Формирование списка "смотри также"
        look_also = []
        for answer in more_answers:
            look_also.append(
                answer_to_look_also_format(answer)
            )

        look_also = ['{}. {}\n'.format(idx + 1, elem)
                     for idx, elem in enumerate(look_also)]

        return look_also
    else:
        return []


def send_very_long_message(chat_id, text, message_length=4000):
    """Отправка сообщения длинее 4096 UTF-8 символов"""

    while text:
        bot.send_message(chat_id, text[:message_length])

        text = text[message_length:]


if SETTINGS.TELEGRAM.ENABLE_WEBHOOK:

    app = Flask(__name__)

    WEBHOOK_URL_BASE = "{}:{}/telebot".format(
        SETTINGS.WEB_SERVER.PUBLIC_LINK,
        SETTINGS.WEB_SERVER.PUBLIC_PORT
    )
    WEBHOOK_URL_PATH = "/{}/".format(SETTINGS.TELEGRAM.API_TOKEN)

    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH)


    @app.route('/', methods=['GET', 'HEAD'])
    def main():
        """Тестовая страница"""
        return '<center><h1>Welcome to Datatron Telegram Webhook page</h1></center>'


    @app.route(WEBHOOK_URL_PATH, methods=['POST'])
    def webhook():
        if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return ''
        else:
            abort(403)


def long_polling(attempt=0):
    bot.remove_webhook()
    send_admin_messages(constants.TELEGRAM_ADMIN['START'], crit=False)
    try:
        bot.polling(none_stop=True)
    except ConnectionError as err:
        send_admin_messages(constants.TELEGRAM_ADMIN['CONNECTION_ERROR'], crit=True)
        if attempt < 5:
            sleep(20)
            long_polling(attempt=attempt + 1)
        else:
            send_admin_messages(constants.TELEGRAM_ADMIN['FAILURE'], crit=True)


# polling cycle
if __name__ == '__main__':
    if not SETTINGS.TELEGRAM.ENABLE_WEBHOOK:
        long_polling()
