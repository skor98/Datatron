from kb.db_creation import Dimension_Value, Value, Cube, Cube_Value
import requests
import json


def is_dim_in_dim_set(dim, dim_set, dd):
    """Проверка наличия в конкретном наборе измерения dim_set такого измерение, название которого равно dim"""
    return bool(list(filter(lambda dim_id: dd[dim_id] == dim, iter(dim_set))))


def is_dim_in_cube(dim, dd):
    """Проверка наличия в среди всеъ измерений куба, измерения с названием dim"""
    return bool(list(filter(lambda dim_id: dd[dim_id] == dim, iter(dd))))


def filter_combinations(combs, dim_set, dd):
    """Фильтрация запросов на основе 1-4 пунктов от Алексея"""
    filtered_combs = list(combs)

    # уровень бюджета, если присутствует в измерения, должен быть указан (пункт 4)
    if is_dim_in_cube('BGLEVELS', dd) and not is_dim_in_dim_set('BGLEVELS', dim_set, dd):
        print('входная комбинация: {} входной массив: {}, сокращение: 100%'.format(dim_set, len(combs)))
        return []

    # год, если присутствует в измерения, должен быть указан (пункт 3)
    if is_dim_in_cube('YEARS', dd) and not is_dim_in_dim_set('YEARS', dim_set, dd):
        print('входная комбинация: {} входной массив: {}, сокращение: 100%'.format(dim_set, len(combs)))
        return []

    # без территории работают уместно использовать 5 уровней бюджета (пункт 1)
    if is_dim_in_dim_set('BGLEVELS', dim_set, dd) and not is_dim_in_dim_set('TERRITORIES', dim_set, dd):
        bg_level_values = set(['09-0', '09-1', '09-8', '09-9', '09-10'])

        for comb in combs:
            formal_values = [i[1] for i in comb]
            if not bg_level_values.intersection(set(formal_values)):
                filtered_combs.remove(comb)

    # с территорией определенные 5 уровней бюджета использовать неуместно (пункт 1)
    if is_dim_in_dim_set('BGLEVELS', dim_set, dd) and is_dim_in_dim_set('TERRITORIES', dim_set, dd):
        bg_level_values = set(['09-0', '09-1', '09-8', '09-9', '09-10'])

        for comb in combs:
            formal_values = [i[1] for i in comb]
            if bg_level_values.intersection(set(formal_values)):
                filtered_combs.remove(comb)

    # значение "все уровни" работает с показателем, если он равен "объем чистых кассовых доходов" (пункт 2)
    if is_dim_in_dim_set('BGLEVELS', dim_set, dd) and is_dim_in_dim_set('MARKS', dim_set, dd):
        bg_level_and_mark_value = set(['09-0', '02-2'])

        for comb in combs:
            formal_values = [i[1] for i in comb]
            if bg_level_and_mark_value.intersection(set(formal_values)) and not bg_level_and_mark_value.issubset(
                    set(formal_values)):
                try:
                    filtered_combs.remove(comb)
                except ValueError:
                    pass

    print('входная комбинация: {0}, входной массив: {1}, выходной массив: {2}, '
          'сокращение: {3:.2%}'.format(dim_set, len(combs), len(filtered_combs), 1 - len(filtered_combs) / len(combs)))
    return filtered_combs


def docs_needed(md, dd, measure_dim_sets):
    """Создание всех возможных комбинаций измерений

    Вход: cловари из имеющихся мер и измерений куба и набор сочитающихся измерений
    Выход: словарь с количество значений для каждого измерения и максимальное количество возможных документов"""

    # словарь вида {id измерения: количество значений для данного измерения}
    dim_with_number_of_values = {}

    # для каждого ключа (то есть id измерения) в словаре измерений
    for d in dd:
        # подчет количества значений в БД для измерения с id = d
        count = Dimension_Value.raw('select count(*) from dimension_value where dimension_id = %s' % d).scalar()

        # добавления получившегося результата в словарь
        dim_with_number_of_values[d] = count

    result = 0

    # для каждого набора (кортежа) измерений
    for d_set in measure_dim_sets:

        # возможное количество вариантов для кортежа измерений
        d_set_values_num = 1

        # для каждого измерения в кортеже
        for dim_id in d_set[1]:

            # если имеются значениия для данного измерения
            if dim_with_number_of_values[dim_id] != 0:
                d_set_values_num *= dim_with_number_of_values[dim_id]

        result += d_set_values_num

    # умножаем получившийся результат на количество значений мер
    result *= len(md)

    return dim_with_number_of_values, result


def report(cube_id, cube_name, md, dd, measure_dim_sets, dim_num, doc_num):
    """Отчет в консоль по генерации документов"""
    split_line = '=' * 10 + ' Шаг %s ' + '=' * 10
    print('Куб: {}, cube_id: {}'.format(cube_name, cube_id))
    print(split_line % '1')
    print('Меры: {}шт. {}\nИзмерения: {}шт. {}'.format(len(md), md, len(dd), dd))
    print(split_line % '2')
    print('Количество сочетаний измерений и мер: %s' % len(measure_dim_sets))
    print(measure_dim_sets)
    print(split_line % '3')
    print('(Измерение : Количество значений)')
    for key, value in dim_num.items():
        print('({}:{})'.format(dd[key], value))
    print('Полное количество документов до фильтрации и удаления пустых запросов: {:,}'.format(doc_num))


def query_data(mdx_query):
    """Фильтрация запросов на основе 1-4 пунктов от Алексея"""
    query_by_elements = mdx_query.split(' ')
    from_element = query_by_elements[query_by_elements.index('FROM') + 1]
    cube = from_element[1:len(from_element) - 4]

    d = {'dataMartCode': cube, 'mdxQuery': mdx_query}
    r = requests.post('http://conf.test.fm.epbs.ru/mdxexpert/CellsetByMdx', d)
    t = json.loads(r.text)

    if 'success' in t:
        return False, t
    elif t["cells"][0][0]["value"] is None:
        return False, None
    else:
        return True, t["cells"][0][0]["value"]


def logging(file_name, text):
    """Логирование промежуточных этапов"""
    with open(file_name + '.txt', 'w') as file:
        file.write(text)


def get_full_nvalues_for_dimensions(fvalues):
    """Получение полных вербальных значений измерений по формальным значениями"""
    full_nvalues = []
    for fvalue in fvalues:
        for value in Value.select().where(Value.fvalue == fvalue):
            full_nvalues.append(value.full_nvalue)
    return full_nvalues


def get_full_nvalue_for_measure(fvalue, cube_name):
    """Получение полного вербального значения меры по формальному значению и кубу"""
    for cube in Cube.select().where(Cube.name == cube_name):
        for cube_value in Cube_Value.select().where(Cube_Value.cube == cube.id):
            for value in Value.select().where(Value.id == cube_value.value_id, Value.fvalue == fvalue):
                return value.full_nvalue