#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 15 15:07:15 2017

@author: larousse
"""

from core.tonita_parser import TonitaParser

syn_tp = TonitaParser()

syn_tp.add_many({
    'россия': 'РФ',
    'российский федерация': 'РФ',
    'россиюшка': 'РФ',
    'рашка': 'РФ',
    'русь': 'РФ',
    'наш страна': 'РФ',
    'держава': 'РФ',
})

syn_tp.add_many({
    'министерство финансы': 'Минфин',
    'мф': 'Минфин',
})

syn_tp.add_many({
    r'(?<!\w)гос\W': 'государственный ',
    r'(?<!\w)соц\W': 'социальный ',
    r'(?<!\w)нац\W': 'национальный ',
    r'(?<!\w)фед\W': 'федеральный '
}, separate_word=False)
