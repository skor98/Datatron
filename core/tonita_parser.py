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
        cond_re = re.compile(r'(?<!\w)' + regexp + r'(?!\w)')
        def _decorate(func):
            def _wrapped(text):
                match = cond_re.search(text)
                if match is None:
                    return text
                update = func(match)
                if preserve_old:
                    return ' '.join([text, update])
                return cond_re.sub(update, text)
            self.actions.append(_wrapped)
            return _wrapped
        return _decorate
    
    def add_simple_sub(self, regexp, sub=''):
        self.re_handler(regexp, False)(lambda match: sub)
        
    def add_many_subs(self, sub_dict):
        for origin in sub_dict:
            self.add_simple_sub(origin, sub_dict[origin])

    def __add__(self, other):
        res = TonitaParser()
        res.actions = self.actions + other.actions
        return res

    def __call__(self, text):
        res = text
        for act in self.actions:
            res = act(res)
        return res
