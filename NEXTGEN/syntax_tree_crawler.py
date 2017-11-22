#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 20 08:37:09 2017

@author: larousse
"""

import requests
import treelib

from collections import namedtuple

APIKEY = 'd0f1403509105fa81976f42834e5bf9b7da2d18b'

def get_ling_data(text, methods):
    url = 'http://api.ispras.ru/texterra/v1/nlp'
    headers = {'Accept': 'application/json'}
    params = {'apikey': APIKEY, 'targetType': methods}
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


Word = namedtuple('Word', ['text', 'lemma', 'gram'])


def make_syntax_tree(text):
    ling_data = get_ling_data(text, ('pos-token', 'lemma', 'syntax-relation'))
    
    tree = treelib.Tree()
    tree.create_node(
        tag='#',
        identifier=-1, 
        data=Word(text=None, lemma='#', gram={'POS': 'UTIL'})
    )

    for word in ling_data:
        idx = word['start']
        pos = word['pos-token'].get('tag', 'UNDEF')
        if pos == 'PUNCT':
            continue
        
        gram = {'POS': pos}
        
        parent_bounds = word['syntax-relation'].get('parent')
        if parent_bounds is None:
            parent_id = -1
        else:
            parent_id = parent_bounds['start']

        if not tree.contains(parent_id):
            tree.create_node(identifier=parent_id, parent=-1)
        
        if pos == 'S':
            cases = [gram['tag']
                     for gram in word['pos-token']['characters']
                     if gram['type'] == 'case']
            if cases:
                gram['case'] = cases[0][:3]
        
        if tree.contains(idx):
            tree.move_node(idx, parent_id)
        else:
            tree.create_node(identifier=idx, parent=parent_id)
    
        tree[idx].tag = word['text'].lower()
        tree[idx].data = Word(
            text=word['text'],
            lemma=word['lemma'],
            gram=gram,
        )
    
    return tree


def walk_tree(tree, dictionary, *, path=[]):
    path = path.copy()
    node = tree[tree.root]
    if 'case' in node.data.gram:
        path.append('*' + node.data.gram['case'])    

    cat = search_node(node, path, dictionary)
    val = node.tag

    if cat is None:
        while path and path[-1].startswith('*'):
            if val != node.tag:
                val = node.tag
            path.pop()
    elif cat == 'C':
        path.append('*' + node.data.lemma)
    else:
        path.append(cat)

    res = {}

    for child_id in node.fpointer:
        subres = walk_tree(tree.subtree(child_id), dictionary, path=path)
        if None in subres:
            if cat == 'C':
                cat = None
            if child_id > node.identifier:
                val = ' '.join((val, subres.pop(None)))
            else:
                val = ' '.join((subres.pop(None), val))
        res.update(subres)

    res[cat] = val
    if 'C' in res:
        res.pop('C')
    return res


def search_node(node, path, dictionary):
    lemma = node.data.lemma
    if lemma in dictionary.get('constants', []):
        return 'C'
    cur_dict = dictionary.get('pathfinder', {})
    for step in path[::-1]:
        if step in cur_dict:
            cur_dict = cur_dict[step]
        else:
            break
    return cur_dict.get('res', None)
