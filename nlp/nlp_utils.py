from collections import OrderedDict
import itertools
import re

import nltk


class TokenTypes(object):

    _typedict = OrderedDict((
        ('null', re.compile('^$')),
        ('whitespace', re.compile(r'([\s_]+)', re.DOTALL)),
        ('punctuation', re.compile(r'(\W+)')),
        ('numeric', re.compile(r'([+-]?\d+)')),
        ('complex_num', re.compile(r'([\d\W]+)')),
        ('word', re.compile(r'([a-zа-яё]+)', re.IGNORECASE)),
        ('distorted_word', re.compile(r'([^\s_]+)', re.IGNORECASE)),
        ('wordset', re.compile(r'((?:[a-zа-яё]+(?:[\s_]|$)+)+)', re.IGNORECASE)),
        ('text', re.compile(r'((?:(?:(?:\d|[^\s\w])*|[^\s\w_]*[a-zа-яё]+[^\s\w]*)(?:[\s_]|$)+)+)', re.IGNORECASE)),
        ('unknown', re.compile(r'.*', re.DOTALL))
    ))

    @staticmethod
    def type_re(type_):
        return TokenTypes._typedict.get(type_, 'unknown')

    @staticmethod
    def _typecheck_basic(token, type_):
        return TokenTypes.type_re(type_).fullmatch(token) is not None

    @staticmethod
    def find_type(token):
        for tname in TokenTypes._typedict.keys():
            if TokenTypes._typecheck_basic(token, tname):
                return tname
        return 'unknown'

    @staticmethod
    def in_type(token, typeset):
        if isinstance(typeset, str):
            typeset = [typeset]
        else:
            typeset = list(set(typeset))

        for tname in TokenTypes._typedict.keys():
            if tname in typeset:
                typeset.remove(tname)
                if TokenTypes._typecheck_basic(token, tname):
                    return True
                elif not typeset:
                    return False
            elif TokenTypes._typecheck_basic(token, tname):
                return False
        return 'unknown' in typeset



def re_strip(regexp, text, flags=0, only_text=True, sides='lr'):
    if isinstance(regexp, str):
        regexp = re.compile(regexp)
    elif not hasattr(regexp, 'match'):
        regexp = re_strip.default_re

    res = []

    if 'l' in sides:
        left = regexp.match(text, flags)
        if left is not None:
            text = text[left.end():]
            left = left.groups()
        res = [left]

    if 'r' in sides:
        revtext = text[::-1]
        right = regexp.match(revtext, flags)
        if right is not None:
            text = text[:-right.end()]
            right = tuple(reversed([g[::-1] for g in right.groups()]))
        res.extend((text, right))
    else:
        res.append(text)

    if only_text:
        return text
    return res


re_strip.default_re = re.compile(r'([\W_]+)', re.DOTALL)


def clean_double_spaces(text):
    return clean_double_spaces.regexp.sub(' ', text)

clean_double_spaces.regexp = re.compile(r'[\s_]+', re.DOTALL)


def try_int(obj):
    if not isinstance(obj, str) or not TokenTypes.in_type(obj, 'numeric'):
        return obj
    return int(obj)


def advanced_tokenizer(text: str, with_punct=False, with_spaces=False):
    tokens = TokenTypes.type_re('whitespace').split(text)

    for idx, token in enumerate(tokens):
        if TokenTypes.in_type(token, 'whitespace'):
            if not with_spaces:
                token = None
            tokens[idx] = (token,)
            continue
        if TokenTypes.in_type(token, 'punctuation'):
            if not with_punct:
                token = None
            tokens[idx] = (token,)
            continue
        if TokenTypes.in_type(token, ('null', 'word')):
            tokens[idx] = (token,)
            continue

        newtokens = nltk.word_tokenize(token)
        for newidx, newtoken in enumerate(newtokens):
            newtoken = re_strip(TokenTypes.type_re('punctuation'), newtoken, only_text=False)
            if not with_punct:
                newtoken = (newtoken[1],)
            else:
                newtoken = [i[0] if isinstance(i, tuple) else i for i in newtoken]
            newtokens[newidx] = newtoken
        tokens[idx] = itertools.chain.from_iterable(newtokens)

    return list(filter(None, itertools.chain.from_iterable(tokens)))

