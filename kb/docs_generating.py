#!/usr/bin/python
# -*- coding: utf-8 -*-

from os import path, remove
import json
import subprocess
import datetime

import pycurl
import requests

import kb.kb_db_creation as dbc
from config import SETTINGS


class DocsGeneration:
    def __init__(self):
        self.file_name = path.join('kb', 'data_for_indexing.json')
        self.core = SETTINGS.SOLR_MAIN_CORE

    def generate_docs(self):
        data = (
            DocsGeneration._create_values() +
            DocsGeneration._create_cubes() +
            DocsGeneration._create_measures()
        )

        self._write_to_file(data)

    def clear_index(self):
        """Очистка ядра"""

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
        """Создание ядра. Не всегда работает хорошо, лучше через командую строку в папке bin
        выполнить команду: solr create -c <core_name>"""

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

    def index_created_documents_via_curl(self):
        """Индексация через cURL"""

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
        r"""Индексация средствами post.jar из папки /example/exampledocs"""

        path_to_json_data_file = self.file_name
        command = r'java -Dauto -Dc={} -Dfiletypes=json -jar {} {}'.format(
            self.core,
            SETTINGS.PATH_TO_SOLR_POST_JAR_FILE,
            path_to_json_data_file
        )
        subprocess.Popen(command, shell=True, stdout=subprocess.PIPE).wait()
        print('Документы для кубов проиндексированы через JAR файл')

    def _write_to_file(self, docs):
        """Запись имеющейся структуры в файл для последующей индексации"""

        json_data = json.dumps(docs)
        with open(self.file_name, 'a', encoding='utf-8') as file:
            file.write(json_data)

    @staticmethod
    def _create_values():
        """Создание на основе БД документов для значений измерений"""

        year_values = DocsGeneration._create_year_values()
        territory_values = DocsGeneration._create_territory_values()

        # Здесь обрабатываются прочее значения измерений
        values = []
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
                                values.append({
                                    'type': 'dimension',
                                    'cube': cube.name,
                                    'name': dimension.label,
                                    'verbal': verbal,
                                    'fvalue': value.cube_value,
                                    'hierarchy_level': value.hierarchy_level})

        return year_values + territory_values + values

    @staticmethod
    def _create_year_values():
        # Отдельно обрабатываются года
        current_year = datetime.datetime.now().year

        # 4-цифренные года: 2007 - current_year
        year_values = [str(i) for i in range(2007, current_year + 1)]

        # 1-2-цифренные года: 7 - 17
        year_values.extend([str(i) for i in range(7, current_year - 1999)])
        for _ in range(len(year_values)):
            year_values.insert(0,
                               {'type': 'year_dimension',
                                'name': 'Years',
                                'fvalue': year_values.pop()})

        return year_values

    @staticmethod
    def _create_territory_values():
        # TODO: рефакторинг
        # Отдельно обрабатываются территории, так как они тоже имеют особую структуру документа
        territory_values = []

        already_used_territory = []

        # Все территории по одному разу
        values = (dbc.Value
                  .select(dbc.Value)
                  .join(dbc.DimensionValue)
                  .join(dbc.Dimension)
                  .where(dbc.Dimension.label == 'Territories'))

        for val in set(values):
            # вербальное значение
            verbal = val.lem_index_value
            if verbal not in already_used_territory:
                already_used_territory.append(verbal)

                # добавление синонимов, если есть
                if val.lem_synonyms:
                    verbal += ' ' + val.lem_synonyms

                # создание исходного словаря
                d = {'type': 'territory_dimension',
                     'name': 'Territories',
                     'verbal': verbal}

                # для всех значений, совпдающих вербально с val
                for v in dbc.Value.select().where(dbc.Value.lem_index_value == val.lem_index_value):
                    # находится куб, соответствующий этому значению
                    cube = (dbc.Cube
                            .select()
                            .join(dbc.CubeDimension)
                            .join(dbc.Dimension)
                            .join(dbc.DimensionValue)
                            .where(dbc.DimensionValue.value_id == v.id))[0]

                    # добавление в словарь новой пары
                    d[cube.name] = v.cube_value

                territory_values.append(d)

        return territory_values

    @staticmethod
    def _create_cubes():
        """Создание документов по кубам"""

        cubes = []
        for cube in dbc.Cube.select():
            cube_description = cube.auto_lem_description
            if cube.manual_lem_description:
                cube_description += ' {}'.format(cube.manual_lem_description)

            cubes.append({
                'type': 'cube',
                'cube': cube.name,
                'description': cube_description})
        return cubes

    @staticmethod
    def _create_measures():
        """Создание документов по мерам"""

        measures = []
        default_measures_ids = []

        # Сбор ID мер, указанных для кубов в БД по умолчанию
        for cube in dbc.Cube.select():
            default_measures_ids.append(cube.default_measure_id)

        # Индексация только тех мер, которые не относятся к значениям по умолчанию
        for measure in dbc.Measure.select():
            if measure.id not in default_measures_ids:
                for cube_measure in dbc.CubeMeasure.select().where(dbc.CubeMeasure.measure_id == measure.id):
                    for cube in dbc.Cube.select().where(dbc.Cube.id == cube_measure.cube_id):
                        measures.append({
                            'type': 'measure',
                            'cube': cube.name,
                            'verbal': measure.lem_index_value,
                            'formal': measure.cube_value
                        })
        return measures
