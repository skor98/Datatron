#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 06:39:36 2017

@author: larousse
"""

# pylint: disable=missing-docstring

import re

class TonitaParser(object):
    
    def __init__(self, sub_dict=None):
        self.actions = []
        if sub_dict is not None:
            self.add_many_subs(sub_dict)

    def re_handler(self, regexp, preserve_old=False):
        cond_re = re.compile(r'(?<!\w)' + regexp + r'(?!\w)', re.IGNORECASE)
        def _decorate(func):
            def _wrapped(text):
                if preserve_old:
                    updates = [func(m) for m in cond_re.finditer(text)]
                    return ' '.join([text, updates])
                return cond_re.sub(func, text)
            self.actions.append(_wrapped)
            return _wrapped
        return _decorate
    
    def add_simple_sub(self, regexp, sub=''):
        self.re_handler(regexp, False)(sub)
        
    def add_many_subs(self, sub_dict):
        for origin in sub_dict:
            self.add_simple_sub(origin, sub_dict[origin])

    def add_simple_plus(self, regexp, new=''):
        self.re_handler(regexp, True)(new)

    def add_many_pluses(self, new_dict):
        for origin in new_dict:
            self.add_simple_plus(origin, new_dict[origin])

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
        res = text
        for act in self.actions:
            res = act(res)
        return res
