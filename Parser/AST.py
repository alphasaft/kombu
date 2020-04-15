from sys import setrecursionlimit
from utils import time_alert, get_time

setrecursionlimit(1000)


def deepcopy(o, from_node=[]):
    if type(o) is dict:
        return _dict_deepcopy(o, from_node)
    elif type(o) is list:
        return _list_deepcopy(o, from_node)
    elif type(o) is AST:
        return o.copy(from_node)
    else:
        return o


def _dict_deepcopy(d, from_node=[]):
    new_d = {}
    if from_node == []:
        for k, v in d.items():
            new_d[k] = deepcopy(v)
    else:
        for k, v in d.items():
            if from_node[0] == k:
                new_d[k] = deepcopy(v, from_node=from_node[1:])
            else:
                new_d[k] = v
    return new_d

def _list_deepcopy(l, from_node=[]):
    new_l = []
    if from_node == []:
        for e in l:
            new_l.append(deepcopy(e))

    else:
        i = 0
        for e in l:
            if from_node[0] == i:
                new_l.append(deepcopy(e, from_node[1:]))
            else:
                new_l.append(e)
            i += 1
    return new_l


class AST:

    def __init__(self, entire_match, fields, type=None):
        self.entire_match = entire_match
        self.type = type
        self._fields = fields

    def __getitem__(self, item):
        return self._fields.get(item)

    def __setitem__(self, key, value):
        self._fields[key] = value

    def __repr__(self):
        if self.type:
            return "< '" + self.type + "' AST which corresponds to '" + self.entire_match + "' " + str(self._fields) + " >"
        else:
            return "< AST which corresponds to '" + self.entire_match + "' " + str(self._fields) + " >"

    def __getattr__(self, item):
        if item.startswith('__'):
            return object.__getattribute__(self, item)
        else:
            return self._fields.get(item)

    def copy(self, from_node=None):
        if from_node:
            return AST(entire_match=self.entire_match, type=self.type, fields=deepcopy(self._fields,  from_node))
        else:
            return AST(entire_match=self.entire_match, type=self.type, fields=deepcopy(self._fields))

    def get(self):
        return self.entire_match

    def add_node(self, position, name, value):
        ast = [self]
        for pos_part in position:
            ast.append(ast[-1][pos_part])
        ast[-1][name] = value

    def set_entire_match(self, position, entire_match):
        node = self.get_node(position)
        if node:
            node.entire_match = entire_match

    def get_node(self, position):
        try:
            ast = self
            for pos_part in position:
                ast = ast[pos_part]
            return ast
        except KeyError:
            return None

