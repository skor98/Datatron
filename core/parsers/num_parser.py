#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 18 01:02:02 2017

@author: larousse
"""

from core.tonita_parser import TonitaParser

num_tp = TonitaParser()

num_tp.add_simple(r'(\d+)[-–—](\d+)', r'\1 \2')

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
    100: ['сто', 'сотня', 'сотый'],
    200: ['двести', 'двухсотый'],
    300: ['триста', 'трёхсотый'],
    400: ['четыреста', 'четырёхсотый'],
    500: ['пятьсот', 'пятисотый'],
    600: ['шестьсот', 'шестисотый'],
    700: ['семьсот', 'семисотый'],
    800: ['восемьсот', 'восьмисотый'],
    900: ['девятьсот', 'девятисотый'],
    1000: ['тысяча', 'тыща', 'тыс', 'К', 'K', 'тысячный'],
    2000: ['двухтысячный'],
    3000: ['трёхтысячный'],
    4000: ['четырёхтысячный'],
    5000: ['пятитысячный'],
    6000: ['шеститысячный'],
    7000: ['семитысячный'],
    8000: ['восьмитысячный'],
    9000: ['девятитысячный'],
    10**6: ['миллион', 'млн', 'M', 'М', 'KK', 'КК', 'лям', 'миллионный'],
    10**9: ['миллиард', 'млрд', 'лярд', 'миллиардный'],
    10**12: ['триллион', 'трлн', 'триллионный'],
}

revdict = {}
for num in numdict:
    for word in numdict[num]:
        revdict[word] = num


def _anything(start=0, end=10**13):
    return '|'.join(i for i in revdict if start <= revdict[i] < end)

_thousands_re = r'(?:(?P<m_num>{}|(\d+[.,])?\d+) (?:{})|(?P<m>{}))'.format(_anything(1, 20), _anything(1000, 1001), _anything(1000, 9001))
_hundreds_re = r'(?P<c>{})'.format(_anything(100, 901))
_teen_re = r'(?P<xi>{})'.format(_anything(10, 20))
_tens_re = r'(?P<x>{})'.format(_anything(20, 91))
_ones_re = r'(?P<i>{})'.format(_anything(1, 10))
_zero_re = r'(?P<zero>{})'.format(_anything(0, 1))

_sign_re = r'(?:(?P<plus>\+|плюс)|(?P<minus>-|минус))'

literal_num_re = r'(?:{}?(?: ?{})?(?: ?{})?(?: ?{}|(?: ?{})?(?: ?{})?)|{})'.format(_sign_re, _thousands_re, _hundreds_re, _teen_re, _tens_re, _ones_re, _zero_re)

bignum_re = r'{}?(?P<num>{}|(\d+[.,])?\d+) ?(?P<deg>{})'.format(_sign_re, _anything(1, 20), _anything(10**6))


@num_tp.re_handler(literal_num_re)
def literal_num_h(match):
    if all(i is None for i in match.groups()[1:]):
        return match.group(0)
    res = 0
    for idx in ('i', 'x', 'xi', 'c', 'm'):
        res += revdict.get(match.group(idx), 0)
    m_num = match.group('m_num')
    if m_num:
        m_num = m_num.replace(',', '.')
        if m_num.isnumeric():
            res += 1000 * int(m_num)
        elif m_num.replace('.', '').isnumeric():
            res += int(1000 * float(m_num))
        else:
            res += 1000 * revdict.get(m_num, 1)
    if match.group('minus'):
        res *= -1
    return str(res)


@num_tp.re_handler(bignum_re)
def bugnum_h(match):
    deg = revdict.get(match.group('deg'), 1)
    if match.group('minus'):
        deg *= -1
    num = match.group('num').replace(',', '.')
    if num.isnumeric():
        return deg * int(num)
    if num.replace('.', '').isnumeric():
        return int(deg * float(num))
    return deg * revdict.get(num, 1)


romdict = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100, 'd': 500, 'm': 1000}
roman_re = r'(?=[ivxlcdm])m{0,4}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})'

@num_tp.re_handler(roman_re)
def roman_h(match):
    rom = [romdict.get(c.lower(), 0) for c in match.group(0)]
    res = 0
    for item, next_ in zip(rom, rom[1:]):
        if item >= next_:
            res += item
        else:
            res -= item
    return str(res + rom[-1])
