#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 14 18:08:47 2017

@author: larousse
"""

from datetime import datetime

from nlp.tonita_parser import TonitaParser


time_tp = TonitaParser()

norm_months = [
    'январь', 'февраль', 'март', 'апрель',
    'май', 'июнь', 'июль', 'август',
    'сентябрь', 'октябрь', 'ноябрь', 'декабрь'
]
time_tp.add_dict({m[:3]: m for m in norm_months if len(m) > 3})
anymonth = '|'.join(norm_months)

seasons = ['зима', 'весна', 'лето', 'осень']
anyseason = '|'.join(seasons)

time_tp.add_dict({
    'мес': 'месяц',
    'кв': 'квартал',
    'семестр': 'полугодие',
    'полгода': 'полугодие',
    'г': 'год',
    'сегодня': 'этот месяц',
})

time_tp.add_h(
    r'(?<!год )(?:2\d|19)\d{2}(?! год)',
    'год',
    preserve_old=True,
)

unit_lens = {
    'год': 12,
    'полугодие': 6,
    'триместр': 4,
    'квартал': 3,
    'месяц': 1
}
anyunit = '|'.join(unit_lens.keys())
unitcombo = r'(?:(?:\d+ )?(?:{}) ?)+'.format(anyunit)

begin_kw = ('состояние на', 'канун', 'старт')
end_kw = ('конец', 'итог', 'финал', 'окончание')

points_re = r'(?P<point>(?P<begin>{})|(?P<end>{}))'.format('|'.join(begin_kw), '|'.join(end_kw))
multipoints_re = r'(?:(?:{p}) )+({p})'.format(p='|'.join(begin_kw + end_kw))

time_tp.add_h(multipoints_re, r'\1')

current_kw = ('текущий', 'нынешний', 'этот?', 'сегодняшний')
last_kw = ('прошл(?:ый|ое)', 'предыдущий', 'прошедший', 'минувший', 'вчерашний')
next_kw = ('следующий', 'будущ(?:ий|ее)', 'грядущий', 'наступающий', 'завтрашний')

current_re = r'(?P<current>(?(point)(?:{c})?|(?:{c})))'.format(c='|'.join(current_kw))
last_re = r'(?P<last>(?:поза[- ]?)*(?:{}))'.format('|'.join(last_kw))
next_re = r'(?P<next_>(?:после[- ]?)*(?:{}))'.format('|'.join(next_kw))
rel_re = r'(?:{} )?(?:{}|{}|{}) (?P<unit>{})'.format(points_re, current_re, last_re, next_re, anyunit)

interval_re = r'(?P<pr>через )?(?P<interval>{})(?(pr)|(?: спустя| (?P<ago>назад)))'.format(unitcombo)

_dayformat = r'(?P<day>[0-3]?\d)'
_monthformat = r'(?P<month>0?[1-9]|1[012]|{})'.format(anymonth)
_yearformat = r'(?P<year>(?:19|2\d)\d{2})(?: год)?'
dateformat_re = r'(?:{}|{})[.,/ \-]{}[.,/ \-]{}'.format(
    points_re, _dayformat, _monthformat, _yearformat)

season_re = r'(?:{} )?(?P<season>{})'.format(points_re, anyseason)

static_re = r'(?:{} )?(?P<num>\d*[1-9]\d*) (?P<unit>{})'.format(points_re, anyunit)

statmonth_re = r'(?:{}|{}) (?P<month>{})'.format(points_re, _dayformat, anymonth)

shortyear_re = r'(?P<month>{}) (?P<year>\d\d)'.format(anymonth)


@time_tp.set_handler(rel_re)
def rel_h(point, begin, last, next_, unit):
    u_len = unit_lens.get(unit, 1)
    begin = begin is not None
    newdate = datetime.today()
    if last is not None:
        sum_len = u_len * (last.count('поза') + 1)
        newdate = mod_date(newdate, -sum_len)
    elif next_ is not None:
        sum_len = u_len * (next_.count('после') + 1)
        newdate = mod_date(newdate, sum_len)
    newdate = process_units(newdate, u_len, begin)
    nomonth = u_len == 12 and point is None
    return date_to_text(newdate, nomonth=nomonth)


@time_tp.set_handler(interval_re)
def interval_h(interval, ago, full):
    words = interval.split(' ')
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
        return full
    if ago is not None:
        sum_len *= -1
    newdate = mod_date(datetime.today(), sum_len)
    if len(u_lens) == 1:
        newdate = process_units(newdate, u_lens[0])
        return date_to_text(newdate, nomonth=(u_lens[0] == 12))
    return date_to_text(newdate)


@time_tp.set_handler(static_re)
def static_h(unit, num, begin, point):
    u_len = unit_lens.get(unit, 1)
    begin = begin is not None
    newdate = get_static(u_len, num, begin)
    noyear = u_len != 12
    nomonth = not noyear and not point
    return date_to_text(newdate, noyear=noyear, nomonth=nomonth)


@time_tp.set_handler(statmonth_re)
def statmonth_h(begin, month, day):
    num = norm_months.index(month) + 1
    begin = (begin is not None or
             (day is not None and
              day <= 15))
    newdate = get_static(1, num, begin)
    return date_to_text(newdate, noyear=True)


@time_tp.set_handler(dateformat_re)
def date_h(day, month, year, begin):
    if isinstance(month, int):
        month = max(min(month, 12), 1)
    else:
        month = norm_months.index(month) + 1
    begin = begin is not None
    if not begin:
        begin = day and day <= 15
    year = max(min(year, 3000), 1)
    newdate = datetime(month=month, year=year, day=1)
    newdate = process_units(newdate, 1, begin)
    return date_to_text(newdate)


@time_tp.set_handler(season_re)
def season_h(season, begin):
    num = seasons.index(season) + 1
    begin = begin is not None
    newdate = get_static(3, num, begin)
    newdate = mod_date(newdate, -1)
    return date_to_text(newdate, noyear=True)


@time_tp.set_handler(shortyear_re)
def shortyear_h(month, year):
    return date_to_text(datetime(year=year, month=norm_months.index(month) + 1, day=1))


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
        if 60 <= res_year < 100:
            res_year += 1900
        elif res_year < 1000:
            res_year += 2000
        res_year = ' '.join([str(res_year), 'год'])
    res_month = None if nomonth else norm_months[date.month - 1]
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
