#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 24 13:13:08 2017

@author: larousse
"""

# pylint: disable=missing-docstring

from pymorphy2 import MorphAnalyzer

'''
SYNONYMS = [
    ('субъект', 'территория', 'регион', 'область', 'край', 'республика',
     'место', 'москва', 'санкт-петербург', 'севастополь', 'байконур',
     'Россия', 'РФ'),
    ('период', 'год', 'срок', 'время'),
]
'''


class Word(object):

    def __init__(self, parsed_word):
        if isinstance(parsed_word, str):
            parsed_word = Phrase.morph.parse(parsed_word)[0]
        elif isinstance(parsed_word, Word):
            parsed_word = parsed_word.original
        self.original = parsed_word

    @property
    def normal(self):
        return self.original.normal_form

    @property
    def verbal(self):
        return self.original.word

    @property
    def deriv_tags(self):
        return set(str(self.original.tag).split(' ')[0].split(','))

    @property
    def infl_tags(self):
        if ' ' not in str(self.original.tag):
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
        if not grammemes:
            return self.clone()
        return Word(self.original.inflect(grammemes))

    def agrees(self, other):
        if isinstance(other, Phrase):
            if other.mainpos is None:
                return False
            return self.agrees(other.main)
        if not isinstance(other, (Phrase, Word)):
            return self.agrees(Phrase(other))
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
        return (self.transitivity == 'tran' or
                self.POS == 'PREP' or
                self.case == 'accs')

    def clone(self):
        return Word(self.original)

    def __getattr__(self, attr):
        return getattr(self.original.tag, attr, None)

    def __contains__(self, item):
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

    def __neq__(self, other):
        return not self == other

    def __str__(self):
        return self.verbal

    def __repr__(self):
        if not self.infl_tags:
            return '<Word {}: {}>'.format(self.verbal, ', '.join(self.deriv_tags))

        return '<Word {}: {} ({}) in form {}>'.format(
            self.verbal, self.normal,
            ', '.join(self.deriv_tags),
            '/'.join(self.infl_tags),
        )


class Phrase(object):

    morph = MorphAnalyzer()

    def __init__(self, phrase, mainpos=None):
        if isinstance(phrase, (Phrase)):
            for key in phrase.__dict__:
                setattr(self, key, getattr(phrase, key))
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

#    def find_in(self, context):
#        if not isinstance(context, Phrase):
#            return self.find_in(Phrase(context))
#        if self.mainpos is None:
#            return None
#        main_synonyms = set(sum(
#            [group for group in SYNONYMS if self.main.normal in group],
#            (self.main.normal,)
#        ))
#        for num, word in enumerate(context):
#            if word.normal in main_synonyms:
#                return num
#        return None
#
#    def put_into(self, context, target_pos=None, preserve_number=False):
#        if not isinstance(context, Phrase):
#            return self.put_into(Phrase(context), target_pos, preserve_number)
#        if target_pos is None:
#            target_pos = self.find_in(context)
#
#        inflect_grammemes = [context[target_pos].case]
#        if not preserve_number:
#            inflect_grammemes.append(context[target_pos].number)
#        new_phrase = self.inflect(inflect_grammemes)
#
#        new_context = []
#        for num, word in enumerate(context):
#            if num == target_pos \
#               or (0 <= num-target_pos+self.mainpos < len(self)
#                       and self[num-target_pos+self.mainpos].normal == word.normal):
#                new_context.append(None)
#            elif word.agrees(context[target_pos]):
#                new_context.append(word.make_agree(new_phrase))
#            else:
#                new_context.append(word)
#
#        res = new_context[:target_pos] + new_phrase.structure + new_context[target_pos + 1:]
#        return Phrase([w for w in res if w is not None])

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
    def parse(phrase):
        res = []
        for word in phrase.strip(' \n\ufeff').split(' '):
            parsed = Phrase.morph.parse(word)
            if parsed[0].tag.case == 'accs' and not (res and res[-1].accepts_accs):
                options = [p for p in parsed if p.tag.case != 'accs']
                res.append(Word(options[0] if options else parsed[0]))
            else:
                res.append(Word(parsed[0]))
        return res

    @staticmethod
    def unparse(phrase):
        return ' '.join(w.verbal for w in phrase)
