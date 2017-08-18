#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Содержит сообщения для взаимодействия с пользователем
"""

from json import dumps

CMD_START_MSG = "Вас приветствует экспертная система Datatron!"

TELEGRAM_START_MSG = '''Я – экспертная система Datatron!

Со мной вы сможете быстро получать открытые финансовые данные. Расходы, доходы, дефицит, долг - не вопрос. Все это я знаю, и у меня есть данные как по России в целом, так и для любого ее региона.

*Особенности взаимодействия*
Datatron предоставляет данные по запросу на естественном языке в формате текстового или голосового сообщения.

*Текстовый режим*
Просто напишите собщение с интересующим вас вопросом.

*Голосовой режим*
Вопрос можно задать голосом, используя встроенную в Telegram запись аудио.

Если вы не знаете, что спросить, вы можете воспользоваться командой /idea. Подробное описание функций доступно по команде /help.

_Datatron – ваш личный эксперт в мире открытых финансовых данных!_'''

ABOUT_MSG = '''*Описание:*
Datatron - личный ассистент, предоставляющий доступ к открытым финансовым данным России и её субъектов по запросам на естественном языке.

*Разработчики:*
Студенты ФБМ и ФКН ВШЭ, а также ВМК МГУ, которые стараются изменить мир к лучшему.

*Обратная связь*
Для нас важно ваше мнение о работе Datatron. Вы можете оставить отзыв о боте, написав его через пробел после команды /fb, или нажав кнопку "Оценить".

*Дополнительно:*
Использует [Yandex SpeechKit Cloud](https://tech.yandex.ru/speechkit/cloud/).'''

ABOUT_KEYBOARD = dumps({
    'inline_keyboard': [
        [
            {'text': 'Оценить', 'url': 'https://telegram.me/storebot?start=datatron_bot'}
        ],
        [
            {'text': 'Ознакомительный ролик', 'callback_data': 'intro_video'}
        ]
    ]
})

HELP_MSG = '''*Список доступных команд*
/start - Начало работы
/help - Помощь
/idea - Вопросы, которые задавали другие пользователи
/fb - Оставить отзыв
/about - О проекте

*Начало работы с Datatron*
Для поиска финансовой информации достаточно просто сформулировать и отправить свой запрос, например:

```
Объем внешнего долга России в 2016 году
Доходы федерального бюджета в 17 году
Исполнение бюджета Москвы по налогу на прибыль```

Также Datatron понимает голосовые запросы – просто отправьте ему голосовое сообщение. Всё устроено точно так же, как и текстовое общение.
'''

RESPONSE_QUALITY = dumps({
    'inline_keyboard': [
        [
            {'text': '👍', 'callback_data': 'correct_response'},
            {'text': '😒', 'callback_data': 'incorrect_response'}
        ],
    ]
})

ERROR_CANNOT_UNDERSTAND_VOICE = 'Не удалось распознать текст сообщения😥 Попробуйте еще раз!'
ERROR_NULL_DATA_FOR_SUCH_REQUEST = 'К сожалению, этих данных в системе нет🤕'
ERROR_SERVER_DOES_NOT_RESPONSE = 'К сожалению, сейчас сервер не доступен😩 Попробуйте снова чуть позже!'
ERROR_NO_DOCS_FOUND = 'Datatron не нашел ответ на Ваш запрос :('

MSG_WE_WILL_FORM_DATA_AND_SEND_YOU = "Спасибо! Сейчас я сформирую ответ и отправлю его вам🙌"
MSG_NO_BUTTON_SUPPORT = 'Кнопочный режим более *не поддерживается*'
MSG_LEAVE_YOUR_FEEDBACK = 'Напишите после команды /fb ваш отзыв.\nНапример: `/fb Мне нравится, что...`'
MSG_WE_GOT_YOUR_FEEDBACK = 'Cпасибо! Ваш отзыв записан :)'
MSG_LOG_HISTORY_IS_EMPTY = 'Истории логов еще нет😔 Не растраивай Datatron, задай вопрос!'
MSG_USER_SAID_CORRECT_ANSWER = "Datatron приятно, что вы довольны ответом!"
MSG_USER_SAID_INCORRECT_ANSWER = 'Datatron извиняется и постарается стать лучше!'

# Constants for m2
ERROR_PARSING = 'Что-то пошло не так🙃 Проверьте ваш запрос на корректность'
ERROR_GENERAL = 'Что-то пошло не так🙃 Данные получить не удалось:('

# Список ключевых слов, которые служат триггером для ответа бота одной
# из фраз из кортежа HELLO_ANSWER
HELLO = ('хай', 'привет', 'здравствуйте', 'приветствую', 'прифки', 'дратути', 'hello')
HELLO_ANSWER = (
    'Привет! Начни работу со мной командой /search или сделай голосовой запрос',
    'Здравствуйте! Самое время ввести команду /search',
    'Приветствую!',
    'Здравствуйте! Пришли за финансовыми данными? Задайте мне вопрос!',
    'Доброго времени суток! С вами Datatron😊, и мы начинаем /search'
)

# Список ключевых слов, которые служат триггером для ответа бота одной
# из фраз из кортежа HOW_ARE_YOU_ANSWER
HOW_ARE_YOU = ('дела', 'поживаешь', 'жизнь')
HOW_ARE_YOU_ANSWER = (
    'У меня все отлично, спасибо :-)',
    'Все хорошо! Дела идут в гору',
    'Замечательно!',
    'Бывало и лучше! Без твоих запросов только и делаю, что прокрастинирую🙈',
    'Чудесно! Данные расходятся, как горячие пирожки! 😄'
)

# Маски для человекочитаемого фидбека по кубам
#
# Синтаксис: всё, что написано вне фигурных скобок, остаётся as is;
# Внутри фигурных скобок: {[?префикс?]код_измерения[*граммемы]?[постфикс]?};
# (значения в квадратных скобках -- опциональные)
#
# Код_измерения -- первое слово названия измерения, из которого берётся значение
# (например, "{раздел}" может обозначать значение измерения "Раздел и подраздел расходов")
# Если код измерения написан с прописной буквы, подставляемое значение тоже будет
# написано с прописной буквы; во всех прочих случаях будет сохраняться оригинальный регистр текста.
# Мере соответствует код "мера"; если мера равна "значение", она игнорируется.
# Кубу соответствует код "куб", но пока его использовать смысла нет, т.к. всё равно
# разным кубам соответствуют разные маски.
# Месяцу (если он есть) и году соответствует код "месгод" (нечто вида "март 2014")
#
# После кода через звёздочку идёт список граммем, соответствующих форме, в которую нужно
# поставить значение (между собой граммемы тоже разделены звёздочками).
# Например, "{раздел*gent*plur}" возьмёт значение нужного измерения и поставит его
# в родительный падеж множественного числа.
# (список обозначений для граммем: pymorphy2.readthedocs.io/en/latest/user/grammemes.html)
#
# Суффикс и постфикс (aka условный контекст) подставляются до/после подставленного значения,
# но только если значение найдено в полученном результате.
# Например "данные{? за ?год? год?}" вернёт "данные за <значение года> год", если во
# входных данных указан год, а если год не указан -- просто "данные".
# "Else" - условия, равно как и вложение сложных выражений в условный контекст,
# на данном этапе работы не поддерживаются.
#
# Пример маски:
#   {Показатели*nomn} {Территория*gent}{? на ?раздел*accs}{? (?код*nomn?)?}{? за ?год? год?}{?: ?мера*nomn}

CUBE_FEEDBACK_MASKS = {
    'CLDO01': '{Показатель*nomn}{?: ?мера*nomn}',
    'CLDO02': '{Показатели*nomn? ?}{территория*gent}{?: ?мера*nomn}',
    'CLMR02': '{Показатели*nomn}{? на ?месгод*accs}{?: ?мера*nomn}',
    'EXDO01': '{Показатели*nomn} бюджета {территория*gent}{? на ?раздел*accs} — оперативные данные{?: ?мера*nomn}',
    'EXYR03': '{Показатели*nomn}{? ?территория*gent}{? на ?раздел*accs}{? за ?месгод*accs}{?: ?мера*nomn}',
    'FSYR01': '{Показатели*nomn}{? ?территория*gent}{? за ?месгод*accs}{? через ?источники*accs}{?: ?мера*nomn}',
    'INDO01': '{Показатели*nomn}{? в бюджет ?территория*gent}{? (?группа*nomn?)?} — оперативные данные{?: ?мера*nomn}',
    'INYR03': '{Показатели*nomn}{? в бюджет ?территория*gent}{? (?группа*nomn?)?}{? за ?месгод*accs}{?: ?мера*nomn}'
}
