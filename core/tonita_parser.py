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
        def _decorate(sub):
            if not callable(sub):
                if not isinstance(sub, str):
                    sub = str(sub)
                if preserve_old:
                    _repl = ' '.join([r'\g<0>' , sub])
                else:
                    _repl = sub
            elif preserve_old:
                def _repl(m): return ' '.join([m.group(0), str(sub(m))])
            else:
                def _repl(m): return str(sub(m))
            _wrapped = partial(cond_re.sub, _repl)
            self.actions.append(_wrapped)
            return _wrapped
        return _decorate
    
    def add_simple(self, regexp, sub='', *args, **kwargs):        
        self.re_handler(regexp, *args, **kwargs)(sub)
        
    def add_many(self, sub_dict, *args, **kwargs):
        for origin in sub_dict:
            self.add_simple(origin, sub_dict[origin], *args, **kwargs)

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
