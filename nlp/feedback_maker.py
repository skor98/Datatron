'''
Created on 24 Aug 2017

@author: larousse
'''

import re

from nlp import nlp_utils
from nlp.phrase_processor import Phrase


class BackFeeder(object):
    @staticmethod
    def fb_to_phrase(cube, verbal_feedback):
        mask = getattr(CubeMasks, cube)
        prepr_feedback = BackFeeder._preprocess_fb(verbal_feedback)
        return BackFeeder._make_phrase(mask, prepr_feedback)

    @staticmethod
    def _preprocess_fb(verbal_feedback):
        """
        Преобразование для дальнейшего парсинга словаря с вербальными значениями измерений.
        Здесь же обрабатываются замены отдельных значений на более удобные.
        """
        res = {'куб': verbal_feedback.get('domain')}
        for dim in verbal_feedback.get('dims', []):
            newkey = dim['dimension_caption'].split(' ', 1)[0].lower()
            newval = dim['member_caption'].strip()
            if newval and newval[:8] not in ('неуказан', 'неизвест'):
                res[newkey] = newval

        if res.get('территория') is None:
            res['территория'] = 'Российская Федерация'
        if verbal_feedback.get('measure', 'значение').lower() == 'значение':
            res['мера'] = None
        else:
            res['мера'] = verbal_feedback.get('measure')

        if 'месяц' in res and 'год' in res:
            res['месгод'] = '{} {} года'.format(res.get('месяц'), res.get('год'))
        elif 'год' in res:
            res['месгод'] = '{} год'.format(res.get('год'))
        elif 'месяц' in res:
            res['месгод'] = res.get('месяц')

        return {key: Phrase(res[key]) for key in res if res[key] is not None}

    @staticmethod
    def _make_phrase(mask, prepr_feedback):
        """
        Создание человекочитаемого фидбека из словаря по маске.
        """
        res = []
        for word in mask.split('{'):
            if '}' not in word:
                res.append(word)
                continue

            code, context = word.split('}', 1)
            if '/' in code:
                code, alt = code.split('/')
            else:
                alt = ''
            code = code.split('?')
            word_index = 2 if code[0] == '' else 0
            word = code[word_index].split('*')
            val = prepr_feedback.get(word[0].lower())

            if val is None:
                res.extend([alt, context])
                continue

            if len(word) == 1:
                val = val.verbal
            else:
                val = val.inflect(word[1:]).verbal

            code[word_index] = val
            res.extend(code + [context])

        res = ''.join(w for w in res if w)
        res = nlp_utils.re_strip(None, res, sides='l')
        res = nlp_utils.clean_double_spaces(res)
        if res[0].islower():
            res = res[0].upper() + res[1:]
        return res


class CubeMasks(object):
    '''
    Маски для человекочитаемого фидбека по кубам
    Синтаксис: всё, что написано вне фигурных скобок, остаётся as is;
    Слева от текста всегда убираются все знаки препинания и пробелы, а первое слово пишется с большой буквы.
    Остальные слова пишутся точно так же, как и в источнике.
    Помимо этого, на последнем этапе из текста вычищаются все парные пробелы.
    Внутри фигурных скобок: {[?префикс?]код_измерения[*граммемы]?[постфикс]?/[значение по умолчанию]};
    (значения в квадратных скобках -- опциональные)

    Код_измерения -- первое слово названия измерения, из которого берётся значение
    (например, "{раздел}" может обозначать значение измерения "Раздел и подраздел расходов")
    Мере соответствует код "мера"; если мера равна "значение", она игнорируется.
    Кубу соответствует код "куб", но пока его использовать смысла нет, т.к. всё равно
    разным кубам соответствуют разные маски.
    Месяцу (если он есть) и году соответствует код "месгод" (нечто вида "март 2014 года")

    После кода через звёздочку идёт список граммем, соответствующих форме, в которую нужно
    поставить значение (между собой граммемы тоже разделены звёздочками).
    Например, "{раздел*gent*plur}" возьмёт значение нужного измерения и поставит его
    в родительный падеж множественного числа.
    (список обозначений для граммем: pymorphy2.readthedocs.io/en/latest/user/grammemes.html)

    Суффикс и постфикс (aka условный контекст) подставляются до/после подставленного значения,
    но только если значение найдено в полученном результате.
    Например "данные{? за ?год? год?}" вернёт "данные за <значение года> год", если во
    входных данных указан год, а если год не указан -- просто "данные".

    Если же значение не найдено, на его место подставляется вариант по умолчанию - тот, что указан
    после "/".
    Вложение в условный контекст сложных выражений и других ссылок на данном этапе работы не поддерживается

    Пример маски:
    '{показатели*nomn/Годовые доходы} {?бюджета ?территория*gent/федерального бюджета}{? в категории ?группа*nomn} в {месгод*loc2/прошлом году}{?: ?мера*nomn}'
    '''

    CLDO01 = 'Оперативные данные по {показатель*datv/федеральному бюджету}{?: ?мера*nomn}'
    CLDO02 = 'Оперативные данные по {уровень*datv/бюджету} {территория*gent/РФ}{?: ?мера*nomn}'
    CLMR02 = '{показатели*nomn/Госдолг РФ} по состоянию на {месгод*accs/настоящее время}{?: ?мера*nomn}'
    EXDO01 = 'Оперативные данные по {показатели*datv/расходам} {?бюджета ?территория*gent/федерального бюджета}{? на ?раздел*accs}{?: ?мера*nomn}'
    EXYR03 = '{показатели*nomn/Годовые расходы} из {?бюджета ?территория*gent/федерального бюджета}{? на ?раздел*accs} в {месгод*loc2/прошлом году}{?: ?мера*nomn}'
    FSYR01 = '{показатели*nomn/Финансирование} {?бюджета ?территория*gent/федерального бюджета} в {месгод*loc2/прошлом году} через {источники*accs/все источники}{?: ?мера*nomn}'
    INDO01 = 'Оперативные данные по {показатели*datv/доходам} {?бюджета ?территория*gent/федерального бюджета}{? в категории ?группа*nomn}{?: ?мера*nomn}'
    INYR03 = '{показатели*nomn/Годовые доходы} {?бюджета ?территория*gent/федерального бюджета}{? в категории ?группа*nomn} в {месгод*loc2/прошлом году}{?: ?мера*nomn}'
