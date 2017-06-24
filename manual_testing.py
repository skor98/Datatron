import requests
import json
import uuid
import datetime
from os import getcwd, listdir
from data_retrieving import DataRetrieving

file_with_cubes_test = 'cubes CMLR02.txt'


def post_request_to_server(request):
    return requests.post('http://api.datatron.ru/test', {"Request": request})


def cube_testing(local=True):
    file_name = 'cube_{}_{}_OK_{}_Fail_{}.txt'
    testing_results = []
    true_answers = 0

    with open(file_with_cubes_test, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f):
            req, answer = line.split(':')
            if local:
                result = DataRetrieving.get_data(req, uuid.uuid4(), formatted=False).toJSON()
                system_answer = json.loads(result)
            else:
                system_answer = json.loads(post_request_to_server(req).text)

            response = system_answer['response']
            if response:
                try:
                    assert int(answer) == response
                    ars = '{}. Запрос "{}" отрабатывает корректно\n'.format(idx, req)
                    testing_results.append(ars)
                    true_answers += 1
                    print(ars)
                except AssertionError:
                    ars = '{}. Запрос "{}" отрабатывает некорректно (должны получать: {}, получаем: {})\n'
                    ars = ars.format(idx, req, int(answer), response)
                    testing_results.append(ars)
                    print(ars)
            else:
                ars = '{}. Запрос "{}" вызвал ошибку: {}\n'.format(idx, req, system_answer['message'])
                testing_results.append(ars)
                print(ars)

        current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if local:
            file_name = file_name.format('local', current_datetime, true_answers, len(testing_results) - true_answers)
        else:
            file_name = file_name.format('server', current_datetime, true_answers, len(testing_results) - true_answers)

        with open(file_name, 'w', encoding='utf-8') as file:
            file.write('\n'.join(testing_results))


def minfin_testing(local=True):
    test_files_paths = []
    test_path = r'{}\{}'.format(getcwd(), 'tests')
    file_name = 'minfin_{}_{}_OK_{}_Fail_{}.txt'
    testing_results = []
    true_answers = 0

    for file in listdir(test_path):
        if file.startswith("minfin"):
            test_files_paths.append(r'{}\{}'.format(test_path, file))

    for tf in test_files_paths:
        with open(tf, 'r', encoding='utf-8') as file:
            for line in file:
                req, question_id = line.split(':')
                if local:
                    result = DataRetrieving.get_minfin_data(req).toJSON()
                    system_answer = json.loads(result)
                else:
                    print('Серверное тестирование еще не реализовано')

                response = system_answer['number']
                question_id = float(''.join(question_id.split()))
                if response:
                    try:
                        assert question_id == response
                        ars = '{q_id} Запрос "{q_id}" отрабатывает корректно'.format(q_id=question_id)
                        testing_results.append(ars)
                        true_answers += 1
                        print(ars)
                    except AssertionError:
                        ars = '{q_id} Запрос "{q_id}" отрабатывает некорректно (должны получать:{q_id}, получаем:{fl})'
                        ars = ars.format(q_id=question_id, fl=response)
                        testing_results.append(ars)
                        print(ars)
                else:
                    # TODO: подправить MSG
                    ars = '{req} Запрос "{req}" вызвал ошибку: {msg}'.format(req=req, msg='Не определена')
                    testing_results.append(ars)
                    print(ars)

    current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if local:
        file_name = file_name.format('local', current_datetime, true_answers, len(testing_results) - true_answers)
    else:
        print('Логи не записаны, так как серверное тестирование еще не реализовано')

    with open(r'{}\{}'.format(test_path, file_name), 'w', encoding='utf-8') as file:
        file.write('\n'.join(testing_results))


minfin_testing()
