#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 06:39:36 2017

@author: larousse
"""

# pylint: disable=missing-docstring

from collections import Iterable
from functools import partial
from inspect import getfullargspec
import re


class TonitaParser(object):
    def __init__(self, sub_dict=None):
        self.actions = []
        if sub_dict is not None:
            self.add_many(sub_dict)

    def re_handler(self, regexp, preserve_old=False, sep_left=True, sep_right=True):
        if not isinstance(regexp, str) and hasattr(regexp, 'pattern'):
            regexp = regexp.pattern
        if sep_left and not regexp.startswith(r'(?<!\w)'):
            regexp = r'(?<!\w)' + regexp
        if sep_right and not regexp.endswith(r'(?!\w)'):
            regexp = regexp + r'(?!\w)'
        cond_re = re.compile(regexp, re.IGNORECASE)
        def _decorate(sub):
            if not callable(sub):
                if not isinstance(sub, str):
                    sub = str(sub)
                if preserve_old:
                    _repl = ' '.join([r'\g<0>' , sub])
                else:
                    _repl = sub
            else:
                _repl = partial(_func_with_match, sub)
                if preserve_old:
                    _repl = lambda m: ' '.join([m.group(0), _repl(m)])

            _wrapped = partial(cond_re.sub, _repl)
            _wrapped.regexp = cond_re
            _wrapped.num = len(self.actions)

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



def _func_with_match(func, match):
    asp = getfullargspec(func)

    kwargs = {}
    if asp.kwonlydefaults is not None:
        kwargs.update(asp.kwonlydefaults)
    if asp.defaults:
        kwargs.update(zip(reversed(asp.args), reversed(asp.defaults)))

    all_args = set(asp.args + asp.kwonlyargs)

    mgdict = match.groupdict()
    mgdict.update({k + '_': v for k, v in mgdict.items() if k + '_' in all_args})
    kwargs.update(mgdict, match=match, full=match.group(0))
    kwargs.update(dict.fromkeys(all_args.difference(kwargs.keys()), None))
    if asp.varkw is None:
        kwargs = {k: v for k, v in kwargs.items() if k in all_args}

    kwargs = {k: int(v) for k, v in kwargs.items() if isinstance(v, str) and v.isnumeric()}

    args = [kwargs.pop(a, None) for a in asp.args]
    if asp.varargs is not None:
        args.extend([match.group(0)] + list(match.groups()))

    args = [int(a) if a.isnumeric() else a for a in args]

    return str(func(*args, **kwargs))
