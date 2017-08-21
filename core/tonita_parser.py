#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 06:39:36 2017

@author: larousse
"""

# pylint: disable=missing-docstring

import re
from functools import partial
from collections import Iterable


class TonitaParser(object):
    def __init__(self, sub_dict=None):
        self.actions = []
        if sub_dict is not None:
            self.add_many_subs(sub_dict)

    def re_handler(self, regexp, preserve_old=False, separate_word=True):
        if separate_word:
            regexp = r'(?<!\w){}(?!\w)'.format(regexp)
        cond_re = re.compile(regexp, re.IGNORECASE)
        def _decorate(func):
            if preserve_old:
                def _newfunc(m): return ' '.join([m.group(0), str(func(m))])
            else:
                def _newfunc(m): return str(func(m))
            _wrapped = partial(cond_re.sub, _newfunc)
            self.actions.append(_wrapped)
            return _wrapped

        return _decorate
    
    def add_simple(self, regexp, sub='', preserve_old=False):
        self.re_handler(regexp, preserve_old)(func=lambda m: sub)
        
    def add_many(self, sub_dict, preserve_old=False):
        for origin in sub_dict:
            self.add_simple(origin, sub_dict[origin], preserve_old)

    def __add__(self, other):
        if other is None:
            other = TonitaParser()
        if hasattr(other, 'actions'):
            res = TonitaParser()
            res.actions = self.actions + other.actions
            return res
        raise TypeError

    def __radd__(self, other):
        if other is None:
            other = TonitaParser()
        if hasattr(other, 'actions'):
            return other.__add__(self)
        raise TypeError

    def __call__(self, text):
        if isinstance(text, str):
            res = text
        elif isinstance(text, Iterable):
            res = ' '.join(text)
        else:
            res = str(text)

        for act in self.actions:
            res = act(res)

        if not isinstance(text, str) and isinstance(text, Iterable):
            return res.split(' ')
        return res
