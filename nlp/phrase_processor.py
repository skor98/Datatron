#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 24 13:13:08 2017

@author: larousse
"""

from pymorphy2 import MorphAnalyzer

from nlp import nlp_utils


class Word(object):
    def __init__(self, parsed_word, caps='lower', noproc=False):
        self.noproc = noproc
        if noproc:
            pass
        elif isinstance(parsed_word, str):
            parsed_word = Phrase.morph.parse(parsed_word)[0]
        elif isinstance(parsed_word, Word):
            parsed_word = parsed_word.original
        self.original = parsed_word
        self.caps = caps

    @property
    def normal(self):
        return self.original.normal_form if not self.noproc else self.original

    @property
    def verbal(self):
        res = self.original.word if not self.noproc else self.original
        if self.caps == 'upper':
            return res.upper()
        if self.caps == 'title':
            return res.capitalize()
        return res.lower()

    @property
    def deriv_tags(self):
        if self.noproc:
            return set()
        return set(str(self.original.tag).split(' ')[0].split(','))

    @property
    def infl_tags(self):
        if self.noproc or ' ' not in str(self.original.tag):
            return set()
        return set(str(self.original.tag).split(' ')[1].split(','))

    @property
    def all_tags(self):
        return self.deriv_tags.union(self.infl_tags)

    def inflect(self, grammemes):
        if isinstance(grammemes, (list, tuple)):
            return self.inflect(set(grammemes))
        if isinstance(grammemes, str):
            return self.inflect(set(grammemes.split(' ')))
        grammemes = set(g for g in grammemes if g is not None)
        if self.noproc or not grammemes:
            return self.clone()
        return Word(self.original.inflect(grammemes), self.caps)

    def agrees(self, other):
        if isinstance(other, Phrase):
            if other.mainpos is None:
                return False
            return self.agrees(other.main)
        if not isinstance(other, (Phrase, Word)):
            return self.agrees(Phrase(other))
        if self.noproc or other.noproc:
            return False
        match = False
        for grammeme in ('number', 'case', 'person', 'gender', 'animacy'):
            gr_pair = (getattr(self, grammeme),
                       getattr(other, grammeme))
            if None in gr_pair:
                continue
            elif gr_pair[0] != gr_pair[1]:
                return False
            match = True
        return match

    def make_agree(self, other):
        if isinstance(other, Phrase):
            if other.mainpos is None:
                return self.clone()
            return self.make_agree(other.main)
        if not isinstance(other, (Phrase, Word)):
            return self.make_agree(Phrase(other))
        if self.noproc or other.noproc:
            return self.clone()
        res = self.clone()
        for grammeme in ('number', 'case', 'person', 'gender', 'animacy'):
            gr_pair = (getattr(res, grammeme),
                       getattr(other, grammeme))
            if gr_pair[0] != gr_pair[1] and None not in gr_pair:
                res = res.inflect(gr_pair[1])
        return res

    @property
    def can_be_main(self):
        return {'NOUN', 'nomn'} in self

    @property
    def accepts_accs(self):
        return (self.transitivity == 'tran'
                or self.POS == 'PREP'
                or self.case == 'accs')

    def clone(self):
        return Word(self.original, self.caps, self.noproc)

    def __getattr__(self, attr):
        if self.noproc:
            return None
        return getattr(self.original.tag, attr, None)

    def __contains__(self, item):
        if self.noproc:
            return False
        if isinstance(item, (list, tuple)):
            return set(item) in self
        if isinstance(item, str):
            return set(item.split(' ')) in self
        return item in self.original.tag

    def __add__(self, other):
        return Phrase(self) + Phrase(other)

    def __radd__(self, other):
        return Phrase(other) + Phrase(self)

    def __eq__(self, other):
        return str(self.original) == str(getattr(other, 'original', None))

    def __str__(self):
        return self.verbal

    def __repr__(self):
        if self.noproc:
            return '<Token "{}": not processed>'.format(self.verbal)
        if not self.infl_tags:
            return '<Word {}: {}>'.format(self.verbal, ', '.join(self.deriv_tags))
        else:
            return '<Word {}: {} ({}) in form {}>'.format(
                self.verbal, self.normal,
                ', '.join(self.deriv_tags),
                '/'.join(self.infl_tags),
            )


class Phrase(object):
    morph = MorphAnalyzer()

    def __init__(self, phrase, mainpos=None):
        if isinstance(phrase, (Phrase)):
            self.structure = phrase.structure
            self.verbal = phrase.verbal
            self.mainpos = phrase.mainpos
            return
        if isinstance(phrase, list):
            self.structure = phrase
            self.verbal = Phrase.unparse(phrase)
        elif isinstance(phrase, Word):
            self.verbal = phrase.verbal
            self.structure = [phrase]
        else:
            self.verbal = str(phrase)
            self.structure = Phrase.parse(phrase)
        if mainpos is not None:
            self.mainpos = mainpos
        else:
            main_finder = [n for n, w in enumerate(self.structure) if w.can_be_main]
            self.mainpos = main_finder[0] if main_finder else None

    @property
    def main(self):
        return None if self.mainpos is None else self[self.mainpos]

    def inflect(self, grammemes):
        if self.mainpos is None:
            return self.clone()
        newmain = self.main.inflect(grammemes)
        return Phrase(
            [w.make_agree(newmain) if w.agrees(self.main) else w
             for w in self.structure],
            self.mainpos
        )

    def clone(self):
        return Phrase([w.clone() for w in self.structure], self.mainpos)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.structure[key]
        res = [w for w in self.structure if w.verbal == key]
        return res[0] if res else None

    def __contains__(self, item):
        if not isinstance(item, Phrase):
            return Phrase(item) in self
        if not item:
            return False
        counter = 0
        for word in self:
            if word == item[counter]:
                counter += 1
                if counter >= len(item):
                    return True
            else:
                counter = 0
        return False

    def __add__(self, other):
        if not isinstance(other, Phrase):
            return self + Phrase(other)
        return Phrase(self.structure + other.structure)

    def __radd__(self, other):
        return Phrase(other) + self

    def __len__(self):
        return len(self.structure)

    def __iter__(self):
        return iter(self.structure)

    def __str__(self):
        return self.verbal

    def __repr__(self):
        return '<Phrase {}: [{}]>'.format(
            self.verbal,
            '; '.join([repr(w) if n != self.mainpos else repr(w) + '(MAIN)'
                       for n, w in enumerate(self.structure)])
        )

    def __bool__(self):
        return bool(self.structure)

    @staticmethod
    def parse(phrase: str):
        res = []
        phrase = nlp_utils.advanced_tokenizer(phrase, True, True)
        for word in phrase:
            if word.isupper():
                caps = 'upper'
            elif word.istitle():
                caps = 'title'
            else:
                caps = 'lower'
            parsed = Phrase.morph.parse(word)
            if (not parsed or
               {'PNCT', 'LATN', 'NUMB', 'UNKN'}.intersection(parsed[0].tag._grammemes_tuple)):
                res.append(Word(word, caps, noproc=True))
            elif parsed[0].tag.case == 'accs' and not (res and res[-1].accepts_accs):
                options = [p for p in parsed if p.tag.case != 'accs']
                res.append(Word(options[0] if options else parsed[0], caps))
            else:
                res.append(Word(parsed[0], caps))
        return res

    @staticmethod
    def unparse(phrase):
        return ''.join(w.verbal for w in phrase)
