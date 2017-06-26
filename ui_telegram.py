from telebot import types
from logs_retriever import LogsRetriever
from db.user_support_library import check_user_existence, create_user, create_feedback, get_feedbacks, \
    define_question_mode, define_expert_mode, get_question_mode, get_expert_mode
from kb.kb_support_library import get_classification_for_dimension
from speechkit import text_to_speech
from messenger_manager import MessengerManager
from text_preprocessing import TextPreprocessing
from config import SETTINGS
from speechkit import speech_to_text

import telebot
import requests
import constants
import config
import uuid
import datetime
import random
import string
import os
import time

API_TOKEN = config.SETTINGS.TELEGRAM_API_TOKEN
bot = telebot.TeleBot(API_TOKEN)

logsRetriever = LogsRetriever('logs.log')

user_name_str = '{} {}'


# /start command handler; send start-message to the user
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, constants.TELEGRAM_START_MSG, parse_mode='HTML')
    if not check_user_existence(message.chat.id):
        create_user(message.chat.id,
                    message.chat.username,
                    ' '.join([message.chat.first_name, message.chat.last_name]))


# /help command handler; send hello-message to the user
@bot.message_handler(commands=['help'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        constants.HELP_MSG,
        parse_mode='HTML',
        reply_markup=constants.HELP_KEYBOARD,
        disable_web_page_preview=True)


@bot.message_handler(commands=['getlog'])
def get_all_logs(message):
    log_file = open('logs.log', 'rb')
    bot.send_document(message.chat.id, data=log_file)
    log_file.close()


@bot.message_handler(commands=['getsessionlog'])
def get_session_logs(message):
    try:
        time_span = None
        try:
            time_span = int(message.text.split()[1])
        except IndexError:
            pass
        if time_span:
            logs = logsRetriever.get_log(kind='session', user_id=message.chat.id, time_delta=time_span)
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
        if logs:
            rnd_str = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(4))
            file_name = '{}_{}_{}_{}.log'.format('info',
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
        MessengerManager.log_data('Команда /getinfolog не сработала', level='warning')


@bot.message_handler(commands=['getwarninglog'])
def get_all_info_logs(message):
    try:
        logs = logsRetriever.get_log(kind='warning')
        if logs:
            rnd_str = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(4))
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
    if not check_user_existence(message.chat.id):
        create_user(message.chat.id,
                    message.chat.username,
                    ' '.join([message.chat.first_name, message.chat.last_name]))
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
                params = '\n'.join(['{}. {}'.format(idx + 1, val) for idx, val in enumerate(values[:15])])
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
        if not check_user_existence(message.chat.id):
            create_user(message.chat.id,
                        message.chat.username,
                        ' '.join([message.chat.first_name, message.chat.last_name]))

        process_response(message)


@bot.message_handler(content_types=['voice'])
def voice_processing(message):
    if not check_user_existence(message.chat.id):
        create_user(message.chat.id,
                    message.chat.username,
                    ' '.join([message.chat.first_name, message.chat.last_name]))

    file_info = bot.get_file(message.voice.file_id)
    file = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(API_TOKEN, file_info.file_path))

    # Госоловое пеперключение
    stt = speech_to_text(bytes=file.content)
    print(stt)

    # Голосовое включение экспертной обратной связи
    tp = TextPreprocessing(uuid.uuid4())
    stt = tp.normalization(stt)
    print(stt)
    if 'экспертный' in stt:
        if 'включить' in stt:
            define_expert_mode(message.chat.id, 1)
            bot.send_message(message.chat.id, 'Режим экспертной обратной связи *включен*', parse_mode='Markdown')
        elif 'выключить' in stt:
            define_expert_mode(message.chat.id, 0)
            bot.send_message(message.chat.id, 'Режим экспертной обратной связи *выключен*', parse_mode='Markdown')
    # Голосовое включение вопрос министерства финансов
    elif 'режим' in stt:
        if 'финансы' in stt:
            define_question_mode(message.chat.id, 1)
            bot.send_message(message.chat.id, 'Включен *режим вопросов о Минфине*', parse_mode='Markdown')
        elif 'знание' in stt:
            define_question_mode(message.chat.id, 0)
            bot.send_message(message.chat.id, 'Включен *режим вопросам по базе знаний*', parse_mode='Markdown')
    else:
        process_response(message, format='voice', file_content=file.content)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == 'intro_video':
        bot.send_message(call.message.chat.id, 'https://youtu.be/swok2pcFtNI')
    elif call.data == 'correct_response':
        request_id = call.message.text.split()[-1]
        MessengerManager.log_data('ID-запроса: {}\tМодуль: {}\tКорректность: {}'.format(request_id, __name__, '+'))
    elif call.data == 'incorrect_response':
        request_id = call.message.text.split()[-1]
        MessengerManager.log_data('ID-запроса: {}\tМодуль: {}\tКорректность: {}'.format(request_id, __name__, '-'))


