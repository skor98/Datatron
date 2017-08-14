#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 06:39:36 2017

@author: larousse
"""

# pylint: disable=missing-docstring

import re
from datetime import datetime

norm_months = [
    'январь', 'февраль', 'март', 'апрель',
    'май', 'июнь', 'июль', 'август',
    'сентябрь', 'октябрь', 'ноябрь', 'декабрь'
]
short_months = [m[:3] for m in norm_months]
all_months = '|'.join(norm_months+short_months)
unit_lens = {
    'год': 12,
    'месяц': 1,
    'квартал': 3,
    'полугодие': 6,
    'семестр': 6,
    'триместр': 4,
}
anyunit = '|'.join(unit_lens.keys())
unitcombo = '(?:(?:[0-9]+ )?(?:{}) ?)+'.format(anyunit)

current_re = r'(?:текущий|нынешний|этот?|сегодняшний) (?P<unit>{})'.format(anyunit)
last_re = r'(?:прошл(?:ый|ое)|предыдущий|прошедший|минувший) (?P<unit>{})'.format(anyunit)
beforelast_re = r'(?P<pref>(?:поза[- ]?)+)прошлый (?P<unit>{})'.format(anyunit)
ago_re = r'(?P<interval>{}) назад'.format(unitcombo)
next_re = '(следующий|будущий|грядущий|наступающий) (?P<unit>{})'.format(anyunit)
afternext_re = '(?P<pref>(?:после[- ]?)+)следующий (?P<unit>{})'.format(anyunit)
later_re = '(?:через )?(?:<interval>{})(?: спустя)?'.format(unitcombo)

_dayformat = '(?P<day>[0-3]?[0-9])'
_monthformat = '(?P<month>0?[0-9]|1[012]|{})'.format(all_months)
_yearformat = r'(?:20)?(?P<year>[01][0-9])'
dateformat_re = r'{}?(?P<sep>[.\- /]){}(?P=sep){}'.format(
    _dayformat, _monthformat, _yearformat)


class TonitaParser(object):

    actions = []

    @staticmethod
    def handler(condition='', preserve_old=False):
        cond_re = re.compile(r'(?<!\w)' + condition + r'(?!\w)')

        def _decorate(func):
            def _wrapped(text):
                match = cond_re.search(text)
                if match is None:
                    return text
                params = {'match': match, 'today': datetime.today()}
                res = func(**params)
                if preserve_old:
                    return ' '.join([text, res])
                return cond_re.sub(res, text)
            TonitaParser.actions.append(_wrapped)
            return _wrapped
        return _decorate

    @staticmethod
    def process(text):
        res = text
        for act in TonitaParser.actions:
            res = act(res)
        return res


@TonitaParser.handler(current_re, preserve_old=False)
def current_h(match, today):
    return date_to_text(today, match.group('unit'))


@TonitaParser.handler(last_re, preserve_old=False)
def last_h(match, today):
    u_len = unit_lens[match.group('unit')]
    newdate = mod_date(today, -u_len)
    return date_to_text(newdate, match.group('unit'))


@TonitaParser.handler(beforelast_re, preserve_old=False)
def beforelast_h(match, today):
    sum_len = unit_lens[match.group('unit')] * len(match.group('pref').split('з'))
    newdate = mod_date(today, -sum_len)
    return date_to_text(newdate, match.group('unit'))


@TonitaParser.handler(ago_re, preserve_old=True)
def ago_h(match, today):
    words = match.group('interval').split(' ')
    unit = max(unit_lens.keys(), key=unit_lens.get)
    sum_len = 0
    coeff = 1
    for word in words:
        if word.isnumeric():
            coeff = int(word)
        else:
            sum_len += unit_lens[word] * coeff
            coeff = 1
            if unit_lens[word] < unit_lens[unit]:
                unit = word
    newdate = mod_date(today, -sum_len)
    return date_to_text(newdate, unit)


@TonitaParser.handler(next_re, preserve_old=False)
def next_h(match, today):
    u_len = unit_lens[match.group('unit')]
    newdate = mod_date(today, u_len)
    return date_to_text(newdate, match.group('unit'))


@TonitaParser.handler(afternext_re, preserve_old=False)
def afternext_h(match, today):
    sum_len = unit_lens[match.group('unit')] * len(match.group('pref').split('л'))
    newdate = mod_date(today, sum_len)
    return date_to_text(newdate, match.group('unit'))


@TonitaParser.handler(later_re, preserve_old=True)
def later_h(match, today):
    words = match.group('interval').split(' ')
    unit = max(unit_lens.keys(), key=unit_lens.get)
    sum_len = 0
    coeff = 1
    for word in words:
        if word.isnumeric():
            coeff = int(word)
        else:
            sum_len += unit_lens[word] * coeff
            coeff = 1
            if unit_lens[word] < unit_lens[unit]:
                unit = word
    newdate = mod_date(today, sum_len)
    return date_to_text(newdate, unit)


@TonitaParser.handler(dateformat_re, preserve_old=False)
def date_h(match, today):
    mdict = match.groupdict()
    mdict = {key: mdict[key] for key in mdict if mdict[key] is not None}
    newyear = int(mdict.get('year', today.year))
    if newyear < 100:
        newyear += 2000
    newmonth = mdict.get('month', today.month)
    if newmonth.isnumeric():
        newmonth = int(newmonth)
    elif newmonth in norm_months:
        newmonth = norm_months.index(newmonth) + 1
    else:
        newmonth = short_months.index(newmonth) + 1
    newdate = datetime(day=1, month=newmonth, year=newyear)
    newday = int(mdict.get('day', 100))
    if newday <= 10:
        newdate = mod_date(newdate, -1)

    unit = min(unit_lens.keys(), key=unit_lens.get)
    return date_to_text(newdate, unit)


def date_to_text(date, unit):
    res = str(date.year)
    u_len = unit_lens[unit]
    if u_len != 12:
        u_end = date.month + u_len - ((date.month-1) % u_len) - 1
        res = ' '.join([norm_months[u_end-1], res])
    return res


def mod_date(date, delta):
    abstime = date.month + (date.year * 12)
    abstime += delta
    newmonth = abstime % 12
    newyear = abstime // 12
    if newmonth == 0:
        newyear -= 1
        newmonth = 12
    return datetime(year=newyear, month=newmonth, day=1)
