#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 18 01:02:02 2017

@author: larousse
"""

from core.tonita_parser import TonitaParser

num_tp = TonitaParser()

numdict = {
    0: ['ноль', 'нуль', 'нулевой'],
    1: ['один', 'первый'],
    2: ['два', 'второй'],
    3: ['три', 'третий'],
    4: ['четыре', 'четвёртый'],
    5: ['пять', 'пятый'],
    6: ['шесть', 'шестой'],
    7: ['семь', 'седьмой'],
    8: ['восемь', 'восьмой'],
    9: ['девять', 'девятый'],
    10: ['десять', 'десятый'],
    11: ['одиннадцать', 'одиннадцатый'],
    12: ['двенадцать', 'двенадцатый'],
    13: ['тринадцать', 'тринадцатый'],
    14: ['четырнадцать', 'четырнадцатый'],
    15: ['пятнадцать', 'пятнадцатый'],
    16: ['шестнадцать', 'шестнадцатый'],
    17: ['семнадцать', 'семнадцатый'],
    18: ['восемнадцать', 'восемнадцатый'],
    19: ['девятнадцать', 'девятнадцатый'],
    20: ['двадцать', 'двадцатый'],
    30: ['тридцать', 'тридцатый'],
    40: ['сорок', 'сороковой'],
    50: ['пятьдесят', 'пятидесятый'],
    60: ['шестьдесят', 'шестидесятый'],
    70: ['семьдесят', 'семидесятый'],
    80: ['восемьдесят', 'восьмидесятый'],
    90: ['девяносто', 'девяностый'],
    100: ['сто', 'сотый'],
    200: ['двести', 'двухсотый'],
    300: ['триста', 'трёхсотый'],
    400: ['четыреста', 'четырёхсотый'],
    500: ['пятьсот', 'пятисотый'],
    600: ['шестьсот', 'шестисотый'],
    700: ['семьсот', 'семисотый'],
    800: ['восемьсот', 'восьмисотый'],
    900: ['девятьсот', 'девятисотый'],
    1000: ['тысяча', 'тысячный'],
    2000: ['двухтысячный'],
    3000: ['трёхтысячный'],
    4000: ['четырёхтысячный'],
    5000: ['пятитысячный'],
    6000: ['шеститысячный'],
    7000: ['семитысячный'],
    8000: ['восьмитысячный'],
    9000: ['девятитысячный'],
}

revdict = {}
for num in numdict:
    for word in numdict[num]:
        revdict[word] = num


def _anything(start=0, end=10000):
    return '|'.join(i for i in revdict if start <= revdict[i] < end)
    
_thousands_re = r'(?:(?P<m_num>{}) тысяча|(?P<m>{}))'.format(_anything(1, 20), _anything(1000, 9001))
_hundreds_re = r'(?P<c>{})'.format(_anything(100, 901))
_teen_re = r'(?P<xi>{})'.format(_anything(10, 20))
_tens_re = r'(?P<x>{})'.format(_anything(20, 91))
_ones_re = r'(?P<i>{})'.format(_anything(1, 10))
_zero_re = r'(?P<zero>{})'.format('|'.join(numdict[0]))

literal_num_re = r'(?:(?P<sign>плюс|минус)?(?: ?{})?(?: ?{})?(?: ?{}|(?: ?{})?(?: ?{})?)|{})'.format(_thousands_re, _hundreds_re, _teen_re, _tens_re, _ones_re, _zero_re)


@num_tp.re_handler(literal_num_re)
def literal_num_h(match):
    if all(i is None for i in match.groups()[1:]):
        return match.group(0)
    res = 0
    for idx in ('i', 'x', 'xi', 'c', 'm'):
        res += revdict.get(match.group(idx), 0)
    if match.group('m_num'):
        res += 1000 * revdict.get(match.group('m_num'), 1)
    if match.group('sign') == 'минус':
        res *= -1
    return str(res)


romdict = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100, 'd': 500, 'm': 1000}
roman_re = r'(?=[ivxlcdm])m{0,4}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})'


@num_tp.re_handler(roman_re)
def roman_h(match):
    rom = [romdict.get(c, 0) for c in match.group(0)]
    res = 0
    for item, next_ in zip(rom, rom[1:]):
        if item >= next_:
            res += item
        else:
            res -= item
    return str(res + rom[-1])


bignum_re = r'(?P<num>[0-9.,]*[0-9]) ?(?P<deg>[MKМК]|[KК][KК])'

@num_tp.re_handler(bignum_re)
def bugnum_h(match):
    deg = match.group('deg')
    if not deg:
        deg = 1
    elif deg in ('K', 'К'):
        deg = 1000
    else:
        deg = 1000000
    num = match.group('num').replace(',', '.')
    if num.count('.') > 1:
        if any(len(i) != 3 for i in num.split('.')[1:]):
            return match.group(0)
        num = int(num.replace('.', ''))
    else:
        num = float(num) * deg
        if num % 1 == 0:
            return str(int(num))
    return str(num)
