from messenger_manager import MessengerManager
from constants import CMD_START_MSG
import json
import requests


def parse_feedback(fb):
    fb_exp = fb['formal']
    fb_norm = fb['verbal']
    exp = 'Экспертная обратная связь:\nКуб: {}\nМера: {}\nИзмерения: {}'
    norm = 'Дататрон выделил следующие параметры (обычная обратная связь):\n{}'
    exp = exp.format(fb_exp['cube'], fb_exp['measure'], ', '.join([i['dim'] + ': ' + i['val'] for i in fb_exp['dims']]))
    norm = norm.format('0. {}\n'.format(
        fb_norm['measure']) + '\n'.join([str(idx + 1) + '. ' + i for idx, i in enumerate(fb_norm['dims'])]))
    line = "==" * 10
    return '{0}\n{1}\n{0}\n{2}\n{0}'.format(line, exp, norm)


print(CMD_START_MSG)

continue_case = ('Y', 'y')
http_api = False
flag = True

http_usage = input('Работать по HTTP API Y[y]/N[n]: ')

if http_usage in ('y', 'Y'):
    http_api = True

while flag:
    text = input('Введите запрос: ')
    text = text.lower().strip()
    if text:
        greets = MessengerManager.greetings(text)
        if greets:
            print(greets)
            continue

        result = None
        if http_api:
            result = requests.get('http://localhost:8019/get/%s' % text)
            result = json.loads(result.text)
            if result['error']:
                print(result['error'])
            else:
                print(parse_feedback(result['feedback']))
                print('Ответ: ' + result['response'])
        else:
            result = MessengerManager.make_request(text.lower(), 'CMD')
            if not result.status:
                print(result.error)
            else:
                print(result.message)
                print(parse_feedback(result.feedback))
                print('Ответ: ' + result.response)

        y_n = input('Продолжить Y/N? ')
        if y_n in continue_case:
            flag = True
        else:
            flag = False
    else:
        print('Введите не пустую строку!')