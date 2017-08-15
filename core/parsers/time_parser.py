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
    'полугодие': 'семестр',
    'полгода': 'семестр',
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

points = r'(?:(?P<begin>начало|состояние|канун) |(?P<end>конец|итог|финал|окончание) )?'

current_re = r'{}(?:текущий|нынешний|этот?|сегодняшний) (?P<unit>{})'.format(points, anyunit)
last_re = r'{}(?P<pref>(?:поза[- ]?)*)(?:прошл(?:ый|ое)|предыдущий|прошедший|минувший) (?P<unit>{})'.format(points, anyunit)
next_re = '{}(?P<pref>(?:после[- ]?)*)(следующий|будущ(?:ий|ее)|грядущий|наступающий) (?P<unit>{})'.format(points, anyunit)
ago_re = r'(?P<interval>{}) назад'.format(unitcombo)
later_re = r'(?P<pr>через )?(?P<interval>{})(?(pr)| спустя)'.format(unitcombo)

_dayformat = '(?P<day>[0-3]?[0-9])'
_monthformat = '(?P<month>0?[1-9]|1[012]|{})'.format(anymonth)
_yearformat = r'(?P<year>(?:20)?[0-9][0-9])'
dateformat_re = r'{}(?P<sep>[.\- /]){}(?:(?P=sep){})?'.format(
    _dayformat, _monthformat, _yearformat)

static_re = r'{}(?P<num>0?[1-9]|1[012]?) (?P<unit>{})(?: {})?'.format(points, anyunit, _yearformat)

@tp_time.re_handler(current_re)
def current_h(match):
    u_len = unit_lens.get(match.group('unit'), 1)
    begin = bool(match.group('begin'))
    newdate = process_units(datetime.today(), u_len, begin)
    return date_to_text(newdate, nomonth=(u_len == 12))


@tp_time.re_handler(last_re)
def last_h(match):
    u_len = unit_lens.get(match.group('unit'), 1)
    sum_len = u_len * len(match.group('pref').split('з'))
    begin = bool(match.group('begin'))
    newdate = mod_date(datetime.today(), -sum_len)
    newdate = process_units(newdate, u_len, begin)
    return date_to_text(newdate, nomonth=(u_len == 12))


@tp_time.re_handler(next_re)
def next_h(match):
    u_len = unit_lens.get(match.group('unit'), 1)
    sum_len = u_len * len(match.group('pref').split('з'))
    begin = bool(match.group('begin'))
    newdate = mod_date(datetime.today(), sum_len)
    newdate = process_units(newdate, u_len, begin)
    return date_to_text(newdate, nomonth=(u_len == 12))


@tp_time.re_handler(ago_re)
def ago_h(match):
    words = match.group('interval').split(' ')
    sum_len = 0
    u_lens = []
    coeff = 1
    for word in words:
        if word.isnumeric():
            coeff = int(word)
        else:
            u_len = unit_lens.get(word, 0)
            if u_len != 0:
                u_lens.append(u_len)
            sum_len += u_len * coeff
            coeff = 1

    if not u_lens:
        return match.group(0)
    newdate = mod_date(datetime.today(), -sum_len)
    if len(u_lens) == 1:
        newdate = process_units(newdate, u_lens[0])
        return date_to_text(newdate, nomonth=(u_lens[0] == 12))
    return date_to_text(newdate, nomonth=False)


@tp_time.re_handler(later_re)
def later_h(match):
    words = match.group('interval').split(' ')
    sum_len = 0
    u_lens = []
    coeff = 1
    for word in words:
        if word.isnumeric():
            coeff = int(word)
        else:
            u_len = unit_lens.get(word, 0)
            if u_len != 0:
                u_lens.append(u_len)
            sum_len += u_len * coeff
            coeff = 1

    if not u_lens:
        return match.group(0)
    newdate = mod_date(datetime.today(), sum_len)
    if len(u_lens) == 1:
        newdate = process_units(newdate, u_lens[0])
        return date_to_text(newdate, nomonth=(u_lens[0] == 12))
    return date_to_text(newdate, nomonth=False)


@tp_time.re_handler(static_re)
def static_h(match):
    u_len = unit_lens.get(match.group('unit'), 1)
    if u_len == 12:
        return match.group(0)
    newmonth = u_len * int(match.group('num'))
    newmonth = max(min(newmonth, 12), 1)
    newyear = match.group('year')
    if not newyear:
        newyear = 1000
    else:
        newyear = int(newyear)
        if newyear < 100:
            newyear += 2000
    begin = bool(match.group('begin'))
    newdate = datetime(year=newyear, month=newmonth, day=1)
    newdate = process_units(newdate, u_len, begin)
    return date_to_text(newdate, nomonth=False)


@tp_time.re_handler(dateformat_re)
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
        newmonth = max(min(int(newmonth), 12), 1)
    else:
        newmonth = norm_months.index(newmonth) + 1
    newday = int(match.group('day'))
    newdate = datetime(day=newday, month=newmonth, year=newyear)
    newdate = process_units(newdate, 1, newday <= 15)
    return date_to_text(newdate, nomonth=False)


def process_units(date, u_len=1, begin=False):
    if begin:
        date = mod_date(date, -u_len)
    newmonth = ((date.month - 1) // u_len + 1) * u_len
    return datetime(year=date.year, month=newmonth, day=1)


def date_to_text(date, nomonth=False):
    res_month = norm_months[date.month-1]
    if date.year < 1200:
        if nomonth:
            return str(datetime.today().year)
        return res_month
    if nomonth:
        return str(date.year)
    return ' '.join([res_month, str(date.year)])


def mod_date(date, delta):
    delta += date.month - 1
    newmonth = (delta % 12) + 1
    newyear = date.year + (delta // 12)
    return datetime(year=newyear, month=newmonth, day=1)
