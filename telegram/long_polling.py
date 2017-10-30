#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Long Polling для бота в телеграме
"""

from time import sleep

from constants import (TELEGRAM_CRITICAL_ADMIN_MSG,
                       TELEGRAM_STARTUP_ADMIN_MSG,
                       TELEGRAM_STOP_ADMIN_MSG)
from telegram.bot_main import bot, admin_notify


def bot_polling():
    old_webhook = bot.get_webhook_info().url
    if old_webhook:
        bot.remove_webhook()
    admin_notify(TELEGRAM_STARTUP_ADMIN_MSG, crit=False)
    try:
        bot.polling(none_stop=True)
    except Exception as ex:
        admin_notify(TELEGRAM_CRITICAL_ADMIN_MSG.format(ex=repr(ex)),
                     crit=True)
        raise ex
    finally:
        admin_notify(TELEGRAM_STOP_ADMIN_MSG, crit=False)
        if old_webhook:
            sleep(1)
            bot.set_webhook(old_webhook)


if __name__ == '__main__':
    bot_polling()
