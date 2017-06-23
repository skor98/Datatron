import requests
import json
import uuid
import datetime
from data_retrieving import DataRetrieving

file_with_cubes_test = 'test_dolg.txt'


def post_request_to_server(request):
    return requests.post('http://api.datatron.ru/test', {"Request": request})


def testing(local=True):
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
