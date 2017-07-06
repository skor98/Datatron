#!/usr/bin/python3
# -*- coding: utf-8 -*-

import socket
import uuid

from messenger_manager import MessengerManager
from constants import CMD_START_MSG


def parse_feedback(fb):
    fb_exp = fb['formal']
    fb_norm = fb['verbal']

    exp = 'Экспертная обратная связь:\nКуб: {}\nМера: {}\nИзмерения: {}'
    norm = 'Дататрон выделил следующие параметры (обычная обратная связь):\n{}'

    exp = exp.format(
        fb_exp['cube'],
        fb_exp['measure'],
        ', '.join([i['dim'] + ': ' + i['val'] for i in fb_exp['dims']])
    )

    if fb_norm['measure'] == 'Значение':
        norm = norm.format(
            '1. {}\n'.format(fb_norm['domain']) +
            '\n'.join([str(idx + 2) + '. ' + i for idx, i in enumerate(fb_norm['dims'])]))

    else:
        norm = norm.format(
            '1. {}\n'.format(fb_norm['domain']) +
            '2. {}\n'.format(fb_norm['measure']) +
            '\n'.join([str(idx + 3) + '. ' + i for idx, i in enumerate(fb_norm['dims'])])
        )

    return '{0}\n{1}\n{0}\n{2}\n{0}'.format('='*20, exp, norm)


if __name__ == "__main__":
    print(CMD_START_MSG)

    while True:
        query_input = input('Введите запрос: ')
        query_input = query_input.strip()
        if query_input:
            greets = MessengerManager.greetings(query_input)
            if greets:
                print(greets)
                continue

            query_result = MessengerManager.make_request(
                query_input,
                'CMD',
                socket.gethostname(),
                socket.gethostname(),
                uuid.uuid4()
            )
            if not query_result.status:
                print(query_result.error)
            else:
                print(query_result.message)
                print(parse_feedback(query_result.feedback))
                print('Ответ: {}'.format(query_result.response))
