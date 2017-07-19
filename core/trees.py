#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""Работа с деревьями."""

import itertools
import re
from copy import copy

# pylint: disable=too-few-public-methods


class TreeNode(object):
    """Хранит информацию об узлах дерева."""

    def __init__(self, pos, label, content=None, terminal=False):
        self.pos = pos
        self.content = content
        self.label = label
        self.terminal = terminal
        self.edges_in = []
        self.edges_out = []

    def __repr__(self):
        return '< TreeNode #{} at ({}, {}) | {}erminal | Edges (i/o): {}/{} | contains {} >'.format(
            self.label,
            *self.pos,
            'T' if self.terminal else 'Not t',
            len(self.edges_in),
            len(self.edges_out),
            self.content
        )


class TreeEdge(object):
    """Хранит информацию о рёбрах дерева."""

    def __init__(self, origin, target, weight=0):
        self.origin = origin
        self.target = target
        if isinstance(weight, int) or isinstance(weight, float):
            self.weight = weight
        else:
            self.weight = 0
        self.visible = True
        origin.edges_out.append(self)
        target.edges_in.append(self)

    def __repr__(self):
        return '{}isible tree edge #{}({}, {}) -> #{}({}, {}) with weight={} {}'.format(
            '<< V' if self.visible else '^^ Inv',
            self.origin.label,
            *self.origin.pos,
            self.target.label,
            *self.target.pos,
            self.weight,
            '>>' if self.visible else '^^',
        )


class TreeModel(object):
    """Основной класс для работы с деревьями."""

    def __init__(self):
        self.structure = [[]]

        self.nodes = TreeNodesHandler(self)
        self.edges = TreeEdgesHandler(self)

        self.nodes.new(-1, label='root')

    def normpos(self, obj):
        """Нормализует входные данные, превращая их в координаты узла внутри дерева.

        Кроме преобразований типов, обрабатывает отрицательные значения координат.

        :param obj: координаты узла (2-tuple), объект узла (TreeNode)
        или имя узла (str) для конверсии.
        :returns: координаты узла (2-tuple); если входные данные корректны,
        то все отрицательные значения координат становятся положительными.

        """
        if isinstance(obj, tuple) and len(obj) == 2:
            layer, point = obj
        elif isinstance(obj, TreeNode):
            layer, point = obj.pos
        elif isinstance(obj, str):
            layer, point = self.nodes.index[obj.lstrip('#')]
        else:
            raise (TypeError, 'Input must be 2-tuple, TreeNode or str, not {}'.format(type(obj)))

        if layer < 0:
            layer += len(self)
        if point < 0 and 0 <= layer < len(self):
            point += len(self[layer])
        return layer, point

    def check(self):
        """Вспомогательный метод для обработки удаления узлов."""
        layer = 0
        while layer < len(self):
            point = 0
            while point < len(self[layer]):
                if getattr(self[layer, point], 'deleted', False):
                    del self.structure[layer][point]
                    continue
                elif self[layer, point].pos != (layer, point):
                    self[layer, point].pos = (layer, point)
                point += 1

            if not self[layer]:
                del self.structure[layer]
            else:
                layer += 1

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.structure[key]
        return self.nodes.get(key)

    def __len__(self):
        return len(self.structure)

    def __contains__(self, pos):
        if isinstance(pos, TreeEdge):
            return pos in self.edges
        return pos in self.nodes

    def __iter__(self):
        return iter(self.structure)

    def add_layer(self):
        """Добавляет новый слой к дереву."""
        self.structure.append([])
        
    def add_fully_connected_layer(self, labels=(), contents=()):
        """Добавляет полносвязный с предыдущим слой, веса всех связей равны 0"""
        self.add_layer()
        for label, content in itertools.zip_longest(labels, contents, fillvalue=None):
            self.nodes.new(-1, label, content, False, self[-2], ())
        
    def add_children_nodes(self, parent, labels=(), contents=(), weights=()):
        """Добавляет зависимые узлы к узлу дерева"""
        newtree = TreeModel()
        newtree.add_layer()
        for label, content, weight in itertools.zip_longest(labels, contents, weights, fillvalue=None):
            newtree.nodes.new(-1, label, content, False, ['root'], [weight])
        self.append(newtree, parent)

    def append(self, subtree, root_pos):
        """Присоединяет к дереву другое дерево в качестве дочернего.

        :param subtree: Дерево для присоединения.
        :param root_pos: Координаты узла исходного дерева, который должен
            совместиться с корнем присоединяемого.

        """
        root_pos = self.normpos(root_pos)
        if root_pos not in self:
            if root_pos[0] >= len(self):
                root_pos = (root_pos[0], 0)
            else:
                root_pos = (root_pos[0], len(self[root_pos[0]]))

        layerlens = [len(l) for l in self]

        def conv_pos(pos):
            if pos == (0, 0):
                return root_pos
            new_layer = pos[0] + root_pos[0]
            if new_layer < len(layerlens):
                new_point = layerlens[new_layer] + pos[1]
            else:
                new_point = pos[1]
            return (new_layer, new_point)

        for node in subtree.nodes:
            newpos = conv_pos(node.pos)
            if newpos not in self:
                self.nodes.new(
                    newpos[0], label=node.label, content=node.content, terminal=node.terminal)
            else:
                if node.content is not None:
                    self[newpos].content = node.content
                if node.label is not 'root':
                    self[newpos].label = node.label
                self[newpos].terminal = self[newpos].terminal and node.terminal

        for edge in subtree.edges:
            self.edges.new(conv_pos(edge.origin.pos),
                           conv_pos(edge.target.pos), edge.weight)
        self.check()
            
    def pathfinder(self, start='root', eval_func=lambda e: e.weight, break_in_terminal=False, output_terminal=False, only_content=False):
        """Поиск пути в дереве по заданным критериям.

        :param start: Узел, из которого начинается поиск
            (по умолчанию - корневой узел дерева).
        :param lookup_func: Функция для расчёта приоритета рёбер. 
            Должна принимать на вход объект TreeEdge и возвращать число,
            прямо пропорциональное приоритету ребра. По умолчанию возвращает вес ребра.
        :param break_in_terminal: Если True, то алгоритм остановится, как только придёт
            в любой терминальный узел. По умолчанию - False.
        :param output_terminal: Если True, то к выводу добавляется значение параметра
            terminal финального узла пути. По умолчанию - False.
        :param only_content: Если True, то в качестве пути возвращается список данных
            из узлов; иначе возвращается список объектов рёбер. По умолчанию - False.
        """
        path = []
        current = self[start]
        
        while len(self.edges.from_node(current)) > 0:
            if break_in_terminal and current.terminal:
                break
            maxpath = max(self.edges.from_node(current, False), key=eval_func)
            path.append(maxpath)
            current = maxpath.target
            
        if only_content:
            path = [e.target.content for e in path]
        
        if output_terminal:
            return (current.terminal, path)
        return path

    def __repr__(self):
        point = len(self.nodes)
        layer = len(self)
        return '{{TreeModel: {} node{} on {} layer{}}}'.format(
            point,
            '' if point == 1 else 's',
            layer,
            '' if layer == 1 else 's',
        )


