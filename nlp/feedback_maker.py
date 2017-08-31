'''
Created on 24 Aug 2017

@author: larousse
'''

import logging
import re

import logs_helper  # pylint: disable=unused-import
from nlp import nlp_utils
from nlp.phrase_processor import Phrase
from nlp.tonita_parser import ReHandler


class BackFeeder(object):
    @staticmethod
    def prettify(cube, verbal_feedback):
        mask = CubeMasks.get_mask(cube)
        prepr_feedback = BackFeeder._preprocess_fb(cube, verbal_feedback)
        pretty = BackFeeder._make_phrase(mask, prepr_feedback)

        # logging.info(
        #     'Обратная связь для ответа из куба {}: {}'.format(
        #         cube,
        #         pretty.replace('\n', '\t')
        #     )
        # )

        return pretty

    @staticmethod
    def _preprocess_fb(cube, verbal_feedback):
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

        if verbal_feedback.get('measure', 'значение').lower() == 'значение':
            res['мера'] = None
        else:
            res['мера'] = verbal_feedback.get('measure')
            
        if 'месяц' not in res and cube == 'CLDO02':
            if str(res.get('год')) == '2017':
                res['месяц'] = 'июль'
            else:
                res['месяц'] = 'декабрь'

        if 'месяц' in res:
            if 'год' not in res:
                res['год'] = '2017'
            res['месгод'] = '{} {} года'.format(res.get('месяц'), res.get('год'))
        elif 'год' in res:
            res['месгод'] = '{} год'.format(res.get('год'))

        return {key: Phrase(res[key]) for key in res if res[key] is not None}

    @staticmethod
    def _make_phrase(mask, prepr_feedback):
        """
        Создание человекочитаемого фидбека из словаря по маске.
        """
        res = BackFeeder._mask_parser(mask, prepr_feedback)
        res = nlp_utils.re_strip('([\s_]+)', res, sides='l')
        res = nlp_utils.clean_double_spaces(res)

        return res

    @staticmethod
    def _mask_parser(mask, prepr_feedback):
        def _repl(key, gram=None, cap=None, lcont='', rcont='', dflt=''):
            val = prepr_feedback.get(key)
            if val is None:
                return dflt
            if gram is not None:
                val = val.inflect(gram.split('*'))

            resword = val.verbal

            if cap is not None and resword[0].islower():
                resword = resword[0].upper() + resword[1:]

            return ''.join((lcont, resword, rcont))

        return ReHandler(
            regexp=BackFeeder._main_re,
            sub=_repl,
            sep_left=False,
            sep_right=False,
            remove_none=True,
            flags=98,
        ).process(mask)

    _main_re = re.compile(r'''(?<!\\)\{
        ((?<!\\)\?(?P<lcont>.*?)(?<!\\)\?)?
        (?P<cap>(?<!\\)\^)?
        (?P<key>.+?)
        (\*(?P<gram>\w+?(\*\w+?)*))?
        ((?<!\\)\?(?P<rcont>.*?)(?<!\\)\?)?
        ((?<!\\)\|(?P<dflt>.*?))?
        (?<!\\)\}''', flags=114)


class CubeMasks(object):
    '''
    Маски для человекочитаемого фидбека по кубам
    Синтаксис: всё, что написано вне фигурных скобок, остаётся as is;
    Слева от текста всегда убираются все знаки препинания и пробелы, а первое слово пишется с большой буквы.
    Остальные слова пишутся точно так же, как и в источнике.
    Помимо этого, на последнем этапе из текста вычищаются все парные пробелы.
    Внутри фигурных скобок: {[?префикс?][^]код_измерения[*граммемы]?[постфикс]?|[значение по умолчанию]};
    (значения в квадратных скобках -- опциональные)

    Код_измерения -- первое слово названия измерения, из которого берётся значение
    (например, "{раздел}" может обозначать значение измерения "Раздел и подраздел расходов")
    Мере соответствует код "мера"; если мера равна "значение", она игнорируется.
    Кубу соответствует код "куб".
    Месяцу (если он есть) и году соответствует код "месгод" (нечто вида "март 2014 года")

    Если перед кодом измерения стоит символ "^", первая буква полученного значения
    будет сделана заглавной, иначе капитализация будет как в БД, без изменений.

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
    после "|".
    Вложение в условный контекст сложных выражений и других ссылок на данном этапе работы не поддерживается

    Пример маски:
    '{^показатели*nomn|Годовые доходы} {?бюджета ?территория*gent|федерального бюджета}{? в категории ?группа*nomn} в {месгод*loc2|прошлом году}{?: ?мера*nomn}'
    '''

    _common_cube_prefix = '{куб*nomn|Прочие данные}. '

    _base_cube_masks = {
        'CLDO01': 'Оперативные данные по {показатель*datv|федеральному бюджету}{?: ?мера*nomn}',
        'CLDO02': '{^показатели*nomn?, о?|О}перативные данные по {уровень*datv|бюджету}{? ?территория*gent}{?: ?мера*nomn}',
        'CLMR02': '{^показатели*nomn|Госдолг РФ} по состоянию на {месгод*accs|настоящее время}{?: ?мера*nomn}',
        'EXDO01': '{^показатели*nomn|Расходы} {уровень*gent|бюджета}{? ?территория*gent}{? на ?раздел*accs}{?: ?мера*nomn}',
        'EXYR03': '{^показатели*nomn|Годовые расходы} {уровень*gent|бюджета}{? ?территория*gent}{? на ?раздел*accs} в {месгод*loc2|прошлом году}{?: ?мера*nomn}',
        'FSYR01': '{^показатели*nomn|Финансирование} {?бюджета ?территория*gent|федерального бюджета} в {месгод*loc2|прошлом году} через {источники*accs|все источники}{?: ?мера*nomn}',
        'INDO01': '{^показатели*nomn|Доходы} {уровень*gent|бюджета}{? ?территория*gent}{? за счёт ?группа*gent}{?: ?мера*nomn}',
        'INYR03': '{^показатели*nomn|Годовые доходы} {уровень*gent|бюджета}{? ?территория*gent}{? за счёт ?группа*gent} в {месгод*loc2|прошлом году}{?: ?мера*nomn}'
    }

    @staticmethod
    def get_mask(cube):
        return CubeMasks._common_cube_prefix + CubeMasks._base_cube_masks.get(
            cube, '')
