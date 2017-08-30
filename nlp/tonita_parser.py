#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 06:39:36 2017

@author: larousse
"""

# pylint: disable=missing-docstring

from typing import Iterable
from functools import partial
from inspect import getfullargspec
from nlp.nlp_utils import try_int
import re


class TonitaHandler(object):
    def __init__(self, process=None, check=None):
        self.process = process
        self.check = check


class ReplaceHandler(TonitaHandler):
    def __init__(self, substr, repl):
        super().__init__(process=lambda text: text.replace(substr, repl),
                         check=lambda text: substr in text)

    @staticmethod
    def fromdict(repl_dict):
        return [ReplaceHandler(k, v) for k, v in repl_dict.items()]


class ReHandler(TonitaHandler):
    def __init__(self, sub, regexp, *,
                 flags=0,
                 remove_none=False,
                 preserve=False,
                 sep_left=True,
                 sep_right=True):
        if isinstance(regexp, str):
            if sep_left:
                regexp = r'(?<![\w-])' + regexp
            if sep_right:
                regexp += r'(?![\w-])'
            regexp = re.compile(regexp, flags)
        self.regexp = regexp

        if isinstance(sub, str):
            def repl(m): return m.expand(sub)
        else:
            repl = ReHandler.args_from_match(sub, remove_none)

        if preserve:
            self.repl = lambda m: ' '.join([m.group(0), str(repl(m))])
        else:
            self.repl = lambda m: str(repl(m))

        def check(text): return regexp.search(text) is not None
        process = partial(regexp.sub, self.repl)

        super().__init__(process=process, check=check)

    @staticmethod
    def fromdict(repl_dict, **kwargs):
        return [ReHandler(sub=v, regexp=k, **kwargs)
                for k, v in repl_dict.items()]

    @staticmethod
    def args_from_match(func, remove_none=False):
        asp = getfullargspec(func)
        argnames = asp.args + asp.kwonlyargs

        def _wrapped(match):
            kwargs = match.groupdict()
            kwargs.update({'match': match, 'full': match.group(0)})
            for key in list(kwargs.keys()):
                val = kwargs.pop(key)
                if (not (remove_none and val is None) and
                        not (asp.varkw is None and key not in argnames)):
                    kwargs[key] = try_int(val)
            return func(**kwargs)

        return _wrapped


class TonitaParser(object):
    def __init__(self, *, handlers=None):
        self.handlers = handlers
        if handlers is None:
            self.handlers = []

    def create_handler(self, htype=TonitaHandler, *args, **kwargs):
        self.handlers.append(htype(*args, **kwargs))

    def set_handler(self, htype=TonitaHandler, *args, **kwargs):
        def _decorate(func):
            self.handlers.append(htype(func, *args, **kwargs))
            return func
        return _decorate

    def __add__(self, other):
        if other is None:
            return self
        if isinstance(other, TonitaHandler):
            return self + TonitaParser(handlers=[other])
        if isinstance(other, TonitaParser):
            return TonitaParser(handlers=self.handlers + other.handlers)
        raise TypeError

    def __radd__(self, other):
        if other is None:
            return self
        if isinstance(other, TonitaHandler):
            return TonitaParser(handlers=[other]) + self
        if isinstance(other, TonitaParser):
            return TonitaParser(handlers=other.handlers + self.handlers)
        raise TypeError

    def process(self, text):
        if isinstance(text, str):
            res = text
        elif isinstance(text, Iterable):
            res = ' '.join(text)
        else:
            res = str(text)

        for handler in self.handlers:
            if ((handler.check is None or handler.check(res)) and
                    handler.process is not None):
                res = str(handler.process(res))

        if not isinstance(text, str) and isinstance(text, Iterable):
            return res.split(' ')
        return res

    __call__ = process
