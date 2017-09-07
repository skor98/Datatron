#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  5 02:43:14 2017

@author: larousse
"""

from nlp.obscene_preprocessor import process_file
from nlp.tonita_parser import TonitaParser, ReHandler, ReplaceHandler


obs_tp = TonitaParser()

_obs_regs, _obs_words = [dict.fromkeys(o, '<censored>') for o in process_file('nlp/obscene.txt')]

obs_tp.handlers.extend(ReplaceHandler.fromdict(_obs_words, sep_left=True, sep_right=True))
obs_tp.handlers.extend(ReHandler.fromdict(_obs_regs, sep_left=True, sep_right=True, flags=34))

obs_tp.create_handler(
    ReHandler,
    regexp=r'<*censored>*',
    sub='<censored>',
    flags=34,
    sep_left=True,
    sep_right=True
)