class TreeNodesHandler(object):
    """Обрабатывает операции с узлами дерева."""

    def __init__(self, tree):
        self._tree = tree
        self.index = {}

    def new(self, layer=-1, label=None, content=None, terminal=False, parents=(), weights=()):
        """Создаёт новый узел.

        :param layer: Слой, в который будет добавлен узел (по умолчанию - последний).
        :param label: Имя нового узла (по умолчанию отсутствует).
        :param content: Содержимое нового узла для постобработки путей,
            внутри дерева не используется (по умолчанию - None).
        :param terminal: Является ли узел конечным, нужно при
            обработке путей (по умолчанию - False).
        :param parents: Список родительских узлов (по умолчанию отсутствуют).
        :param weights: Список весов рёбер к новому узлу
            от родительских путей (по умолчанию отсутствуют).
        :returns: Созданный узел.

        """
        layer = self._tree.normpos((layer, 0))[0]
        while len(self._tree) <= layer:
            self._tree.add_layer()

        if label is None:
            if callable(content):
                label = type(content)
            elif len(str(content)) > 20:
                label = str(content)[:17] + ' __'
            else:
                label = str(content)
        else:
            label = re.sub(r'_[0-9]+?$', '', str(label))
        if label in self.index:
            label += '_'
            num = 1
            while label + str(num) in self.index:
                num += 1
            label += str(num)
        self.index[label] = (layer, len(self._tree[layer]))

        newnode = TreeNode(
            pos=(layer, len(self._tree[layer])),
            label=label,
            content=content,
            terminal=terminal,
        )
        self._tree.structure[layer].append(newnode)

        for parent, weight in itertools.zip_longest(parents, weights, fillvalue=0):
            self._tree.edges.new(parent, newnode, weight)

        return newnode

    def get(self, pos, default=None):
        """Получает узел по координатам, имени или порядковому номеру.

        :param pos: Координаты узла, его имя или порядковый номер в дереве.
        :param default: Значение по умолчанию, возвращаемое, если узел
            не найден (по умолчанию - None).
        :returns: Запрашиваемый узел.

        """
        if isinstance(pos, int):
            if pos >= len(self):
                return default
            return [i for i in self][pos]
        layer, point = self._tree.normpos(pos)
        if (layer, point) not in self:
            return default
        return self._tree.structure[layer][point]

    def remove(self, pos):
        """Удаляет узел из дерева.

        :param pos: Координаты узла/его имя/порядковый номер в дереве/сам объект узла.

        """
        pos = self._tree.normpos(pos)
        self.index.pop(self.get(pos).label, None)
        self.get(pos).deleted = True
        for edge in itertools.chain(self._tree.edges.to_node(pos),
                                    self._tree.edges.from_node(pos)):
            self._tree.edges.remove(edge)
        self._tree.check()

    def __getitem__(self, key):
        return self.get(key)

    def __iter__(self):
        return itertools.chain.from_iterable(self._tree.structure)

    def __contains__(self, obj):
        if isinstance(obj, TreeNode):
            return obj is self._tree[obj.pos]
        elif isinstance(obj, str):
            return obj in self.index
        elif isinstance(obj, tuple):
            layer, point = self._tree.normpos(obj)
            return (0 <= layer < len(self._tree)) and (0 <= point < len(self._tree[layer]))
        return False

    def __len__(self):
        return sum((len(l) for l in self._tree))


