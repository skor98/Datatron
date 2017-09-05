#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  5 02:43:14 2017

@author: larousse
"""

from nlp.tonita_parser import TonitaParser, ReHandler

obs_tp = TonitaParser()

obs_words = []
with open('nlp/obscene.txt', encoding='utf-8') as f:
    for line in f:
        line = line.encode('cp1251').decode('koi8-r').strip('\n\t ')
        if not line or line.startswith('#') or line.startswith('!'):
            continue
        obs_words.extend(line.split(', '))
        
obs_re = '(' + '|'.join(obs_words) + ')'

obs_tp.create_handler(
    ReHandler,
    regexp=obs_re,
    sub='<censored>',
    flags=98,
    sep_left=True,
    sep_right=True
)