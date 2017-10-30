#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Определение структуры деревы решений
"""

from itertools import islice

import core.cube_filters as cf
import networkx as nx


class Graph(nx.DiGraph):
    """
    Граф, который используются для реализации нашей модели процессинга запроса
    """

    __instance = None

    @staticmethod
    def inst(num_of_variants):
        if Graph.__instance is None:
            Graph.__instance = Graph(num_of_variants)
        return Graph.__instance

    def __init__(self, num_of_variants=10):
        super().__init__()
        self._define_nodes()
        self._define_edges()
        self.tree_paths = list(self._k_shortest_paths(0, 16, num_of_variants))

    def _define_nodes(self):
        """Определение вершин"""

        graph_annotation = (
            {'name': 'Корень', 'function': cf.tree_start},
            {'name': 'Выбор 1го куба', 'function': cf.select_first_cube},
            {'name': 'Выбор 2го куба', 'function': cf.select_second_cube},
            {'name': 'Выбор 3го куба', 'function': cf.select_third_cube},
            {'name': 'Выбор 4го куба', 'function': cf.select_forth_cube},
            {'name': 'Игнор тек. года', 'function': cf.ignore_current_year},
            {'name': 'НЕ игнор тек. года', 'function': cf.not_ignore_current_year},
            {'name': 'ГОД важнее КУБА', 'function': cf.define_year_privilege_over_cube},
            {'name': 'ГОД НЕ важнее КУБА',
                'function': cf.define_cube_privilege_over_year},
            {'name': 'ТЕРРИТОРИЯ важнее КУБА',
                'function': cf.define_territory_privilege_over_cube},
            {'name': 'ТЕРРИТОРИЯ НЕ важнее КУБА',
                'function': cf.define_cube_privilege_over_territory},
            {'name': 'Иерархия элем. измерений',
                'function': cf.form_members_in_hierachy_by_score},
            {'name': 'Выбор элементов из lv.1',
                'function': cf.all_members_from_first_hierarchy_level},
            {'name': 'Выбор элементов из lv.2',
                'function': cf.all_members_from_second_hierarchy_level},
            {'name': 'Выбор элементов из lv.3',
                'function': cf.all_members_from_third_hierarchy_level},
            {'name': 'Выбор элементов из lv.4',
                'function': cf.all_members_from_forth_hierarchy_level},
            {'name': 'Конец', 'function': cf.tree_end}
        )

        for ind, annotation, in enumerate(graph_annotation):
            self.add_node(ind, **annotation)

    def _define_edges(self):
        """Определение связей между узлами"""

        WEIGHTS = {
            'w0.1': 5, 'w0.2': 10, 'w0.3': 25, 'w0.4': 60,
            'w1.5': 30, 'w1.6': 70,
            'w2.5': 30, 'w2.6': 70,
            'w3.5': 30, 'w3.6': 70,
            'w4.5': 30, 'w4.6': 70,
            'w5.7': 30, 'w5.8': 70,
            'w6.7': 30, 'w6.8': 70,
            'w7.9': 40, 'w7.10': 60,
            'w8.9': 40, 'w8.10': 60,
            'w9.11': 0,
            'w10.11': 0,
            'w11.12': 5, 'w11.13': 10, 'w11.14': 25, 'w11.15': 60,
            'w12.16': 0,
            'w13.16': 0,
            'w14.16': 0,
            'w15.16': 0,
        }

        self.add_weighted_edges_from([
            (0, 1, WEIGHTS['w0.1']), (0, 2, WEIGHTS['w0.2']
                                      ), (0, 3, WEIGHTS['w0.3']), (0, 4, WEIGHTS['w0.4']),
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
