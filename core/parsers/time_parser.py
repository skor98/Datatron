#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 14 18:08:47 2017

@author: larousse
"""

from datetime import datetime

from core.tonita_parser import TonitaParser

tp_time = TonitaParser()

norm_months = [
    'январь', 'февраль', 'март', 'апрель',
    'май', 'июнь', 'июль', 'август',
    'сентябрь', 'октябрь', 'ноябрь', 'декабрь'
]
tp_time.add_many_subs({m[:3]: m for m in norm_months if len(m) > 3})
anymonth = '|'.join(norm_months)

tp_time.add_many_subs({
    'г': 'год',
    'мес': 'месяц',
    'кв': 'квартал',
    'полугодие': 'семестр'
})
unit_lens = {
    'год': 12,
    'семестр': 6,
    'триместр': 4,
    'квартал': 3,
    'месяц': 1,
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
_monthformat = '(?P<month>0?[0-9]|1[012]|{})'.format(anymonth)
_yearformat = r'(?P<year>(?:20)?[0-9][0-9])'
dateformat_re = r'{}(?P<sep>[.\- /]){}(?:(?P=sep){})?'.format(
    _dayformat, _monthformat, _yearformat)

static_re = r'(?P<num>[0-9]+) (?P<unit>{})(?: {})?'.format(anyunit, _yearformat)

@tp_time.re_handler(current_re, preserve_old=False)
def current_h(match):
    return date_to_text(datetime.today(), match.group('unit'))


@tp_time.re_handler(last_re, preserve_old=False)
def last_h(match):
    u_len = unit_lens[match.group('unit')]
    newdate = mod_date(datetime.today(), -u_len)
    return date_to_text(newdate, match.group('unit'))


@tp_time.re_handler(beforelast_re, preserve_old=False)
def beforelast_h(match):
    sum_len = unit_lens[match.group('unit')] * len(match.group('pref').split('з'))
    newdate = mod_date(datetime.today(), -sum_len)
    return date_to_text(newdate, match.group('unit'))


@tp_time.re_handler(ago_re, preserve_old=True)
def ago_h(match):
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
    newdate = mod_date(datetime.today(), -sum_len)
    return date_to_text(newdate, unit)


@tp_time.re_handler(next_re, preserve_old=False)
def next_h(match):
    u_len = unit_lens[match.group('unit')]
    newdate = mod_date(datetime.today(), u_len)
    return date_to_text(newdate, match.group('unit'))


@tp_time.re_handler(afternext_re, preserve_old=False)
def afternext_h(match):
    sum_len = unit_lens[match.group('unit')] * len(match.group('pref').split('л'))
    newdate = mod_date(datetime.today(), sum_len)
    return date_to_text(newdate, match.group('unit'))


@tp_time.re_handler(later_re, preserve_old=True)
def later_h(match):
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
    newdate = mod_date(datetime.today(), sum_len)
    return date_to_text(newdate, unit)


@tp_time.re_handler(static_re, preserve_old=False)
def static_h(match):
    unit = match.group('unit')
    u_len = unit_lens[unit]
    if u_len == 12:
        return match.group(0)
    
    num = int(match.group('num')) % (12//u_len)
    if num == 0:
        num = 12//u_len
    newyear = match.group('year')
    if not newyear:
        newyear = 1000
    else:
        newyear = int(newyear)
        if newyear < 100:
            newyear += 2000
    newmonth = u_len * (num - 1) + 1
    newdate = datetime(year=newyear, month=newmonth, day=1)
    return date_to_text(newdate, unit)


@tp_time.re_handler(dateformat_re, preserve_old=False)
def date_h(match):
    newyear = match.group('year')
    if not newyear:
        newyear = 1000
    else:
        newyear = int(newyear)
        if newyear < 100:
            newyear += 2000
    newmonth = match.group('month')
    if newmonth.isnumeric():
        newmonth = int(newmonth)
    else:
        newmonth = norm_months.index(newmonth) + 1
    newday = int(match.group('day'))
    newdate = datetime(day=newday, month=newmonth, year=newyear)
    if newday <= 10:
        newdate = mod_date(newdate, -1)

    unit = min(unit_lens.keys(), key=unit_lens.get)
    return date_to_text(newdate, unit)


def date_to_text(date, unit):
    u_len = unit_lens.get(unit, 1)
    if u_len != 12:
        u_end = date.month + u_len - ((date.month-1) % u_len) - 1
        res_month = norm_months[u_end-1]
        if date.year < 1200:
            return res_month
        return ' '.join([res_month, str(date.year)])
    elif date.year < 1200:
        return str(datetime.today().year)
    return str(date.year)


def mod_date(date, delta):
    abstime = date.month + (date.year * 12)
    abstime += delta
    newmonth = abstime % 12
    newyear = abstime // 12
    if newmonth == 0:
        newyear -= 1
        newmonth = 12
    return datetime(year=newyear, month=newmonth, day=1)
