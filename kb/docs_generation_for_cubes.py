#!/usr/bin/python
# -*- coding: utf-8 -*-


import json
import subprocess
import datetime
import pycurl
import requests

from os import path, remove
from peewee import fn

import kb.kb_db_creation as dbc
from kb.kb_support_library import get_cube_dimensions
from kb.kb_support_library import get_default_cube_measure
from kb.kb_support_library import get_connected_value_to_given_value
from kb.kb_support_library import get_measure_lem_key_words
from config import SETTINGS


class CubeDocsGeneration:
    """
    Класс для работы с данными по кубам. В нем происходит создание
    документов,
    """

    def __init__(self):
        self.file_name = path.join('kb', 'cube_data_for_indexing.json')
        self.core = SETTINGS.SOLR_MAIN_CORE

    def generate_docs(self):
        """
        Создание полного перечня документов по кубам. Их структуру можно посмотреть тут:
        http://redmine.epbs.krista.ru/redmine/projects/budgetapps/wiki/RequestManagerThread

        И запись этих документов в файл для последующей индексации в Apache Solr
        """

        data = (
            CubeDocsGeneration._create_values() +
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
        try:
            remove(self.file_name)
        except FileNotFoundError:
            pass

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
    def _create_values():
        """
        Создание на основе БД (knowledge_base.db) документов со значениями
        измерений.
        """

        # Отдельное создание ГОДОВ, так как структура
        # документов для этих измерений отличается
        year_values = CubeDocsGeneration._create_year_values()

        # Отдельное создание ТЕРРИТОРИЙ, так как структура
        # них также отличает от других измерений
        territory_values = CubeDocsGeneration._create_territory_values()

        # TODO: рефакторинг
        # Выбор всех остальных значений измерений и формирование документа
        other_values = []
        for cube in dbc.Cube.select():
            for dim_cub in dbc.CubeDimension.select().where(dbc.CubeDimension.cube_id == cube.id):
                for dimension in dbc.Dimension.select().where(dbc.Dimension.id == dim_cub.dimension_id):
                    if dimension.label not in ('Years', 'Territories'):
                        for dimension_value in dbc.DimensionValue.select().where(
                                        dbc.DimensionValue.dimension_id == dimension.id
                        ):
                            for value in dbc.Value.select().where(dbc.Value.id == dimension_value.value_id):
                                verbal = value.lem_index_value
                                if value.lem_synonyms:
                                    verbal += ' {}'.format(value.lem_synonyms)
                                other_values.append({
                                    'type': 'dimension',
                                    'cube': cube.name,
                                    'dimension': dimension.label,
                                    'verbal': verbal,
                                    'cube_value': value.cube_value,
                                    'hierarchy_level': value.hierarchy_level,
                                    'connected_value': get_connected_value_to_given_value(value.cube_value)
                                })

        return year_values + territory_values + other_values

    @staticmethod
    def _create_year_values():
        """
        Создание документов типа ГОД.
        У Кристы есть данные только с 2007 года
        """

        year_values = []
        current_year = datetime.datetime.now().year

        # 4-цифренные года: 2007 - current_year
        years = [str(i) for i in range(2007, current_year + 1)]

        # 1-2-цифренные года: 7 - 17
        years.extend([str(i) for i in range(7, current_year - 1999)])

        # создание документов нужной структуры
        for year in years:
            year_values.append(
                {
                    'type': 'year_dimension',
                    'dimension': 'Years',
                    'cube_value': year
                }
            )

        return year_values

    @staticmethod
    def _create_territory_values():
        """Создание на основе БД документов типа ТЕРРИТОРИЯ"""

        territory_values = []

        # Все уникальные территории
        values = (dbc.Value
                  .select(fn.Distinct(dbc.Value.lem_index_value))
                  .join(dbc.DimensionValue)
                  .join(dbc.Dimension)
                  .where(dbc.Dimension.label == 'Territories'))

        # Создание документа определенной структуры
        for item in values:
            verbal = item.lem_index_value

            # добавление синонимов, если есть
            if item.lem_synonyms:
                verbal += ' ' + item.lem_synonyms

            # создание исходной структур
            d = {
                'type': 'territory_dimension',
                'dimension': 'Territories',
                'verbal': verbal
            }

            used_cube_with_territory = None

            # добавление значений по кубам
            for v in dbc.Value.select().where(dbc.Value.lem_index_value == item.lem_index_value):
                # находится куб, соответствующий этому значению
                cube = (dbc.Cube
                        .select()
                        .join(dbc.CubeDimension)
                        .join(dbc.Dimension)
                        .join(dbc.DimensionValue)
                        .where(dbc.DimensionValue.value_id == v.id))[0]

                # добавление в словарь новой пары
                d[cube.name] = v.cube_value

                if not used_cube_with_territory:
                    used_cube_with_territory = cube.name

            d['connected_value'] = get_connected_value_to_given_value(
                d[used_cube_with_territory]
            )

            territory_values.append(d)

        return territory_values

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
                'caption': cube.caption,
                'description': cube_description,
                'dimensions': get_cube_dimensions(cube.name),
                'default_measure': get_default_cube_measure(cube.name)
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
                 .where(dbc.Measure.id.not_in(default_measures_ids))
                 )

        # Создание нужной структуры документов
        for item in query:
            measures.append({
                'type': 'measure',
                'cube': item.cube.name,
                'verbal': item.measure.lem_index_value,
                'lem_key_words': get_measure_lem_key_words(
                    item.measure.cube_value,
                    item.cube.name
                ),
                'cube_value': item.measure.cube_value
            })

        return measures

    def _write_to_file(self, docs):
        """
        Преобразование сгенерированных документов по кубам в JSON и
        запись файл cube_data_for_indexing.json для последующей
        индексации в Apache Solr
        """

        with open(self.file_name, 'a', encoding='utf-8') as file:
            file.write(json.dumps(docs, ensure_ascii=False))

    def index_created_documents_via_curl(self):
        """
        Отправа JSON файла с документами по кубам
        на индексацию в Apache Solr через cURL
        """

        c = pycurl.Curl()
        curl_addr = (
            'http://' +
            SETTINGS.SOLR_HOST +
            ':8983/solr/{}/update?commit=true'
        )
        c.setopt(c.URL, curl_addr.format(self.core))
        c.setopt(c.HTTPPOST,
                 [
                     ('fileupload',
                      (c.FORM_FILE, self.file_name,
                       c.FORM_CONTENTTYPE, 'application/json')
                      ),
                 ])
        c.perform()
        print('Документы для кубов проиндексированы через CURL')

    def index_created_documents_via_jar_file(self):
        """
        Отправа JSON файла с документами по кубам
        на индексацию в Apache Solr через файл
        встроенный инструмент от Apache Solr – файл post.jar
        из папки /example/exampledocs
        """

        path_to_json_data_file = self.file_name
        command = r'java -Dauto -Dc={} -Dfiletypes=json -jar {} {}'.format(
            self.core,
            SETTINGS.PATH_TO_SOLR_POST_JAR_FILE,
            path_to_json_data_file
        )
        subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).wait()
        print('Документы для кубов проиндексированы через JAR файл')
