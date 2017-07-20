#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Определение структуры деревы решений
"""

import networkx as nx


def define_graph_structure():
    """Определение структуры графа"""

    dir_graph = nx.DiGraph()
    define_nodes(dir_graph)
    define_edges(dir_graph)

    return dir_graph


def define_nodes(graph: nx.DiGraph):
    """Определение вершин"""
    pass


def define_edges(graph: nx.DiGraph):
    """Определение связей между ними"""
    pass
