from kb.db_filling import KnowledgeBaseSupport
from kb.docs_generating import DocsGeneration
from kb.minfin_docs_generation import set_up_minfin_core
from collections import Counter
from config import SETTINGS


def set_up_db(overwrite=True):
    """Создание и заполнение БД

    :param overwrite: если True, то БД будет создана полностью заново, если False - то будет дополнена
    :return:
    """
    # 1. Создание и заполнение БД
    kb_path = SETTINGS.PATH_TO_KNOWLEDGEBASE
    db_file = kb_path.split('\\')[Counter(kb_path)['\\']]
    # kbs = KnowledgeBaseSupport('CLMR02.csv', db_file)
    kbs = KnowledgeBaseSupport('knowledge_base.db.sql', db_file)
    kbs.set_up_db(overwrite=overwrite)


def set_up_solr_cube_data(index_way='curl'):
    """Создание и индексирование документов по кубам

    :param index_way: если curl, то индексирование документов в Solr Apache будет черз сURL,
    если jar_file, то средствами java скрипта от Solr
    :return:
    """
    # 2. Генерация и индексация документов
    dga = DocsGeneration(core=SETTINGS.SOLR_MAIN_CORE)
    dga.clear_index()  # Удаление документов из ядра
    dga.generate_docs()  # Генерация документов
    if index_way == 'curl':
        dga.index_created_documents_via_curl()
    elif index_way == 'jar_file':
        dga.index_created_documents_via_cmd(SETTINGS.PATH_TO_SOLR_POST_JAR_FILE)


def set_up_all_together():
    """Настройка БД, документов по кубам и минфину одним методом.
    Если какой-то функционал не нужен, то он комметируется перед выполнением"""
    # set_up_db()
    set_up_solr_cube_data('jar_file')
    set_up_minfin_core('jar_file', clear=False, core=SETTINGS.SOLR_MAIN_CORE)


set_up_all_together()

# Команда переключение в нужну дерикторию и запуска Solr для Димы
# cd C:\Users\User\Desktop\solr\solr-6.3.0\solr-6.3.0\bin
# solr.cmd start -f
