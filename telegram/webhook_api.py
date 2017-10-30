#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Серверная часть для вебхуков
"""

from flask import Flask, request, abort, redirect, url_for
from telebot.apihelper import ApiException
from telebot.types import Update

from config import SETTINGS
from telegram.bot_main import bot, bot_info_str, webhook_info_str


BOT_API_PATH = 'telebot'

WEBHOOK_URL = {'PATH': '/{}/'.format(SETTINGS.TELEGRAM.API_TOKEN)}

if hasattr(SETTINGS.WEB_SERVER, 'PUBLIC_LINK'):
    WEBHOOK_URL['DEFINED'] = True
    WEBHOOK_URL['BASE'] = '{}:{}/{}'.format(
        SETTINGS.WEB_SERVER.PUBLIC_LINK,
        SETTINGS.WEB_SERVER.PUBLIC_PORT,
        BOT_API_PATH
    )
    if SETTINGS.TELEGRAM.ENABLE_WEBHOOK:
        try:
            bot.set_webhook(WEBHOOK_URL['BASE'] + WEBHOOK_URL['PATH'])
        except ApiException:
            WEBHOOK_URL['DEFINED'] = False
else:
    WEBHOOK_URL['DEFINED'] = False

app = Flask(__name__)


@app.route('/', methods=['GET', 'HEAD'])
def main():
    """Тестовая страница"""
    content = ('<center>This is to Datatron Telegram Bot API section<br>\n'
               'API token is required to access bot info and list of available actions</center>')
    return content, 200


@app.route(WEBHOOK_URL['PATH'], methods=['GET', 'HEAD'])
def bot_info_page():
    '''Cтраница с информацией о параметрах бота для отладки'''
    data = [
        '<h1>Welcome to the Datatron Telegram Bot Webhook page</h1>',
        bot_info_str(True),
        webhook_info_str(True)
    ]

    wh_url = bot.get_webhook_info().url
    if wh_url:
        data.append('<a href={}>remove webhook</a>'.format(
            url_for('update_webhook', action='remove')))
    elif WEBHOOK_URL['DEFINED']:
        data.append('<a href={}>set default webhook</a>'.format(
            url_for('update_webhook', action='restore')))
    else:
        data.append('<i>no valid public url available for this page; '
                    'in order to use webhooks for this bot, '
                    'specify webhook params in config file</i>')
    content = '\n'.join('<p>{}</p>'.format(s) for s in (data))
    return content, 200


@app.route(WEBHOOK_URL['PATH'] + 'handlers/', methods=['GET'])
def update_webhook():
    action = request.args.get('action', '')
    if action == 'remove':
        bot.remove_webhook()
    elif action == 'restore' and WEBHOOK_URL['DEFINED']:
        bot.set_webhook(WEBHOOK_URL['BASE'] + WEBHOOK_URL['PATH'])
    else:
        abort(400)
    return redirect(url_for('bot_info_page'))


@app.route(WEBHOOK_URL['PATH'], methods=['POST'])
def webhook():
    """Обработчик запросов"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)
