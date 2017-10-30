"""
Обратная совместимость
"""

from telegram.long_polling import bot_polling
from config import SETTINGS

if not SETTINGS.TELEGRAM.ENABLE_WEBHOOK:
    bot_polling()