# inline mode handler
@bot.inline_handler(lambda query: len(query.query) >= 0)
def query_text(query):
    input_message_content = query.query

    user_name = user_name_str.format(query.from_user.first_name, query.from_user.last_name)
    m2_result = MessengerManager.make_request_directly_to_m2(input_message_content, 'TG-INLINE',
                                                             query.from_user.id, user_name, uuid.uuid4())

    result_array = []
    if m2_result.status is False:  # in case the string is not correct we ask user to keep typing
        msg = types.InlineQueryResultArticle(id='0',
                                             title='Продолжайте ввод запроса',
                                             input_message_content=types.InputTextMessageContent(
                                                 message_text=input_message_content + '\nЗапрос не удался😢'
                                             ))
        result_array.append(msg)  # Nothing works without this list, I dunno why :P
        bot.answer_inline_query(query.id, result_array)

    else:
        try:
            msg_append_text = ':\n' + str(m2_result.response)
            title = str(m2_result.response)

            msg = types.InlineQueryResultArticle(id='1',
                                                 title=title,
                                                 input_message_content=types.InputTextMessageContent(
                                                     message_text=input_message_content + msg_append_text),
                                                 )
            result_array.append(msg)

        finally:
            bot.answer_inline_query(query.id, result_array)


def process_response(message, format='text', file_content=None):
    qm = get_question_mode(message.chat.id)
    if not qm:
        process_cube_questions(message, format=format, file_content=file_content)
    else:
        process_minfin_questions(message, format=format, file_content=file_content)


def process_cube_questions(message, format='text', file_content=None):
    start_time = time.time()
    request_id = uuid.uuid4()
    user_name = user_name_str.format(message.chat.first_name, message.chat.last_name)

    bot.send_chat_action(message.chat.id, 'typing')
    if format == 'text':
        result = MessengerManager.make_request(message.text, 'TG', message.chat.id, user_name, request_id)
    else:
        result = MessengerManager.make_voice_request("TG", message.chat.id, user_name, request_id, bytes=file_content)

    if not result.status:
        bot.send_message(message.chat.id, result.error)
    else:
        if format == 'text':
            # response_str = parse_feedback(result.feedback).format(result.response, request_id)
            response_str = parse_feedback_for_hackathon(message.chat.id, result.feedback).format(result.response)
        else:
            # response_str = parse_feedback(result.feedback, True).format(result.response, request_id)
            response_str = parse_feedback_for_hackathon(message.chat.id, result.feedback, True).format(result.response)

        bot.send_message(message.chat.id, result.message)
        # bot.send_message(message.chat.id, response_str, parse_mode='HTML', reply_markup=constants.RESPONSE_QUALITY)
        bot.send_message(message.chat.id, response_str, parse_mode='Markdown')

        before_tts = time.time() - start_time
        bot.send_chat_action(message.chat.id, 'upload_audio')
        bot.send_voice(message.chat.id, text_to_speech(result.response))
        after_tts = time.time() - start_time

        with open('speed_text.txt', 'a', encoding='utf-8') as file:
            file.write('{}\t{}\t{}\n'.format(message.text, before_tts, after_tts))


