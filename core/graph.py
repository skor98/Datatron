#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Определение структуры деревы решений
"""

import networkx as nx
import core.cube_filters as cfilter
from itertools import islice


class Graph(nx.DiGraph):
    def __init__(self, num_of_variants=10):
        super().__init__()
        self._define_nodes()
        self._define_edges()
        self.gr_answer_combinations = self._k_shortest_paths(0, 16, num_of_variants)

    def _define_nodes(self):
        """Определение вершин"""

        self.add_node(0, function=cfilter.tree_start)
        self.add_node(1, function=cfilter.select_first_cube)
        self.add_node(2, function=cfilter.select_second_cube)
        self.add_node(3, function=cfilter.select_third_cube)
        self.add_node(4, function=cfilter.select_forth_cube)
        self.add_node(5, function=cfilter.ignore_current_year)
        self.add_node(6, function=cfilter.not_ignore_current_year)
        self.add_node(7, function=cfilter.define_year_privilege_over_cube)
        self.add_node(8, function=cfilter.define_cube_privilege_over_year)
        self.add_node(9, function=cfilter.define_territory_privilege_over_cube)
        self.add_node(10, function=cfilter.define_cube_privilege_over_territory)
        self.add_node(11, function=cfilter.form_members_in_hierachy_by_score)
        self.add_node(12, function=cfilter.all_members_from_first_hierarchy_level)
        self.add_node(13, function=cfilter.all_members_from_second_hierarchy_level)
        self.add_node(14, function=cfilter.all_members_from_third_hierarchy_level)
        self.add_node(15, function=cfilter.all_members_from_forth_hierarchy_level)
        self.add_node(16, function=cfilter.tree_end)

    def _define_edges(self):
        """Определение связей между узлами"""

        WEIGHTS = {
            'w0.1': 5, 'w0.2': 15, 'w0.3': 30, 'w0.4': 50,
            'w1.5': 30, 'w1.6': 70,
            'w2.5': 30, 'w2.6': 70,
            'w3.5': 30, 'w3.6': 70,
            'w4.5': 30, 'w4.6': 70,
            'w5.7': 30, 'w5.8': 70,
            'w6.7': 30, 'w6.8': 70,
            'w7.9': 45, 'w7.10': 55,
            'w8.9': 45, 'w8.10': 55,
            'w9.11': 0,
            'w10.11': 0,
            'w11.12': 5, 'w11.13': 15, 'w11.14': 30, 'w11.15': 50,
            'w12.16': 0,
            'w13.16': 0,
            'w14.16': 0,
            'w15.16': 0,
        }

        self.add_weighted_edges_from([
            (0, 1, WEIGHTS['w0.1']), (0, 2, WEIGHTS['w0.2']), (0, 3, WEIGHTS['w0.3']), (0, 4, WEIGHTS['w0.4']),
            (1, 5, WEIGHTS['w1.5']), (1, 6, WEIGHTS['w1.6']),
            (2, 5, WEIGHTS['w2.5']), (2, 6, WEIGHTS['w2.6']),
            (3, 5, WEIGHTS['w3.5']), (3, 6, WEIGHTS['w3.6']),
            (4, 5, WEIGHTS['w4.5']), (4, 6, WEIGHTS['w4.6']),
            (5, 7, WEIGHTS['w5.7']), (5, 8, WEIGHTS['w5.8']),
            (6, 7, WEIGHTS['w6.7']), (6, 8, WEIGHTS['w6.8']),
            (7, 9, WEIGHTS['w7.9']), (7, 10, WEIGHTS['w7.10']),
            (9, 11, WEIGHTS['w9.11']),
            (10, 11, WEIGHTS['w10.11']),
            (11, 12, WEIGHTS['w11.12']), (11, 13, WEIGHTS['w11.13']),
            (11, 14, WEIGHTS['w11.14']), (11, 15, WEIGHTS['w11.15']),
            (12, 16, WEIGHTS['w12.16']),
            (13, 16, WEIGHTS['w13.16']),
            (14, 16, WEIGHTS['w14.16']),
            (15, 16, WEIGHTS['w15.16']),
        ])

    def _k_shortest_paths(self, source: int, target: int, k: int):
        """k наиболее коротких путей от source-node до target-node"""

        return islice(nx.shortest_simple_paths(self, source, target, weight='weight'), k)


g = Graph()
print(list(g.gr_answer_combinations))