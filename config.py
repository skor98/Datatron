YANDEX_API_KEY = 'e05f5a12-8e05-4161-ad05-cf435a4e7d5b'


class ServerSettings:
    """Настройки для сервера"""
    # путь к БД, в которой храняться все данные по предметной области
    PATH_TO_KNOWLEDGEBASE = r'C:\Users\imon\Documents\Git\Datatron_2.0\Datatron\kb\knowledge_base.db'

    # путь к БД, в которой храняться данные о пользователях
    PATH_TO_USER_DB = r'C:\Users\imon\Documents\Git\Datatron_2.0\Datatron\db\users.db'

    # путь к файлу внутри Apache Solr для индексации файла с документами
    PATH_TO_SOLR_POST_JAR_FILE = r'"C:\local\solr-6.4.2\example\exampledocs\post.jar"'

    # путь к FFmpeg утилите, используемой для конвертации аудизаписи в различные форматы
    PATH_TO_FFMPEG = r'C:\Users\imon\Documents\Git\Datatron_2.0\Datatron\ffmpeg\ffmpeg.exe'

    # Путь к документам, картинкам и данным, связанным с ответами на вопросы по Министерству Финансов
    PATH_TO_MINFIN_ATTACHMENTS = r'C:\Users\imon\Documents\Git\Datatron_2.0\Datatron\data\minfin'

    # Токен, на котором работает текущее серверное приложение
    TELEGRAM_API_TOKEN = '231161869:AAFpafehgQl9V-5f6-1KvwjPkzhbgdqDflU'  # OpenFinData

    # Токен, на который нужно будет перенести решение, как только все будет готово
    TELEGRAM_API_TOKEN_FINAL = '242536845:AAELC6ay-SVnaw0nIZHCZpsqw_KN8yiaD1U'  # Datatron

    # Ядро в Apache Solr, в котором храняться все текущие документы
    SOLR_MAIN_CORE = 'kb_3c'

    # Ядро в Apache Solr, в котором раньше хранились Минфин-документы,
    # которые теперь лежат в одном ядре (kb_3c) с остальными
    SOLR_MINFIN_CORE = 'new_minfin'

    # ID Димы Е., Димы В., Маши и Лёши которым приходит уведомление при запуске системы
    ADMIN_TELEGRAM_ID = (65305591, 164241807, 139653713, 441850514)

    # Хост, на котором запущен Solr
    SOLR_HOST = 'localhost'

    # Хост на котором работает Bottle приложение из ui_web.py
    HOST = '0.0.0.0'


class DimaSettings:
    """Настройки для работы на локальном компьютере Димы Е."""

    PATH_TO_KNOWLEDGEBASE = r'C:\Users\User\PycharmProjects\Datatron\kb\knowledge_base.db'
    PATH_TO_USER_DB = r'C:\Users\User\PycharmProjects\Datatron\db\users.db'
    PATH_TO_SOLR_POST_JAR_FILE = r'"C:\Users\User\Desktop\solr\solr-6.3.0\solr-6.3.0\example\exampledocs\post.jar"'
    PATH_TO_FFMPEG = r'C:\Users\User\PycharmProjects\Datatron\ffmpeg\ffmpeg.exe'
    PATH_TO_MINFIN_ATTACHMENTS = r'C:\Users\User\PycharmProjects\Datatron\data\minfin'
    TELEGRAM_API_TOKEN = '371109250:AAE_0U6v5MKNcNSCZBmzIXVFIM8FPNCPqPc'  # DimaTestBot
    SOLR_MAIN_CORE = 'kb_3c'
    SOLR_MINFIN_CORE = 'minfin'
    ADMIN_TELEGRAM_ID = (65305591,)
    SOLR_HOST = 'localhost'
    HOST = 'localhost'


class MashaSettings:
    """Настройки для работы на локальном компьютере Маши"""

    PATH_TO_KNOWLEDGEBASE = r'C:\Users\The Cat Trex\PycharmProjects\Datatron\kb\knowledge_base.db'
    PATH_TO_USER_DB = r'C:\Users\The Cat Trex\PycharmProjects\Datatron\db\users.db'
    PATH_TO_SOLR_POST_JAR_FILE = r'C:\Users\The Cat Trex\Desktop\solr\solr-6.3.0\solr-6.3.0\example\exampledocs\post.jar"'
    PATH_TO_FFMPEG = r'C:\Users\The Cat Trex\PycharmProjects\Datatron\ffmpeg\ffmpeg.exe'
    PATH_TO_MINFIN_ATTACHMENTS = r'C:\Users\The Cat Trex\PycharmProjects\Datatron\data\minfin'
    TELEGRAM_API_TOKEN = '417763822:AAHltJOUDJyI0amublz1WHgctzL7zkQR_Vo'  # MaryDatatronTestBot
    SOLR_MAIN_CORE = 'kb_3c'
    SOLR_MINFIN_CORE = 'minfin'
    ADMIN_TELEGRAM_ID = (164241807,)
    SOLR_HOST = 'localhost'
    HOST = 'localhost'


class AlexSettings:
    """Настройки для работы на локальной виртуальной машине Лёши"""

    PATH_TO_KNOWLEDGEBASE = r'C:\Users\RealPC\Desktop\Datatron\kb\knowledge_base.db'
    PATH_TO_USER_DB = r'C:\Users\RealPC\Desktop\Datatron\db\users.db'
    PATH_TO_SOLR_POST_JAR_FILE = r'"C:\Users\RealPC\Desktop\solr-6.6.0\example\exampledocs\post.jar"'
    PATH_TO_FFMPEG = r'"C:\Users\RealPC\Desktop\ffmpeg\ffmpeg.exe"'
    PATH_TO_MINFIN_ATTACHMENTS = r'C:\Users\RealPC\Desktop\Datatron\data\minfin'
    TELEGRAM_API_TOKEN = '385055797:AAElq4hXYZPkubP42Aj5Jk4w6wa6Qd5aHe8'  # AlexDatatronBot
    SOLR_MAIN_CORE = 'kb_3c'
    SOLR_MINFIN_CORE = 'minfin'
    ADMIN_TELEGRAM_ID = (441850514,)
    SOLR_HOST = '192.168.1.8'
    HOST = '0.0.0.0'


ss, ds, ms = ServerSettings, DimaSettings, MashaSettings
alex_settings = AlexSettings
SETTINGS = ds  # Подставь нужную переменную для работы системы
