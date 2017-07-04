#!/usr/bin/python
# -*- coding: utf-8 -*-

from os import getcwd, remove
import json
import subprocess
import datetime

import pycurl
import requests

from kb.kb_db_creation import *  # ToDo Убрать звёздочку
from config import SETTINGS


class DocsGeneration:
    def __init__(self, core):
        self.file_name = r'kb\data_for_indexing.json'
        self.core = core

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
            remove('{}\\{}'.format(getcwd(), self.file_name))
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
                      (c.FORM_FILE, getcwd() + '\\{}'.format(self.file_name),
                       c.FORM_CONTENTTYPE, 'application/json')
                      ),
                 ])
        c.perform()
        print('Документы для кубов проиндексированы через CURL')

    def index_created_documents_via_cmd(self, path_to_post_jar_file):
        r"""Индексация средствами post.jar из папки \example\exampledocs"""

        path_to_json_data_file = '{}\\{}'.format(getcwd(), self.file_name)
        command = r'java -Dauto -Dc={} -Dfiletypes=json -jar {} {}'.format(
            self.core,
            path_to_post_jar_file,
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
        for cube in Cube.select():
            for dim_cub in CubeDimension.select().where(CubeDimension.cube_id == cube.id):
                for dimension in Dimension.select().where(Dimension.id == dim_cub.dimension_id):
                    if dimension.label not in ('Years', 'Territories'):
                        for dimension_value in DimensionValue.select().where(
                                        DimensionValue.dimension_id == dimension.id
                        ):
                            for value in Value.select().where(Value.id == dimension_value.value_id):
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
            year_values.insert(0, {'type': 'year_dimension', 'fvalue': year_values.pop()})

        return year_values

    @staticmethod
    def _create_territory_values():
        # TODO: рефакторинг
        # Отдельно обрабатываются территории, так как они тоже имеют особую структуру документа
        territory_values = []
        dimension = Dimension.get(Dimension.label == 'Territories')
        for dimension_value in DimensionValue.select().where(DimensionValue.dimension_id == dimension.id):
            for value in Value.select().where(Value.id == dimension_value.value_id):
                index_value = value.lem_index_value
                if value.lem_synonyms:
                    index_value += ' {}'.format(value.lem_synonyms)
                territory_values.append(index_value)

        td = {}  # ToDo: Что это такое?

        for item in territory_values:
            td[item] = []
            for value in Value.select().where(Value.lem_index_value == item):
                td[item].append({'id': value.id, 'fvalue': value.cube_value})

        for key, value in td.items():
            for item in value:
                dimension_value_dimension_id = DimensionValue.get(
                    DimensionValue.value_id == item['id']
                ).dimension_id
                cube_id = CubeDimension.get(CubeDimension.dimension_id == dimension_value_dimension_id).cube_id
                item['cube'] = Cube.get(Cube.id == cube_id).name
                item.pop('id', None)

        territory_values.clear()

        for key, value in td.items():
            d = {'type': 'territory_dimension', 'verbal': key}
            for item in value:
                d[item['cube']] = item['fvalue']
            territory_values.append(d)

        return territory_values

    @staticmethod
    def _create_cubes():
        """Создание документов по кубам"""

        cubes = []
        for cube in Cube.select():
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
        for cube in Cube.select():
            default_measures_ids.append(cube.default_measure_id)

        # Индексация только тех мер, которые не относятся к значениям по умолчанию
        for measure in Measure.select():
            if measure.id not in default_measures_ids:
                for cube_measure in CubeMeasure.select().where(CubeMeasure.measure_id == measure.id):
                    for cube in Cube.select().where(Cube.id == cube_measure.cube_id):
                        measures.append({
                            'type': 'measure',
                            'cube': cube.name,
                            'verbal': measure.lem_index_value,
                            'formal': measure.cube_value
                        })
        return measures
