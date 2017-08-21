#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 14 18:08:47 2017

@author: larousse
"""

from datetime import datetime

from core.tonita_parser import TonitaParser

time_tp = TonitaParser()

norm_months = [
    'январь', 'февраль', 'март', 'апрель',
    'май', 'июнь', 'июль', 'август',
    'сентябрь', 'октябрь', 'ноябрь', 'декабрь'
]
time_tp.add_many({m[:3]: m for m in norm_months if len(m) > 3})
anymonth = '|'.join(norm_months)

seasons = ['зима', 'весна', 'лето', 'осень']
anyseason = '|'.join(seasons)

time_tp.add_many({
    'мес': 'месяц',
    'кв': 'квартал',
    'семестр': 'полугодие',
    'полгода': 'полугодие',
    'г': 'год',
    'сегодня': 'этот месяц',
})

time_tp.add_simple(r'(20|19)\d{2}', 'год', True)

unit_lens = {
    'год': 12,
    'полугодие': 6,
    'триместр': 4,
    'квартал': 3,
    'месяц': 1
}
anyunit = '|'.join(unit_lens.keys())
unitcombo = r'(?:(?:\d+ )?(?:{}) ?)+'.format(anyunit)

begin_re = r''
points_re = r'(?P<point>(?P<begin>состояние на|канун|старт)|(?P<end>конец|итог|финал|окончание))'.format(begin_re)

current_kw = ('текущий', 'нынешний', 'этот?', 'сегодняшний')
last_kw = ('прошлый', 'прошлое', 'предыдущий', 'прошедший', 'минувший', 'вчерашний')

current_re = r'(?:{p} )?(?(point)({c})?|({c})) (?P<unit>{u})'.format(p=points_re, c='|'.join(current_kw), u=anyunit)
last_re = r'(?:{} )?(?P<pref>(?:поза[- ]?)*)(?:{}) (?P<unit>{})'.format(points_re, '|'.join(last_kw), anyunit)
next_re = r'(?:{} )?(?P<pref>(?:после[- ]?)*)(следующий|будущ(?:ий|ее)|грядущий|наступающий|завтрашний) (?P<unit>{})'.format(points_re, anyunit)
interval_re = r'(?P<pr>через )?(?P<interval>{})(?(pr)|(?: спустя| (?P<ago>назад)))'.format(unitcombo)

_dayformat = r'(?P<day>[0-3]?\d)'
_monthformat = r'(?P<month>0?[1-9]|1[012]|{})'.format(anymonth)
_yearformat = r'(?P<year>(?:19|20)\d\d)'
dateformat_re = r'(?:{}|{})[.,/ \-]{}[.,/ \-]{}'.format(
    points_re, _dayformat, _monthformat, _yearformat)

season_re = r'(?:{} )?(?P<season>{})'.format(points_re, anyseason)

static_re = r'(?:{} )?(?P<num>\d*[1-9]\d*) (?P<unit>{})'.format(points_re, anyunit)

statmonth_re = r'{} (?P<month>{})'.format(points_re, anymonth)

@time_tp.re_handler(current_re)
def current_h(match):
    u_len = unit_lens.get(match.group('unit'), 1)
    begin = bool(match.group('begin'))
    newdate = process_units(datetime.today(), u_len, begin)
    return date_to_text(newdate, nomonth=(u_len == 12))


@time_tp.re_handler(last_re)
def last_h(match):
    u_len = unit_lens.get(match.group('unit'), 1)
    sum_len = u_len * len(match.group('pref').split('з'))
    begin = bool(match.group('begin'))
    newdate = mod_date(datetime.today(), -sum_len)
    newdate = process_units(newdate, u_len, begin)
    return date_to_text(newdate, nomonth=(u_len == 12))


@time_tp.re_handler(next_re)
def next_h(match):
    u_len = unit_lens.get(match.group('unit'), 1)
    sum_len = u_len * len(match.group('pref').split('з'))
    begin = bool(match.group('begin'))
    newdate = mod_date(datetime.today(), sum_len)
    newdate = process_units(newdate, u_len, begin)
    return date_to_text(newdate, nomonth=(u_len == 12))


@time_tp.re_handler(interval_re)
def interval_h(match):
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
    if match.group('ago'):
        sum_len *= -1
    newdate = mod_date(datetime.today(), sum_len)
    if len(u_lens) == 1:
        newdate = process_units(newdate, u_lens[0])
        return date_to_text(newdate, nomonth=(u_lens[0] == 12))
    return date_to_text(newdate)


@time_tp.re_handler(static_re)
def static_h(match):
    u_len = unit_lens.get(match.group('unit'), 1)
    num = int(match.group('num'))
    begin = bool(match.group('begin'))
    end = bool(match.group('end'))
    newdate = get_static(u_len, num, begin)
    noyear = u_len != 12
    nomonth = not noyear and not begin and not end
    return date_to_text(newdate, noyear=noyear, nomonth=nomonth)


@time_tp.re_handler(statmonth_re)
def statmonth_h(match):
    num = norm_months.index(match.group('month')) + 1
    begin = bool(match.group('begin'))
    newdate = get_static(1, num, begin)
    return date_to_text(newdate, noyear=True)


@time_tp.re_handler(dateformat_re)
def date_h(match):
    newmonth = match.group('month')
    if newmonth.isnumeric():
        newmonth = max(min(int(newmonth), 12), 1)
    else:
        newmonth = norm_months.index(newmonth) + 1
    begin = bool(match.group('begin'))
    if not begin:
        newday = match.group('day')
        begin = newday and int(newday) <= 15
    newyear = max(min(int(match.group('year')), 3000), 1)
    newdate = datetime(month=newmonth, year=newyear, day=1)
    newdate = process_units(newdate, 1, begin)
    return date_to_text(newdate)

@time_tp.re_handler(season_re)
def season_h(match):
    num = seasons.index(match.group('season')) + 1
    begin = bool(match.group('begin'))
    newdate = get_static(3, num, begin)
    newdate = mod_date(newdate, -1)
    return date_to_text(newdate, noyear=True)


def process_units(date, u_len=1, begin=False):
    if begin:
        date = mod_date(date, -u_len)
    newmonth = ((date.month - 1) // u_len + 1) * u_len
    return datetime(year=date.year, month=newmonth, day=1)


def date_to_text(date, noyear=False, nomonth=False):
    if noyear:
        res_year = None
    else:
        res_year = date.year
        if 60 <= res_year < 1000:
            res_year += 1900
        elif res_year < 1000:
            res_year += 2000
        res_year = str(res_year)
    res_month = None if nomonth else norm_months[date.month-1]
    return ' '.join(i for i in (res_month, res_year) if i is not None)


def mod_date(date, delta):
    delta += date.month - 1
    newmonth = (delta % 12) + 1
    newyear = min(max(1, date.year + (delta // 12)), 3000)
    return datetime(year=newyear, month=newmonth, day=1)


def get_static(u_len, num, begin=False):
    if u_len == 12:
        year = max(min(num, 3000), 1)
        newdate = datetime(month=1, year=year, day=1)
    else:
        newmonth = max(min(u_len * num, 12), 1)
        newdate = datetime(month=newmonth, year=100, day=1)
    return process_units(newdate, u_len, begin)
