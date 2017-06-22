import requests
import json
import uuid
from data_retrieving import DataRetrieving


def post_request_to_server(request):
    return requests.post('http://api.datatron.ru/test', {"Request": request})


def server_testing():
    with open('test_dolg.txt', 'r', encoding='utf-8') as f:
        for line in f:
            req, answer = line.split(':')
            server_value = json.loads(post_request_to_server(req).text)
            response = server_value['response']
            if response:
                try:
                    assert int(answer) == response
                    print('Запрос "{}" отрабатывает корректно\n'.format(req))
                except AssertionError:
                    assert_result_str = 'Запрос "{}" отрабатывает некорректно (должны получать: {}, получаем: {})\n'
                    print(assert_result_str.format(req, int(answer), response))
            else:
                print('Запрос "{}" вызвал ошибку: {}\n'.format(req, server_value['message']))


def local_testing():
    with open('test_dolg.txt', 'r', encoding='utf-8') as f:
        for line in f:
            req, answer = line.split(':')
            result = DataRetrieving.get_data(req, uuid.uuid4(), formatted=False).toJSON()
            server_value = json.loads(result)
            response = server_value['response']
            if response:
                try:
                    assert int(answer) == response
                    print('Запрос "{}" отрабатывает корректно\n'.format(req))
                except AssertionError:
                    assert_result_str = 'Запрос "{}" отрабатывает некорректно (должны получать: {}, получаем: {})\n'
                    print(assert_result_str.format(req, int(answer), response))
            else:
                print('Запрос "{}" вызвал ошибку: {}\n'.format(req, server_value['message']))
