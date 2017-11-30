#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 23 02:07:33 2017

@author: larousse
"""

from syntax_tree_maker import SyntaxWizard
from syntax_tree_analyzer import make_dict
from syntax_tree_search import get_text_contents

EX_APIKEY = 'd0f1403509105fa81976f42834e5bf9b7da2d18b'
EX_BASE_PHRASE = 'Доходы краевого бюджета Краснодарского края с административных платежей и сборов в 2015 году.'
EX_TEST_PHRASE = 'Доходы бюджета Москвы в 2012 году с налогов на недвижимость.'
EX_VAL_POS = {
    (0, 6): 'DOMAIN',
    (7, 15): 'BGLEVEL',
    (24, 43): 'TERRITORY',
    (46, 80): 'SOURCE',
    (83, 87): 'YEAR',
}

if __name__ == '__main__':
    ex_wizard = SyntaxWizard(EX_APIKEY)
    ex_dict = make_dict(EX_BASE_PHRASE, EX_VAL_POS, ex_wizard)
    ex_base_res = get_text_contents(EX_BASE_PHRASE, ex_dict, ex_wizard)
    print('Base result:\n', ex_base_res, '\n')
    ex_test_res = get_text_contents(EX_TEST_PHRASE, ex_dict, ex_wizard)
    print('Test result:\n', ex_test_res, '\n')
