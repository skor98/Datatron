# Краткое интро в архитектуру и best practics

## Архитектура кратко
ToDo: написать что-то сюда

## Стратегия логгирования
Пользуемся стандартным модулем `logging`. Предварительно его нужно
иниициализировать. Для этого достаточно импортировать `logs_helper.py`.

Вывод на консоль и в файл **различается**!

Есть несколько уровней обработки ошибок:

| Уровень  | Числом  | Исползование       |
|----------|:-------:|--------------------|
| CRITICAL |    50   | logging.critical() |
| ERROR    |    40   | logging.error()    |
| WARNING  |    30   | logging.warning()  |
| INFO     |    20   | logging.info()     |
| DEBUG    |    10   | logging.debug()    |

Каждый последующий включает в себя предыдущие, но не наоборот. Уровень
настраивается по ключу `log_level` в файле `settings.json`.

Желательно писать в лог максимально много, но соотвествующим уровнем. Для
минимизации лишних вычислений исползуем это:

```
if logging.getLogger().isEnabledFor(logging.DEBUG):
    logging.debug(very_expensive_func())
```

Для некоторых критичных функций полезно логгировать время, это можно сделать
с помощью декоратора `time_with_message`:

```
from logs_helper import time_with_message

@time_with_message("expensive_func", "info", 5)
def expensive_func(a, b):
    return a * b
```

Параметры:

1. Сообщение для логгирования. Лучше всего выбрать то, что потом будет удобно
искать в логе
2. Уровень вывода сообщения: `debug` или `info`.
3. Время в секундах, которое считается слишком большим. Если оно будет превышено,
то будет записан warning в лог

### Как использовать `grep`?

1. Получение логов с определённым уровнем: `grep -iw "WARNING" logs.log`
2. Получение контекста: `-B2` добавляет 2 строки ДО, `-C2` добавляет 2 строки ДО
и ПОСЛЕ: `grep -iw -B2 "WARNING" logs.log`
3. Получение времени по функции`grep  "TextQuery API Get\" заняло"  logs.log`
или более кратко: `grep -o "TextQuery API Get\" заняло [[:digit:]:.]*" logs.log`
4. Получение логов по запросу:
`grep  "Query_ID: c02d14c6dbaa420a8cf040617021adc7" logs.log`

## Стратегия обработки ошибок
Если вы поймали исключение, то оно логгируется с помощью `logging.exception(e)`.
Если исключение возникает при разработке или при самом старте системы, то лучше
всего упасть сразу, через `sys.exit(0)`.
Если исключение возникло при реальной работе, то падать нельзя, но можно
его залоггировать.

## Стратегия использования настроек
Если вам необходимо подставить какую-то константу, но у вас есть сомнения,
что она неоптимальна или неокончательно, то её необходимо сделать константой `LIKE_THIS`.
Лучше всего, когда её область видимости: если используется только в одной функции,
то пусть будет в ней, при условии, что в других функциях это значение не нужно.

Если вам кажется, что это константа необходима в нескольких файлах, то опишите её в `config.py`.

Если такая константа очень похожа на текстовое сообщение, то её стоит разместить в
файле `constants.py`.

### Структура файла настроек
Настройки компьютера -- это json файл, который содержит набор непосредственно
самих настроек по ключу `settings` и имя текущего ключа с настройками по ключу
`cur_settings`.

По ключу `log_level` устанавливается подробность логгирования. Доступны строки
DEBUG, `INFO`, `WARNING`, `ERROR` и числовые значения от
0 (всё писать) до 50 (только критическое).

#### Описание значений каждой из настроек
1. `PATH_TO_KNOWLEDGEBASE` путь к БД, в которой храняться все данные по
 предметной области
2. `PATH_TO_USER_DB` путь к БД, в которой храняться данные о пользователях
3. `PATH_TO_SOLR_POST_JAR_FILE` путь к файлу внутри Apache Solr для индексации
 файла с документами
4. `PATH_TO_FFMPEG` путь к FFmpeg утилите, используемой для конвертации 
аудизаписи в различные форматы
5. `PATH_TO_MINFIN_ATTACHMENTS` путь к документам, картинкам и данным, 
связанным с ответами на вопросы по Министерству Финансов
6. `TELEGRAM_API_TOKEN` токен, на котором работает текущее серверное приложение
7. `TELEGRAM_API_TOKEN_FINAL` токен, на который нужно будет перенести решение,
 как только все будет готово
8. `SOLR_MAIN_CORE` ядро в Apache Solr, в котором храняться все текущие документы
9. `ADMIN_TELEGRAM_ID` ID людей, которым приходит уведомление при старте
10. `SOLR_HOST` хост, на котором запущен Solr
11. `HOST` хост на котором работает Bottle приложение из `ui_web.py`

## API
Расположен в `ui_api.py`. Порт на котором будет работать, задаётся через API_PORT
из `config.py`. 

Для примеров будет удобно использовать `httpie` (установка: `pip install httpie`)

* `GET v1/minfin_docs` запрос без параметров, возвращает массив со словарями по
каждому из вопросов: `[{"id":"5.3", "question":"..."},...]`. Пример:
`http get http://127.0.0.1:5005/v1/minfin_docs`
* `GET v1/text` с параметрами `apikey` и `query`. Возвращает стандартное JSON
представление ответа. Пример:
`http get http://127.0.0.1:5005/v1/text apikey=API_KEY query=Какой госдолг РФ?`
* `POST v1/voice` с параметрами `apikey` и `file` Пример:
`http -f post http://127.0.0.1:5005/v1/voice apikey=API_KEY file@file_name`

## Кому писать в случае вопросов
| Нужная часть          | Имя             | VK                 | telegram      |
|-----------------------|-----------------|--------------------|---------------|
| Бэкенд, автоматизация, MachineLearning | Алексей Лобанов | [Алексей Лобанов](vk.com/lobanovat23) | [@hippo23](https://t.me/hippo23), но лучше вк |
| Бэкенд, лингвистика | Глеб Николаев | [Larousse Nikolaev](https://vk.com/sprakvetenskap) | [@craboo](https://t.me/craboo) |
| Бэкенд | Дмитрий Елисеев | [Дмитрий Елисеев](https://vk.com/dimaquime) | [@dimaquime](https://t.me/dimaquime) |
