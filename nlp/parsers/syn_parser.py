#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 15 15:07:15 2017

@author: larousse
"""

from nlp.tonita_parser import TonitaParser, ReHandler


syn_tp = TonitaParser()

# распространённые канцелярские сокращения, с точкой/пробелом и без
contr = {
    'гос': 'государственный',
    'соц': 'социальный',
    'нац': 'национальный',
    'фед': 'федеральный',
    'ин': 'иностранный',
    'мин': 'министерство',
    'фин': 'финансовый'
}
contr = {key + r'\W+': contr[key] + ' ' for key in contr}
syn_tp.handlers.extend(ReHandler.fromdict(
        contr, sep_left=True, sep_right=False, flags=98
))

# разные варианты указания на Россию
russland_names = (
    'россия',
    'российский[\s_]федерация',
    'россиюшка',
    'рашка',
    'русь',
    'наш[\s_]страна',
    'этот?[\s_]страна',
    'держава',)
syn_tp.handlers.extend(
    ReHandler.fromdict(
        dict.fromkeys(russland_names, 'РФ'),
        flags=98
    )
)

# разные варианты указания на Минфин
minfin_names = (
    'мф',
    'министерство[\s_]финанс(?:ы|овый)?',
    'финанс(?:ы|овый)?[\s_]министерство',)
syn_tp.handlers.extend(
    ReHandler.fromdict(
        dict.fromkeys(minfin_names, 'минфин'),
        flags=98
    )
)

# отдельные случаи
syn_tp.create_handler(
    ReHandler,
    regexp=r'это(?=$)',
    sub='определение',
    flags=98,
    sep_left=True,
    sep_right=False
)
