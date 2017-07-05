import kb.kb_db_creation as dbc
from kb.kb_support_library import create_automative_cube_description
from text_preprocessing import TextPreprocessing
from os import remove, path
import json

sep1 = ';'


class KnowledgeBaseSupport:
    def __init__(self, data_source_file, db_file):
        self.data_source_file = data_source_file
        self.db_file = db_file

    def set_up_db(self, overwrite=False):
        """Метод для настройки извне"""

        self._create_db(overwrite=overwrite)

        # Если заполнение БД должно идти из SQL скрипта (в 95% случаев)
        if self.data_source_file.endswith('.sql'):
            # Указания пути к sql файлу
            data_source_file_path = path.join('kb', self.data_source_file)

            # Чтение данных из файла
            with open(data_source_file_path, 'r', encoding="utf-8") as file:
                inserts = file.read().split(';')[1:-2]

            # Построчное исполнение команд
            for i in inserts:
                dbc.database.execute_sql(i)
        else:
            # Если же оно должно идти из метаданных полученных с серверов Кристы
            # Что очень редко, так как обновление БД на основе этих данных удалит ручные дополнения
            data_set_list = KnowledgeBaseSupport._read_data()

            if not isinstance(data_set_list, list):
                data_set_list = [data_set_list]

            KnowledgeBaseSupport._transfer_data_to_db(data_set_list)
            KnowledgeBaseSupport._create_cube_lem_description(data_set_list)

    def _create_db(self, overwrite=False):
        """Создание БД"""

        db_file_path = path.join('kb', self.db_file)
        if path.exists(db_file_path):
            if overwrite:
                remove(db_file_path)
            else:
                return None
            
        dbc.create_tables()

    @staticmethod
    def _read_data():
        """Перенос данных из текстового вида в определенную структуру класса DataSet"""

        data_set_list = []

        cube_metadata_file = path.join('kb', 'cubes_metadata.txt')

        with open(cube_metadata_file, 'r', encoding='utf-8') as file:
            data = file.read()
        cube_metadata = json.loads(data)

        tp = TextPreprocessing('Filling db')

        for item in cube_metadata:
            cube_data_set = DataSet()
            cube_data_set.cube = {'name': item['formal_name'],
                                  'lem_description': '-'}

            for dimension in item['dimensions']:
                cube_data_set.dimensions[dimension['name'].upper()] = None

            for measure in item['measures']:
                cube_data_set.measures.append({'full_value': measure['caption'],
                                               'lem_index_value': tp.normalization(measure['caption']),
                                               'cube_value': measure['name']})
            for element in item['cube_elements']:
                dim_name = element['hierarchyName'].upper()
                if not cube_data_set.dimensions[dim_name]:
                    cube_data_set.dimensions[dim_name] = []

                # игнорирование "не указанных", "не определенных" параметров
                normalized_elem = tp.normalization(element['caption'])
                if not [item for item in ('неуказанный', 'не определить') if item in normalized_elem]:
                    cube_data_set.dimensions[dim_name].append({'full_value': element['caption'],
                                                               'lem_index_value': normalized_elem,
                                                               'cube_value': element['name'],
                                                               'hierarchy_level': int(element['levelDepth'])})
            data_set_list.append(cube_data_set)

        return data_set_list

    @staticmethod
    def _transfer_data_to_db(data_set):
        """Перенос данных из определнной структуры в БД"""

        for item in data_set:
            # Занесение куба
            cube = dbc.Cube.create(**item.cube)

            # Занесение мер & связка мер с кубов
            for measure in item.measures:
                m = dbc.Measure.create(**measure)
                dbc.CubeMeasure.create(cube=cube, measure=m)

            # Занесение измерений & занесение значений & связка значений и измерений
            for dimension_name, dimension_values in item.dimensions.items():
                d = dbc.Dimension.create(label=dimension_name)
                dbc.CubeDimension.create(cube=cube, dimension=d)
                for dimension_value in dimension_values:
                    v = dbc.Value.create(**dimension_value)
                    dbc.DimensionValue.create(value=v, dimension=d)

    @staticmethod
    def _create_cube_lem_description(data_set):
        """Нормализованное описание куба на основе частотного распределения слов в значениях его измерений"""

        cubes = [item.cube['name'] for item in data_set]
        for cube in dbc.Cube.select().where(dbc.Cube.name in cubes):
            if cube.lem_description == '-':
                description = create_automative_cube_description(cube.name)
                dbc.Cube.update(lem_description=description).where(dbc.Cube.name == cube.name).execute()


class DataSet:
    def __init__(self):
        self.cube = None
        self.dimensions = {}
        self.measures = []
