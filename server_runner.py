#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сервер для API и телеграма
"""

# pylint: disable=invalid-name

from werkzeug.serving import run_simple
from werkzeug.wsgi import DispatcherMiddleware

from ui_web_api import app as web_api_app
from ui_telegram import app as telegram_app

from config import SETTINGS, SETTINGS_PATH

if telegram_app is None:
    server_app = web_api_app
elif web_api_app is None:
    server_app = telegram_app
else:
    server_app = DispatcherMiddleware(web_api_app, {'/telebot': telegram_app})


def run_server():
    """Запуск приложения"""

    run_simple(
        hostname=SETTINGS.WEB_SERVER.HOST,
        port=SETTINGS.WEB_SERVER.RUN_PORT,
        application=server_app,
        use_reloader=True,
        extra_files=SETTINGS_PATH,
        threaded=True,
    )


if __name__ == '__main__':
    run_server()
