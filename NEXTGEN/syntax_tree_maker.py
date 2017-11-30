#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 30 09:18:34 2017

@author: larousse
"""

import requests
from treelib import Tree

class WordData(object):
    def __init__(self, data):
        self.text = data.get('text', '')
        self.lemma = data.get('lemma', self.text)

        gram_data = data.get('pos-token', {})
        self.pos = gram_data.get('tag', 'UNDEF')
        if self.pos.endswith('PRO'):
            self.syncat = self.pos[:-3]
        elif self.pos == 'ANUM':
            self.syncat = 'A'
        elif self.pos in ('CONJ', 'PR'):
            self.syncat = 'LINKER'
        else:
            self.syncat = self.pos

        self.gram = {gr['type']: gr['tag']
                     for gr in gram_data.get('characters', [])}


class SyntaxWizard(object):
    
    def __init__(self, apikey):
        self.apikey = apikey

    def get_ling_data(self, text, methods):
        url = 'http://api.ispras.ru/texterra/v1/nlp'
        headers = {'Accept': 'application/json'}
        params = {'apikey': self.apikey, 'targetType': methods}
        form = [{'text': text}]
        response = requests.post(url, json=form, params=params, headers=headers)
        data = response.json()[0]['annotations']
        res = []
        for method, annot in data.items():
            for idx, word_data in enumerate(annot):
                if len(res) <= idx:
                    res.append({
                        'start': word_data['start'],
                        'end': word_data['end'],
                        'text': text[word_data['start']:word_data['end']],
                    })
                res[idx].update({method: word_data['value']})
        return res    
    
    def make_syntax_tree(self, text):
        tree = Tree()
        tree.create_node(
            tag='#',
            identifier=-1, 
            data=WordData({'lemma': '#'}),
        )
        
        ling_data = self.get_ling_data(text, ('pos-token', 'lemma', 'syntax-relation'))
        for word in ling_data:
            word_object = WordData(word)
            if word_object.pos == 'PUNCT':
                continue
            idx = word['start']        
            parent_bounds = word['syntax-relation'].get('parent')
            if parent_bounds is None:
                parent_id = -1
            else:
                parent_id = parent_bounds['start']
                if not tree.contains(parent_id):
                    tree.create_node(identifier=parent_id, parent=-1)
            
            if tree.contains(idx):
                tree.move_node(idx, parent_id)
            else:
                tree.create_node(identifier=idx, parent=parent_id)
        
            tree[idx].tag = word_object.text.lower()
            tree[idx].data = word_object
    
        return tree