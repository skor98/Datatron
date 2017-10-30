#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  7 10:08:44 2017

@author: larousse
"""

import re

from nlp.tonita_parser import TonitaParser, ReHandler


def process_file(filename, bnop_in=True, bnop_out=True):
    with open(filename, encoding='utf-8') as f_in:
        lines = [line.strip(',\t\n ') for line in f_in]
    if bnop_in:
        lines = [line.encode('cp1251').decode('koi8-r') for line in lines]
    regular = set(line.strip('!\t ') for line in lines if line.startswith('!'))
    comp_regs = [re.compile(r'(^|\s){}($|\s)'.format(r), flags=34)
                 for r in regular]

    output = []
    all_words = set()
    for line in lines:
        if line.startswith('##'):
            output.extend(['', '', line])
        elif line.startswith('#'):
            output.extend(['', '\t' + line])
        elif line.startswith('!'):
            output.append('\t' + line)
        elif line:
            words = [w.strip('\t\n ') for w in line.split(',')]
            words = [_word_preproc(w) for w in words if w]
            words = sorted(set.union(*words))
            words = [w for w in words
                     if (all(r.search(w) is None for r in comp_regs) and
                         w not in all_words)]
            all_words.update(words)
            output.append('\t' + ', '.join(words))
    output = '\n'.join(output).strip('\t\n ')
    if bnop_out:
        output = output.encode('koi8-r').decode('cp1251')
    with open(filename, 'w', encoding='utf-8') as f_out:
        f_out.write(output)
    return regular, all_words


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
    (lambda ab: '({}|{}|{})'.format(ab,
                                    ''.join(_letternames.get(l, l)
                                            for l in ab),
                                    ' '.join(_letternames.get(l, l) for l in ab)), r'<(?P<ab>\w+)>'),
    ('(е/ё)', 'ё'),
    (lambda end: '({}|{})'.format(end, _endings.get(
        end, end)), '_(?P<end>[^_]*?)(?=$|\)|\s)'),
    (' ', '  +')
]
_variations = TonitaParser(handlers=[
    ReHandler(*var, flags=34, sep_left=False, sep_right=False)
    for var in _variations
])

_regexp_unifier = [
    (r'|)', r'\)\?'),
    (r'(\1|)', r'(.)\?'),
    ('|', '/'),
]
_regexp_unifier = TonitaParser(handlers=[
    ReHandler(*ru, flags=34, sep_left=False, sep_right=False)
    for ru in _regexp_unifier
])

_preparser = _variations + _regexp_unifier

_multigroup_re = re.compile(r'\(([^()]*?)\)')


def _word_preproc(word):
    word = _preparser(word)

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
