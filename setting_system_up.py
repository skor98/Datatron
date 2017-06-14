from kb.db_filling import KnowledgeBaseSupport
from kb.docs_generating import DocsGeneration
from kb.minfin_docs_generation import set_up_minfin_core
from collections import Counter
from config import SETTINGS


def set_up_db(overwrite=True):
    # 1. Создание и заполнение БД
    kb_path = SETTINGS.PATH_TO_KNOWLEDGEBASE
    db_file = kb_path.split('\\')[Counter(kb_path)['\\']]
    # kbs = KnowledgeBaseSupport('CLMR02.csv', db_file)
    kbs = KnowledgeBaseSupport('knowledge_base.db.sql', db_file)
    kbs.set_up_db(overwrite=overwrite)


def set_up_solr_cube_data(index_way='curl'):
    # 2. Генерация и индексация документов
    dga = DocsGeneration(core=SETTINGS.SOLR_MAIN_CORE)
    # dga.create_core()
    dga.clear_index()  # Удаление документов из ядра
    dga.generate_docs()  # Генерация документов
    if index_way == 'curl':
        dga.index_created_documents_via_curl()  # Индексация документов
    elif index_way == 'jar_file':
        # Если видете ошибку: pycurl.error: (6, 'Could not resolve: localhost (Domain name not found)')
        # Используйте index_way='jar_file'
        dga.index_created_documents_via_cmd(SETTINGS.PATH_TO_SOLR_POST_JAR_FILE)  # Индексация документов


def set_up_solr_minfin_data(index_way='curl'):
    set_up_minfin_core(index_way=index_way)


# set_up_db()
# set_up_solr_cube_data()
set_up_minfin_core('jar_file')



# import os
# import subprocess
# def start_solr():
#     start_wd = os.getcwd()
#     os.chdir(SETTINGS.PATH_TO_SOLR_BIN_FOLDER)
#     subprocess.Popen('solr.cmd start -f'.split(), stdout=subprocess.PIPE)
#     os.chdir(start_wd)

# cd C:\Users\User\Desktop\solr\solr-6.3.0\solr-6.3.0\bin
# solr.cmd start -f
