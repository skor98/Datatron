#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 18 01:02:02 2017

@author: larousse
"""

import logging
from itertools import chain, zip_longest
from pymorphy2 import MorphAnalyzer
from nlp.tonita_parser import TonitaParser, ReHandler

logging.getLogger("pymorphy2").setLevel(logging.ERROR)

num_tp = TonitaParser()

num_tp.create_handler(
    ReHandler,
    regexp=r'(\d+)[-–—](\d+)',
    sub=r'\1 \2',
    flags=98
)

num_tp.create_handler(
    ReHandler,
    regexp=r'(\d*),(\d+)',
    sub=r'\1.\2',
    flags=98
)

numdict = {
    0: ['ноль', 'нуль', 'нулевой', 'нулевое'],
    1: ['один', 'первый', 'первое'],
    2: ['два', 'второй', 'второе'],
    3: ['три', 'третий', 'третье'],
    4: ['четыре', 'четвёртый', 'четвёртое'],
    5: ['пять', 'пятый', 'пятое'],
    6: ['шесть', 'шестой', 'шестое', 'шест'],
    7: ['семь', 'седьмой', 'седьмое'],
    8: ['восемь', 'восьмой', 'восьмое'],
    9: ['девять', 'девятый', 'девятое'],
    10: ['десять', 'десятый', 'десятое'],
    11: ['одиннадцать', 'одиннадцатый', 'одиннадцатое'],
    12: ['двенадцать', 'двенадцатый', 'двенадцатое'],
    13: ['тринадцать', 'тринадцатый', 'тринадцатое'],
    14: ['четырнадцать', 'четырнадцатый', 'четырнадцатое'],
    15: ['пятнадцать', 'пятнадцатый', 'пятнадцатое'],
    16: ['шестнадцать', 'шестнадцатый', 'шестнадцатое'],
    17: ['семнадцать', 'семнадцатый', 'семнадцатое'],
    18: ['восемнадцать', 'восемнадцатый', 'восемнадцатое'],
    19: ['девятнадцать', 'девятнадцатый', 'девятнадцатое'],
    20: ['двадцать', 'двадцатый', 'двадцатое'],
    30: ['тридцать', 'тридцатый', 'тридцатое'],
    40: ['сорок', 'сороковой', 'сороковое'],
    50: ['пятьдесят', 'пятидесятый', 'пятидесятое'],
    60: ['шестьдесят', 'шестидесятый', 'шестидесятое'],
    70: ['семьдесят', 'семидесятый', 'семидесятое'],
    80: ['восемьдесят', 'восьмидесятый', 'восьмидесятое'],
    90: ['девяносто', 'девяностый', 'девяностое'],
    100: ['сто', 'сотня', 'сотый', 'сотое'],
    200: ['двести', 'двухсотый', 'двухсотое'],
    300: ['триста', 'трёхсотый', 'трёхсотое'],
    400: ['четыреста', 'четырёхсотый', 'четырёхсотое'],
    500: ['пятьсот', 'пятисотый', 'пятисотое'],
    600: ['шестьсот', 'шестисотый', 'шестисотое'],
    700: ['семьсот', 'семисотый', 'семисотое'],
    800: ['восемьсот', 'восьмисотый', 'восьмисотое'],
    900: ['девятьсот', 'девятисотый', 'девятисотое'],
    1000: ['тысяча', 'тыща', 'тыс', 'тысячный', 'тысячное'],
    2000: ['двухтысячный', 'двухтысячное'],
    3000: ['трёхтысячный', 'трёхтысячное'],
    4000: ['четырёхтысячный', 'четырёхтысячное'],
    5000: ['пятитысячный', 'пятитысячное'],
    6000: ['шеститысячный', 'шеститысячное'],
    7000: ['семитысячный', 'семитысячное'],
    8000: ['восьмитысячный', 'восьмитысячное'],
    9000: ['девятитысячный', 'девятитысячное'],
    10**6: ['миллион', 'млн', 'лям', 'миллионный', 'миллионное'],
    10**9: ['миллиард', 'млрд', 'лярд', 'миллиардный', 'миллиардное'],
    10**12: ['триллион', 'трлн', 'триллионный', 'триллионное'],
}

revdict = dict(
    chain.from_iterable((zip_longest(
        v, [k], fillvalue=k) for k, v in numdict.items())))


def _anything(start=0, end=10**13):
    return '|'.join(i for i in revdict if start <= revdict[i] < end)

_thousands_re = r'''
   (?:
    (?P<m_num> {} | (\d+ \. )?\d+) [\s_] (?: {})
    | (?P<m> {}))
   '''.format(_anything(1, 20), _anything(1000, 1001), _anything(1000, 9001))

_hundreds_re = r'(?P<c>{})'.format(_anything(100, 901))
_teen_re = r'(?P<xi>{})'.format(_anything(10, 20))
_tens_re = r'(?P<x>{})'.format(_anything(20, 91))
_ones_re = r'(?P<i>{})'.format(_anything(1, 10))
_zero_re = r'(?P<zero>{})'.format(_anything(0, 1))

_sign_re = r'(?: (?P<plus> \+ | плюс) | (?P<minus> - | минус))'

literal_num_re = r'''
    (?:
        {}?
        (?: [\s_]? {})?
        (?: [\s_]? {})?
        (?:
            [\s_]? {}
            | (?: [\s_]? {})? (?: [\s_]? {})?
        ) | {}
    )'''.format(_sign_re, _thousands_re, _hundreds_re,
                _teen_re, _tens_re, _ones_re, _zero_re)

bignum_re = r'''
    {}?
    (?P<num> (\d+ \. )?\d+) [\s_]?
    (?P<deg>{})
    '''.format(_sign_re, _anything(10**6))


@num_tp.set_handler(ReHandler, regexp=literal_num_re, flags=98)
def literal_num_h(match):
    if all(i is None for i in match.groups()[2:]):
        return match.group(0)
    res = 0
    for idx in ('i', 'x', 'xi', 'c', 'm'):
        res += revdict.get(match.group(idx), 0)
    m_num = match.group('m_num')
    if m_num is not None:
        if m_num.isnumeric():
            res += 1000 * int(m_num)
        elif m_num.replace('.', '').isnumeric():
            res += int(1000 * float(m_num))
        else:
            res += 1000 * revdict.get(m_num, 1)
    if match.group('minus') is not None:
        res *= -1
    return str(res)


@num_tp.set_handler(ReHandler, regexp=bignum_re, flags=98)
def bugnum_h(minus, num, deg):
    deg = revdict.get(deg, 1)
    if minus is not None:
        deg *= -1
    if isinstance(num, int):
        return deg * int(num)
    num = num.replace(',', '.')
    if num.replace('.', '').isnumeric():
        return int(deg * float(num))
    return deg * revdict.get(num, 1)


romdict = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100, 'd': 500, 'm': 1000}
roman_re = r'''
   (?=[ivxlcdm])
   m{0,4}
   (cm|cd|d?c{0,3})
   (xc|xl|l?x{0,3})
   (ix|iv|v?i{0,3})
   '''


@num_tp.set_handler(ReHandler, regexp=roman_re, flags=98)
def roman_h(full):
    rom = [romdict.get(c.lower(), 0) for c in full]
    res = 0
    for item, next_ in zip(rom, rom[1:]):
        if item >= next_:
            res += item
        else:
            res -= item
    return str(res + rom[-1])


contracted_re = r'(?P<num>\d+)-?(?P<post>[а-яё]+)'

@num_tp.set_handler(ReHandler, regexp=contracted_re, flags=98)
def contracted_h(num, post):
    forms = wordforms.get(find_last_word(num), [])
    if any(form.endswith(post) for form in forms):
        return str(num)
    return ' '.join((str(num), post))


def find_last_word(num):
    if num in numdict:
        return num
    if num < min(numdict) or num > max(numdict):
        return None
    options = [num % (10**n) for n in range(1, 5)]
    options = [i for i in options if i != 0 and i in numdict]
    if not options:
        return None
    return options[-1]

morph = MorphAnalyzer()

wordforms = {num: set(chain.from_iterable([form.word for form in morph.parse(word)[0].lexeme] for word in verb)) for num, verb in numdict.items()}
