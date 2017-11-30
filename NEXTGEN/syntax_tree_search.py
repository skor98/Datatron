#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 20 08:37:09 2017

@author: larousse
"""

from syntax_tree_maker import SyntaxWizard


def get_text_contents(text, dictionary, wizard=None, apikey=None):
    if wizard is None:
        wizard = SyntaxWizard(apikey)
    tree = wizard.make_syntax_tree(text)
    return walk_tree(tree, dictionary)
    

def walk_tree(tree, dictionary, path=[]):
    path = path.copy()
    node = tree[tree.root]
    if node.data.syncat == 'S' and 'case' in node.data.gram:
        path.append('**' + node.data.gram['case'][:3])

    cat = search_node(node, path, dictionary)
    tag = node.tag

    if cat is None:
        while path and path[-1].startswith('*'):
            path.pop()
    elif cat == 'C':
        step = '*' + node.data.lemma
        if node.data.syncat == 'LINKER':
            step = '*' + step
        path.append(step)
    else:
        path.append(cat)

    res = {}

    for child_id in node.fpointer:
        subres = walk_tree(tree.subtree(child_id), dictionary, path=path)
        if None in subres:
            if cat == 'C':
                cat = None
            if child_id > node.identifier:
                tag = ' '.join((tag, subres.pop(None)[0]))
            else:
                tag = ' '.join((subres.pop(None)[0], tag))
        for key, val in subres.items():
            if key not in res:
                res[key] = []
            res[key].extend(val)

    if cat not in res:
        res[cat] = []
    res[cat].append(tag)
    if 'C' in res:
        res.pop('C')
    return res


def search_node(node, path, dictionary):
    if (node.data.syncat == 'LINKER' or 
            node.data.lemma in dictionary.get('constants', [])):
        return 'C'
    cur_dict = dictionary.get('pathfinder', {})
    for step in path[::-1]:
        if step in cur_dict:
            cur_dict = cur_dict[step]
        else:
            break
    return cur_dict.get('res', None)
