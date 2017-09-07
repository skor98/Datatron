#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  5 02:43:14 2017

@author: larousse
"""

import re

from nlp.tonita_parser import TonitaParser, ReHandler


def _process_file(filename, bnop_in=True, bnop_out=True):
    res = []
    all_words = []
    with open(filename, encoding='utf-8') as f_in:
        for line in f_in:
            if bnop_in:
                line = line.encode('cp1251').decode('koi8-r')
            line = line.strip(',\t\n ')
            if line.startswith('##'):
                res.extend(['', '', line])
            elif line.startswith('#'):
                res.extend(['', '\t' + line])
            elif line.startswith('!'):
                res.append('\t' + line)
                all_words.append(line.strip('!\t\n '))
            elif line:
                words = [w.strip('\t\n ') for w in line.split(',')]
                words = [_word_preproc(w) for w in words if w]
                words = sorted(set.union(*words))
                all_words.extend(words)
                res.append('\t' + ', '.join(words))
    res = '\n'.join(res).strip('\t\n ')
    if bnop_out:
        res = res.encode('koi8-r').decode('cp1251')
    with open(filename, 'w', encoding='utf-8') as f_out:
        f_out.write(res)
    return set(all_words)


_letternames = {'б': 'бэ', 'в': 'вэ', 'г': 'гэ', 'д': 'дэ', 'ж': 'жэ',
               'з': 'зэ', 'к': 'к(а/э)', 'л': '(эл(ь)?/лэ)', 'м': '(эм/мэ)',
               'н': '(эн/нэ)', 'п': 'пэ', 'р': '(эр/рэ)', 'с': '(эс/сэ)',
               'т': 'тэ', 'ф': '(эф/фэ)', 'х': 'х(а/э)', 'ц': 'цэ', 'ч': 'че',
               'ш': 'ш(а/э)', 'щ': 'щ(а/е)'}

_endings = {'ать': 'ан(и|ь)е', 'ять': 'ен(и|ь)е',
            'яться': 'ен(и|ь)е', 'аться': 'ан(и|ь)е',
            'ий': 'о|ость', 'ой': 'о|ость', 'ый': 'о|ость',
            'ец': 'ка', 'к': 'ца', 'инг': 'ер|ин|'}

_variations = [
    (r'\g<l>\g<l>?', r'(?P<l>[йцкнгшщзхфвпрлджчсмтб])(?P=l)(?!\?)'),
    (lambda ab: '({}|{})'.format(ab, ''.join(_letternames.get(l, l) for l in ab)), r'<(?P<ab>\w+)>'),
    ('(е/ё)', 'ё'),
    (lambda end: '({}|{})'.format(end, _endings.get(end, end)), '_(?P<end>[^_]*?)$'),
]
_variations = TonitaParser(handlers=[
    ReHandler(*var, flags=98, sep_left=False, sep_right=False)
    for var in _variations
])

_regexp_unifier = [
    (r'|)', r'\)\?'),
    (r'(\1|)', r'(.)\?'),
    ('|', '/'),
]
_regexp_unifier = TonitaParser(handlers=[
    ReHandler(*ru, flags=98, sep_left=False, sep_right=False)
    for ru in _regexp_unifier
])

_preparser = _variations + _regexp_unifier

_multigroup_re = re.compile(r'\(([^()]*?)\)')

def _word_preproc(word):
    if len(word) >= 5 and word != 'комми':
        word = _preparser(word)
    else:
        word = _preparser[1:](word)

    def _handle_re(re_word):
        parts = _multigroup_re.split(re_word)
        if len(parts) == 1:
            return set(parts)
        res = ['']
        for idx, elem in enumerate(parts):
            if idx % 2 == 0:
                elem = [elem]
            else:
                elem = elem.split('|')
            res = [r + v for r in res for v in elem]
        return set.union(*(_handle_re(v) for v in res))
    return _handle_re(word)


_obs_words = _process_file('nlp/obscene.txt')

_obs_re = '(' + '|'.join(_obs_words) + ')'

obs_tp = TonitaParser()

obs_tp.create_handler(
    ReHandler,
    regexp=_obs_re,
    sub='<censored>',
    flags=98,
    sep_left=True,
    sep_right=True
)
