#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 06:39:36 2017

@author: larousse
"""

# pylint: disable=missing-docstring

import copy
from typing import Iterable, Pattern
from functools import partial
from inspect import getfullargspec
from nlp.nlp_utils import try_int
import re


class TonitaParser(object):
    def __init__(self):
        self.handlers = []

    def set_handler(self, regexp, *,
                    preserve_old=False, sep_left=True, sep_right=True):
        if not isinstance(regexp, Pattern):
            if sep_left and not regexp.startswith(r'(?<!\w)'):
                regexp = r'(?<!\w)' + regexp
            elif sep_right and not regexp.endswith(r'(?!\w)'):
                regexp = regexp + r'(?!\w)'
            regexp = re.compile(regexp, re.IGNORECASE)

        def _decorate(sub):
            if not callable(sub):
                if preserve_old:
                    _repl = r'\g<0> {}'.format(sub)
                else:
                    _repl = str(sub)
            else:
                _repl = partial(_func_with_match, sub)
                if preserve_old:
                    _repl = TonitaParser.set_handler.repl_maker(_repl)

            _wrapped = partial(regexp.sub, _repl)
            _wrapped.num = len(self.handlers)

            self.handlers.append(_wrapped)
            return _wrapped

        return _decorate

    set_handler.repl_maker = lambda r: lambda m: ' '.join((m.group(0), r(m)))

    def add_h(self, regexp, sub='', **kwargs):
        self.set_handler(regexp, **kwargs)(sub)

    def add_dict(self, hdict, **kwargs):
        for origin, target in hdict.items():
            self.add_h(origin, target, **kwargs)

    def __add__(self, other):
        if other is None or isinstance(other, TonitaParser):
            hnew = copy.deepcopy(getattr(other, 'handlers', []))
            for handler in hnew:
                handler.num += len(self.handlers)
            res = TonitaParser()
            res.handlers = copy.deepcopy(self.handlers) + hnew
            return res
        raise TypeError

    def __radd__(self, other):
        if other is None:
            return self + None
        elif isinstance(other, TonitaParser):
            return other.__add__(self)
        raise TypeError

    def process(self, text):
        if isinstance(text, str):
            res = text
        elif isinstance(text, Iterable):
            res = ' '.join(text)
        else:
            res = str(text)

        for handler in self.handlers:
            res = handler(res)

        if not isinstance(text, str) and isinstance(text, Iterable):
            return res.split(' ')
        return res

    __call__ = process

    @staticmethod
    def from_dict(hdict, **kwargs):
        res = TonitaParser()
        res.add_dict(hdict, **kwargs)
        return res

    @staticmethod
    def once(text='', regexp=None, sub=None, *, asdict=None, **kwargs):
        hdict = {}
        if isinstance(asdict, dict):
            hdict.update(asdict)
        if None not in (regexp, sub):
            hdict[regexp] = sub
        return TonitaParser.from_dict(hdict, **kwargs)(text)


def _func_with_match(func, match):
    asp = getfullargspec(func)

    kwargs = {}
    if asp.kwonlydefaults is not None:
        kwargs.update(asp.kwonlydefaults)
    if asp.defaults:
        kwargs.update(zip(reversed(asp.args), reversed(asp.defaults)))

    all_args = set(asp.args + asp.kwonlyargs)

    mgdict = match.groupdict()
    mgdict = {k: v for k, v in mgdict.items() if v is not None}
    mgdict.update(
        {k + '_': v
         for k, v in mgdict.items() if k + '_' in all_args})
    kwargs.update(mgdict, match=match, full=match.group(0))
    kwargs.update(dict.fromkeys(all_args.difference(kwargs), None))
    if asp.varkw is None:
        kwargs = {k: v for k, v in kwargs.items() if k in all_args}

    args = [kwargs.pop(a, None) for a in asp.args]
    if asp.varargs is not None:
        args.extend([match.group(0)] + list(match.groups()))

    kwargs = {k: try_int(v) for k, v in kwargs.items()}
    args = [try_int(a) for a in args]

    return str(func(*args, **kwargs))
