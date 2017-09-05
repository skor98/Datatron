#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Генерация документов по кубам
"""

import datetime
import json
from os import path
import subprocess
from uuid import uuid4

from peewee import fn
import requests

from config import SETTINGS, TECH_CUBE_DOCS_FILE
from model_manager import MODEL_CONFIG
import kb.kb_db_creation as dbc
from kb.kb_support_library import get_cube_dimensions
from kb.kb_support_library import get_default_cube_measure
from kb.kb_support_library import get_measure_lem_key_words
from kb.kb_support_library import get_with_member_to_given_member
from kb.kb_support_library import TOO_LONG_ELEMS, USELESS_BGLEVELS
import pycurl


class CubeDocsGeneration:
    """
    Класс для работы с данными по кубам. В нем происходит создание
    документов,
    """

    def __init__(self):
        self.file_name = path.join('kb', 'cube_data_for_indexing.json')
        self.tech_file_name = TECH_CUBE_DOCS_FILE
        self.search_file_name = path.join('kb', 'search_cube_data_for_indexing.json')
        self.core = SETTINGS.SOLR_MAIN_CORE

    def generate_docs(self):
        """
        Создание полного перечня документов по кубам. Их структуру можно посмотреть тут:
        http://redmine.epbs.krista.ru/redmine/projects/budgetapps/wiki/RequestManagerThread

        И запись этих документов в файл для последующей индексации в Apache Solr
        """

        data = (
            CubeDocsGeneration._create_dimension_members() +
            CubeDocsGeneration._create_cubes() +
            CubeDocsGeneration._create_measures()
        )

        self._write_to_file(data)

    def clear_index(self):
        """Очистка ядра в Apache Solr"""

        dlt_str = (
            'http://' +
            SETTINGS.SOLR_HOST +
            ':8983/solr/{}/update?stream.' +
            'body=%3Cdelete%3E%3Cquery%3E*:*%3C/' +
            'query%3E%3C/delete%3E&commit=true'
        )
        requests.get(dlt_str.format(self.core))

    def create_core(self):
        """
        Создание ядра. Лучше данный метод не использовать,
        не всегда работает хорошо. Самый простой способ создать
        ядро, это в папке bin Apache Solr выполнить команду:
        solr create -c <core_name>
        """

        status_str = 'http://localhost:8983/solr/admin/cores?action=STATUS&core={}&wt=json'
        solr_response = requests.get(status_str.format(self.core))
        solr_response = json.loads(solr_response.text)
        if solr_response['status'][self.core]:
            print('Ядро {} уже существует'.format(self.core))
        else:
            create_core_str = (
                'http://' +
                SETTINGS.SOLR_HOST +
                ':8983/solr/admin/cores?action=CREATE' +
                '&name={}&configSet=basic_configs'
            )
            solr_response = requests.get(create_core_str.format(self.core))
            if solr_response.status_code == 200:
                print('Ядро {} автоматически создано'.format(self.core))
            else:
                print('Что-то пошло не так: ошибка {}'.format(solr_response.status_code))

    @staticmethod
    def _create_dimension_members():
        """
        Создание на основе БД (knowledge_base.db) документов со значениями
        измерений.
        """

        # Отдельное создание ГОДОВ, так как структура
        # документов для этих измерений отличается
        year_values = CubeDocsGeneration._create_year_caption()

        # Отдельное создание ТЕРРИТОРИЙ, так как структура
        # них также отличает от других измерений
        territory_values = CubeDocsGeneration._create_territory_caption()

        # TODO: рефакторинг
        # Выбор всех остальных значений измерений и формирование документа
        other_values = []
        for cube in dbc.Cube.select():
            for dim_cub in dbc.CubeDimension.select().where(dbc.CubeDimension.cube_id == cube.id):
                for dimension in dbc.Dimension.select().where(dbc.Dimension.id == dim_cub.dimension_id):
                    if dimension.cube_value not in ('YEARS', 'TERRITORIES', 'KIF'):
                        for dimension_value in dbc.DimensionMember.select().where(
                                        dbc.DimensionMember.dimension_id == dimension.id
                        ):
                            for member in dbc.Member.select().where(dbc.Member.id == dimension_value.member_id):
                                if member.cube_value not in (TOO_LONG_ELEMS + USELESS_BGLEVELS):
                                    other_values.append({
                                        'type': 'dim_member',
                                        'cube': cube.name,
                                        'dimension': dimension.cube_value,
                                        'lem_member_caption': member.lem_caption,
                                        'lem_member_caption_len': len(member.lem_caption.split()),
                                        'lem_key_words': member.lem_synonyms,
                                        'member_caption': member.caption,
                                        'cube_value': member.cube_value,
                                        'hierarchy_level': member.hierarchy_level,
                                        'connected_value': get_with_member_to_given_member(member.id),
                                        'inner_id': uuid4().hex
                                    })

        return year_values + territory_values + other_values

    @staticmethod
    def _create_year_caption():
        """
        Создание документов типа ГОД.
        У Кристы есть данные только с 2007 года
        """

        year_values = []
        current_year = datetime.datetime.now().year

        # 4-цифренные года: 2007 - current_year
        years = [str(i) for i in range(2007, current_year + 1)]

        # создание документов нужной структуры
        for year in years:
            year_values.append(
                {
                    'type': 'year_dim_member',
                    'dimension': 'YEARS',
                    'cube_value': year,
                    'lem_member_caption': year,
                    'lem_member_caption_len': 1,
                    'member_caption': year
                }
            )

        return year_values

    @staticmethod
    def _create_territory_caption():
        """Создание на основе БД документов типа ТЕРРИТОРИЯ"""

        territory_caption = []

        # Все уникальные территории
        members = (dbc.Member
                   .select(fn.Distinct(dbc.Member.lem_caption),
                           dbc.Member.lem_synonyms)
                   .join(dbc.DimensionMember)
                   .join(dbc.Dimension)
                   .where(dbc.Dimension.cube_value == 'TERRITORIES'))

        # Создание документа определенной структуры
        for item in members:
            # создание исходной структур
            terr_doc = {
                'type': 'terr_dim_member',
                'dimension': 'TERRITORIES',
                'lem_member_caption': item.lem_caption,
                'lem_member_caption_len': len(item.lem_caption.split()),
                'lem_key_words': item.lem_synonyms,
                'member_caption': item.caption
            }

            some_terr_id = None

            # добавление значений по кубам
            for member in dbc.Member.select().where(dbc.Member.lem_caption == item.lem_caption):
                # находится куб, соответствующий этому значению
                cube = (dbc.Cube
                        .select()
                        .join(dbc.CubeDimension)
                        .join(dbc.Dimension)
                        .join(dbc.DimensionMember)
                        .where(dbc.DimensionMember.member_id == member.id)
                        )[0]

                # добавление в словарь новой пары
                terr_doc[cube.name] = member.cube_value

                if not some_terr_id:
                    some_terr_id = member.id

            terr_doc['connected_value'] = get_with_member_to_given_member(
                some_terr_id
            )

            territory_caption.append(terr_doc)

        return territory_caption

    @staticmethod
    def _create_cubes():
        """Создание документов по кубам"""

        cubes = []
        for cube in dbc.Cube.select():
            cube_description = cube.auto_lem_key_words

            # добавление к описанию куба ключевых слов от методологов
            if cube.key_words:
                cube_description += ' {}'.format(cube.lem_key_words)

            cubes.append({
                'type': 'cube',
                'cube': cube.name,
                'cube_caption': cube.caption,
                'lem_key_words': cube_description,
                'dimensions': get_cube_dimensions(cube.name),
                'default_measure': get_default_cube_measure(cube.name),
            })
        return cubes

    @staticmethod
    def _create_measures():
        """Создание документов по мерам"""

        measures = []
        default_measures_ids = []

        # Сбор ID мер, указанных для кубов в БД по умолчанию
        for cube in dbc.Cube.select():
            default_measures_ids.append(cube.default_measure_id)

        # Выбор мер, которые не относятся к значениям по умолчанию
        query = (dbc.CubeMeasure
                 .select(dbc.CubeMeasure, dbc.Cube, dbc.Measure)
                 .join(dbc.Measure)
                 .switch(dbc.CubeMeasure)
                 .join(dbc.Cube)
                 .where(dbc.Measure.cube_value != 'VALUE')
                 )

        # Создание нужной структуры документов
        for item in query:
            measures.append({
                'type': 'measure',
                'cube': item.cube.name,
                'lem_member_caption': item.measure.lem_caption,
                'member_caption': item.measure.caption,
                'lem_member_caption_len': len(item.measure.lem_caption.split()),
                'lem_key_words': get_measure_lem_key_words(
                    item.measure.cube_value,
                    item.cube.name
                ),
                'cube_value': item.measure.cube_value,
                'inner_id': uuid4().hex
            })

        return measures

    def _write_to_file(self, docs):
        """
        Преобразование сгенерированных документов по кубам в JSON и
        запись файл cube_data_for_indexing.json для последующей
        индексации в Apache Solr
        """

        if MODEL_CONFIG['enable_searching_and_tech_info_separation']:
            tech_keys = ('member_caption', 'inner_id')
            tech_docs = []

            for doc in docs:
                # документы по ключам из tech_keys
                if all(tk in doc.keys() for tk in tech_keys):
                    tech_docs.append(
                        {
                            tech_keys[0]: doc.get(tech_keys[0]),
                            tech_keys[1]: doc.get(tech_keys[1])
                        }
                    )
                # удаление из документа поля
                doc.pop(tech_keys[0], None)

            # запись данных в технический файл
            with open(self.tech_file_name, 'w', encoding='utf-8') as file:
                file.write(json.dumps(tech_docs, ensure_ascii=False, indent=4))

            # запись данных в индексируемый файл
            with open(self.search_file_name, 'w', encoding='utf-8') as file:
                file.write(json.dumps(docs, ensure_ascii=False, indent=4))
        else:
            with open(self.file_name, 'w', encoding='utf-8') as file:
                file.write(json.dumps(docs, ensure_ascii=False, indent=4))

    def index_created_documents_via_curl(self):
        """
        Отправа JSON файла с документами по кубам
        на индексацию в Apache Solr через cURL
        """

        indexed_file = self.file_name

        if MODEL_CONFIG['enable_searching_and_tech_info_separation']:
            indexed_file = self.search_file_name

        pycrl = pycurl.Curl()
        curl_addr = (
            'http://' +
            SETTINGS.SOLR_HOST +
            ':8983/solr/{}/update?commit=true'
        )
        pycrl.setopt(pycrl.URL, curl_addr.format(self.core))
        pycrl.setopt(pycrl.HTTPPOST,
                 [
                     ('fileupload',
                      (pycrl.FORM_FILE, indexed_file,
                       pycrl.FORM_CONTENTTYPE, 'application/json')
                      ),
                 ])
        pycrl.perform()
        print('Документ {} проиндексирован через CURL'.format(
            indexed_file
        ))

    def index_created_documents_via_jar_file(self):
        """
        Отправа JSON файла с документами по кубам
        на индексацию в Apache Solr через файл
        встроенный инструмент от Apache Solr – файл post.jar
        из папки /example/exampledocs
        """

        path_to_json_data_file = self.file_name

        if MODEL_CONFIG['enable_searching_and_tech_info_separation']:
            path_to_json_data_file = self.search_file_name

        command = r'java -Dauto -Dc={} -Dfiletypes=json -jar {} {}'.format(
            self.core,
            SETTINGS.PATH_TO_SOLR_POST_JAR_FILE,
            path_to_json_data_file
        )
        subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).wait()
        print('Документ {} проиндексирован через JAR файл'.format(
            path_to_json_data_file
        ))
