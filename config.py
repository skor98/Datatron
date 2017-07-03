YANDEX_API_KEY = 'e05f5a12-8e05-4161-ad05-cf435a4e7d5b'


class ServerSettings:
    PATH_TO_KNOWLEDGEBASE = r'C:\Users\imon\Documents\Git\Datatron_2.0\Datatron\kb\knowledge_base.db'
    PATH_TO_USER_DB = r'C:\Users\imon\Documents\Git\Datatron_2.0\Datatron\db\users.db'
    PATH_TO_SOLR_POST_JAR_FILE = r'"C:\local\solr-6.4.2\example\exampledocs\post.jar"'
    PATH_TO_FFMPEG = r'C:\Users\imon\Documents\Git\Datatron_2.0\Datatron\ffmpeg\ffmpeg.exe'
    PATH_TO_MINFIN_ATTACHMENTS = r'C:\Users\imon\Documents\Git\Datatron_2.0\Datatron\data\minfin'
    TELEGRAM_API_TOKEN = '231161869:AAFpafehgQl9V-5f6-1KvwjPkzhbgdqDflU'  # OpenFinData
    TELEGRAM_API_TOKEN_FINAL = '242536845:AAELC6ay-SVnaw0nIZHCZpsqw_KN8yiaD1U'  # Datatron
    SOLR_MAIN_CORE = 'kb_3c'
    SOLR_MINFIN_CORE = 'new_minfin'
    ADMIN_TELEGRAM_ID = (65305591, 164241807, 139653713)
    HOST = '0.0.0.0'


class DimaSettings:
    PATH_TO_KNOWLEDGEBASE = r'C:\Users\User\PycharmProjects\Datatron\kb\knowledge_base.db'
    PATH_TO_USER_DB = r'C:\Users\User\PycharmProjects\Datatron\db\users.db'
    PATH_TO_SOLR_POST_JAR_FILE = r'"C:\Users\User\Desktop\solr\solr-6.3.0\solr-6.3.0\example\exampledocs\post.jar"'
    PATH_TO_FFMPEG = r'C:\Users\User\PycharmProjects\Datatron\ffmpeg\ffmpeg.exe'
    PATH_TO_MINFIN_ATTACHMENTS = r'C:\Users\User\PycharmProjects\Datatron\data\minfin'
    TELEGRAM_API_TOKEN = '371109250:AAE_0U6v5MKNcNSCZBmzIXVFIM8FPNCPqPc'  # Dimatest_Bot
    SOLR_MAIN_CORE = 'kb_3c'
    SOLR_MINFIN_CORE = 'minfin'
    ADMIN_TELEGRAM_ID = (65305591,)
    HOST = 'localhost'


class MashaSettings:
    PATH_TO_KNOWLEDGEBASE = r'C:\Users\The Cat Trex\PycharmProjects\Datatron\kb\knowledge_base.db'
    PATH_TO_USER_DB = r'C:\Users\The Cat Trex\PycharmProjects\Datatron\db\users.db'
    PATH_TO_SOLR_POST_JAR_FILE = r'C:\Users\The Cat Trex\Desktop\solr\solr-6.3.0\solr-6.3.0\example\exampledocs\post.jar"'
    PATH_TO_FFMPEG = r'C:\Users\The Cat Trex\PycharmProjects\Datatron\ffmpeg\ffmpeg.exe'
    PATH_TO_MINFIN_ATTACHMENTS = r'C:\Users\The Cat Trex\PycharmProjects\Datatron\data\minfin'
    TELEGRAM_API_TOKEN = '417763822:AAHltJOUDJyI0amublz1WHgctzL7zkQR_Vo'  # MaryDatatronTestBot
    SOLR_MAIN_CORE = 'kb_3c'
    SOLR_MINFIN_CORE = 'minfin'
    ADMIN_TELEGRAM_ID = (164241807,)
    HOST = 'localhost'


ss, ds, ms = ServerSettings, DimaSettings, MashaSettings
SETTINGS = ms

