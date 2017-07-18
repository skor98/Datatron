# -*- coding: utf-8 -*-
"""
Created on Mon Jul 17 22:16:42 2017

@author: larousse
"""

class TreeNode (object):
    def __init__(self, tree, pos, content, terminal=False):
        self.tree = tree
        self.pos = pos
        self.content = content
        self.terminal = terminal
        self.paths = []

    def link(self, target, weight):
        self.paths.append(TreePath(self, target, weight))
        
    def get_path_to(self, target_pos):
        res = [_ for _ in self.paths if _.target == target_pos]
        return res[0] if len(res) > 0 else None
        
    def make_child(self, weight, content, terminal=False):
        child = self.tree.add_node(self.pos[0]+1, content, terminal)
        self.link(child, weight)
        return child
    
    def step (self):
        if self.terminal:
            return None
        elif len(self.paths) == 0:
            return None
        else:
            choice = max(self.paths, key=lambda p: p.weight*p.visible)
            if choice.weight == 0 or not choice.visible:
                return None
            else:
                return choice
        
        
        
class TreePath (object):
    def __init__(self, origin, target, weight):
        self.origin = origin.pos
        self.target = target.pos
        self.content = target.content
        self.weight = weight
        self.visible = True
        
        
class TreeModel (object):
    def __init__(self):
        self.layers = []
        self.add_node(0, None)
        
    def __getitem__(self, key):
        return self.layers[key[0]][key[1]]
    
    def add_node (self, layer, content, terminal=False):
        if len(self.layers) <= layer:
            self.layers += [[] for _ in range(len(self.layers), layer+1)]
        newnode = TreeNode(self, (layer, len(self.layers[layer])), content, terminal)
        self.layers[layer].append(newnode)
        return newnode
        
    def walk (self, starter=(0, 0)):
        curr = self[starter]
        res = []
        
        #TODO: rewrite
        path = curr.step()
        while path is not None:
            res.append(path)
            curr = self[path.target]
            path = curr.step()
            
        return res
    
    def hide_path (self, origin, target):
        self[origin].get_path_to(target).visible = False
            
    def unhide_all (self):
        for layer in self.layers:
            for node in layer:
                for path in node.paths:
                    path.visible = True
                    
    