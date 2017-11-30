#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 30 09:15:39 2017

@author: larousse
"""

from syntax_tree_maker import SyntaxWizard


def make_dict(text, val_positions, wizard=None, apikey=None):
    if wizard is None:
        wizard = SyntaxWizard(apikey)
    paths, ids = preprocess_text(text, val_positions, wizard)
    return paths_to_dict(paths, ids)


def get_paths(tree):
    node = tree[tree.root]
    path = []
    res = []
    if node.data.syncat == 'S' and 'case' in node.data.gram:
        path.append('**' + node.data.gram['case'][:3])
    path.append(node.identifier)
    res = [(node.identifier, node.data, path[:-1])]
    for child_id in node.fpointer:
        subres = get_paths(tree.subtree(child_id))
        res.extend([(idx, data, path + subpath) for idx, data, subpath in subres])
    return sorted(res)


def preprocess_text(text, val_positions, wizard):
    tree = wizard.make_syntax_tree(text)
    paths = get_paths(tree)
    ids = {}
    for path in paths:
        value = '*' + path[1].lemma
        if path[1].syncat == 'LINKER':
            value = '*' + value
        for pos, val in val_positions.items():
            if pos[0] <= path[0] < pos[1]:
                value = val
                break
        ids[path[0]] = value
    return paths, ids


def paths_to_dict(paths, ids):
    res = {'constants': [], 'pathfinder': {}}
    for path in paths:
        value = ids[path[0]]
        if value.startswith('*'):
            if not value.startswith('**'):
                res['constants'].append(value.lstrip('*'))
            continue
        current = res['pathfinder']
        for step in path[2][::-1]:
            step_val = ids.get(step, step)
            if step_val not in current:
                current[step_val] = {}
            current = current[step_val]
            if step in ids and not ids[step][1].startswith('**'):
                break
        if step_val != value:
            current['res'] = value
    return res