def process_minfin_questions(message, format='text', file_content=None):
    bot.send_chat_action(message.chat.id, 'typing')
    if format == 'text':
        result = MessengerManager.make_minfin_request(message.text)
    else:
        result = MessengerManager.make_minfin_request_voice(bytes=file_content)

    if result.status:
        bot.send_message(message.chat.id,
                         'Datatron понял ваш вопрос как *"{}"*'.format(result.question),
                         parse_mode='Markdown')
        if result.full_answer:
            bot.send_message(message.chat.id,
                             '*Ответ:* {}'.format(result.full_answer),
                             parse_mode='Markdown', reply_to_message_id=message.message_id)
        # может быть несколько
        if result.link_name:
            if type(result.link_name) is list:
                link_output_str = []
                for idx, (ln, l) in enumerate(zip(result.link_name, result.link)):
                    link_output_str.append('{}. [{}]({})'.format(idx + 1, ln, l))
                link_output_str.insert(0, '*Дополнительные результаты* можно посмотреть по ссылкам:')
                bot.send_message(message.chat.id, '\n'.join(link_output_str), parse_mode='Markdown')
            else:
                link_output_str = '*Дополнительные результаты* можно посмотреть по ссылке:'
                bot.send_message(message.chat.id,
                                 '{}\n[{}]({})'.format(link_output_str, result.link_name, result.link),
                                 parse_mode='Markdown')
        # может быть несколько
        if result.picture_caption:
            if type(result.picture_caption) is list:
                for pc, p in zip(result.picture_caption, result.picture):
                    with open('data/minfin/img/{}'.format(p), 'rb') as picture:
                        bot.send_photo(message.chat.id, picture, caption=pc)
            else:
                with open('data/minfin/img/{}'.format(result.picture), 'rb') as picture:
                    bot.send_photo(message.chat.id, picture, caption=result.picture_caption)
        # может быть несколько
        if result.document_caption:
            if type(result.document_caption) is list:
                for dc, d in zip(result.document_caption, result.document):
                    with open('data/minfin/doc/{}'.format(d), 'rb') as document:
                        bot.send_document(message.chat.id, document, caption=dc)
            else:
                with open('data/minfin/doc/{}'.format(result.document), 'rb') as document:
                    bot.send_document(message.chat.id, document, caption=result.document_caption)

        bot.send_chat_action(message.chat.id, 'upload_audio')
        bot.send_voice(message.chat.id, text_to_speech(result.short_answer))
    else:
        bot.send_message(message.chat.id, constants.ERROR_NO_DOCS_FOUND)


def parse_feedback(fb, user_request_notification=False):
    fb_exp = fb['formal']
    fb_norm = fb['verbal']
    exp = '<b>Экспертная обратная связь</b>\nКуб: {}\nМера: {}\nИзмерения: {}'
    norm = '<b>Дататрон выделил следующие параметры (обычная обратная связь)</b>:\n{}'
    exp = exp.format(fb_exp['cube'], fb_exp['measure'],
                     ', '.join([i['dim'] + ': ' + i['val'] for i in fb_exp['dims']]))
    norm = norm.format('1. {}\n'.format(
        fb_norm['measure']) + '\n'.join([str(idx + 2) + '. ' + i for idx, i in enumerate(fb_norm['dims'])]))

    cntk_response = '<b>CNTK разбивка</b>\n{}'
    r = ['{}. {}: {}'.format(idx + 1, i['tagmeaning'].lower(), i['word'].lower()) for idx, i in enumerate(fb['cntk'])]
    cntk_response = cntk_response.format(', '.join(r))

    user_request = ''
    if user_request_notification:
        user_request = '<b>Ваш запрос</b>\nДататрон решил, что Вы его спросили следующее: "{}"\n\n'
        user_request = user_request.format(fb['user_request'])

    formatted_feedback = '{}{}\n\n{}\n\n{}'.format(user_request, exp, norm, cntk_response)
    formatted_feedback += '\n\n<b>Ответ: {}</b>\nID-запроса: {}'
    return formatted_feedback


def parse_feedback_for_hackathon(user_id, fb, user_request_notification=False):
    fb_norm = fb['verbal']

    exp = ''
    if get_expert_mode(user_id):
        fb_exp = fb['formal']
        exp = '*Экспертная обратная связь*\nКуб: {}\nМера: {}\nИзмерения: {}\n'
        exp = exp.format(fb_exp['cube'], fb_exp['measure'],
                         ', '.join([i['dim'] + ': ' + i['val'] for i in fb_exp['dims']]))

    norm = '*Datatron выделил следующие параметры*:\n{}'
    norm = norm.format('\n'.join([str(idx + 1) + '. ' + i for idx, i in enumerate(fb_norm['dims'])]))

    user_request = ''
    if user_request_notification:
        user_request = '*Ваш запрос*\nДататрон решил, что Вы его спросили следующее: "{}"\n\n'
        user_request = user_request.format(fb['user_request'])

    formatted_feedback = '{}{}\n{}\n\n'.format(user_request, exp, norm)
    formatted_feedback += '*Ответ:*\n{}'
    return formatted_feedback


# polling cycle
if __name__ == '__main__':
    admin_id = SETTINGS.ADMIN_TELEGRAM_ID

    for _id in admin_id:
        bot.send_message(_id, "ADMIN_INFO: Бот запушен")

    bot.polling(none_stop=True)
