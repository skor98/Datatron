#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 23 02:07:33 2017

@author: larousse
"""

from syntax_tree_crawler import make_syntax_tree, walk_tree

EXAMPLE_DICTIONARY = {
    'constants': ['#', 'бюджет', 'в', 'год', 'и', 'с'],
    'pathfinder': {
        '*Gen': {
            '*бюджет': {'res': 'TERRITORY'},
            '*с': {
                'DOMAIN': {'res': 'SOURCE'}
            }
        },
        '*Nom': {
            '*#': {'res': 'DOMAIN'}
        },
        '*бюджет': {'res': 'BGLEVEL'},
        '*год': {'res': 'YEAR'}
    }
}

EXAMPLE_PHRASE = 'Доходы краевого бюджета Краснодарского края с административных платежей и сборов в 2015 году.'


if __name__ == '__main__':
    example_tree = make_syntax_tree(EXAMPLE_PHRASE)
    example_result = walk_tree(example_tree, EXAMPLE_DICTIONARY)
    print(example_result)