class TreeEdgesHandler(object):
    """Обрабатывает операции с рёбрами дерева."""

    def __init__(self, tree):
        self._tree = tree

    def new(self, origin, target, weight=0):
        """Создаёт новое ребро.

        :param origin: Исходный узел.
        :param target: Конечный узел.
        :param weight: Вес перехода.

        """
        or_pos, tar_pos = self._tree.normpos(origin), self._tree.normpos(target)
        if (or_pos, tar_pos) in self:
            self.get(or_pos, tar_pos).weight += weight
        else:
            TreeEdge(self._tree[or_pos], self._tree[tar_pos], weight)

    def get(self, origin, target, default=None, show_hidden=True):
        """Получает ребро по координатам его концов.

        :param origin: Координаты исходной точки ребра.
        :param target: Координаты конечной точки ребра.
        :param default: Значение по умолчанию, возвращаемое, если ребро
            не найдено (по умолчанию - None).

        """
        or_pos, tar_pos = self._tree.normpos(origin), self._tree.normpos(target)
        for edge in self._tree[or_pos].edges_out:
            if edge.target.pos == tar_pos and (show_hidden or edge.visible):
                return edge
        return default

    def remove(self, origin, target):
        """Удаляет ребро.

        :param origin: Координаты исходной точки ребра.
        :param target: Координаты конечной точки ребра.

        """
        or_pos, tar_pos = self._tree.normpos(origin), self._tree.normpos(target)
        if not getattr(self._tree[or_pos], 'deleted', False):
            self._tree[or_pos].edges_out = [e for e in origin.edges_out if e.target.pos != tar_pos]
        if not getattr(self._tree[tar_pos], 'deleted', False):
            self._tree[tar_pos].edges_in = [e for e in target.edges_in if e.origin.pos != or_pos]
            
    
    def hide(self, origin, target):
        """Скрывает ребро (может учитываться при поиске пути).
        
        :param origin: Координаты исходной точки ребра.
        :param target: Координаты конечной точки ребра.

        """
        self.get(origin, target).visible = False
        
    def unhide(self, origin, target):
        """Делает скрытое ребро видимым.
        
        :param origin: Координаты исходной точки ребра.
        :param target: Координаты конечной точки ребра.

        """
        self.get(origin, target).visible = True
        
    def unhide_all(self):
        """Делает все рёбра дерева видимыми."""
        for e in self:
            e.visible = True

    def to_node(self, pos, show_hidden=True):
        """Список рёбер, входящих в узел дерева.

        :param pos: Координаты узла.

        """
        return [e for e in self._tree[pos].edges_in if (show_hidden or e.visible)]
    
    def from_node(self, pos, show_hidden=True):
        """Список рёбер, выходящих из узла дерева.

        :param pos: Координаты узла.

        """
        return [e for e in self._tree[pos].edges_out if (show_hidden or e.visible)]
        

    def to_layer(self, layer, show_hidden=True):
        """Список рёбер, входящих в слой дерева.

        :param layer: Номер слоя.

        """
        return sum((self.to_node(n, show_hidden) for n in self._tree[layer]), [])
        
    def from_layer(self, layer, show_hidden=True):
        """Список рёбер, выходящих из слоя дерева.

        :param layer: Номер слоя.

        """
        return sum((self.from_node(n, show_hidden) for n in self._tree[layer]), [])

    def __getitem__(self, key):
        return self.get(*key)

    def __iter__(self):
        return itertools.chain.from_iterable(self.from_layer(l) for l in range(len(self._tree)))

    def __contains__(self, obj):
        if isinstance(obj, TreeEdge):
            return obj in self._tree[obj.origin.pos].edges_out
        elif isinstance(obj, tuple):
            return self.get(*obj) is not None
        return False

    def __len__(self):
        return len([i for i in self])
    
def piper(tree, return_path=False, **kwargs):
    """Находит оптимальный путь в дереве, после чего собирает функцию из значений узлов пути.
    
    :param tree: Дерево, в котором ведётся поиск пути и определение функций.
    :param return_path: Если True, возвращает не только получившуюся функцию, но и
        получившийся путь.
    :param **kwargs: Аргументы для функции tree.pathfinder()
        
    """
    path = tree.pathfinder(**kwargs)
    if kwargs.get('output_terminal', False):
        pipe = path[1]
    else:
        pipe = path
    if not kwargs.get('only_content', False):
        pipe = [e.target.content for e in pipe]
    
    def pipe_func(val):
        res = copy(val)
        for func in pipe:
            res = func(res)
        return res
    
    if return_path:
        return (pipe_func, path)
    return pipe_func