#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 15 15:07:15 2017

@author: larousse
"""

from nlp.tonita_parser import TonitaParser

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
syn_tp.add_dict(contr, sep_left=True, sep_right=False)

# разные варианты указания на Россию
russland_names = (
    'россия',
    'российский федерация',
    'россиюшка',
    'рашка',
    'русь',
    'наш страна',
    'этот? страна',
    'держава', )
syn_tp.add_dict(dict.fromkeys(russland_names, 'РФ'))

# разные варианты указания на Минфин
minfin_names = (
    'мф',
    'министерство финанс(?:ы|овый)?',
    'финанс(?:ы|овый)? министерство', )
syn_tp.add_dict(dict.fromkeys(minfin_names, 'минфин'))

# отдельные случаи
syn_tp.add_dict({'это(?=$)': 'определение'}, sep_left=True, sep_right=False)
