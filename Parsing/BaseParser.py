from Parsing.contexts import Contexts
from sys import setrecursionlimit

setrecursionlimit(10000)


class BaseParser(Contexts):
    def __init__(self):
        Contexts.__init__(self)
        self.src = ""
        self.trace = []
        self._properties = {}

    def _init_properties(self, **properties):
        self._properties = properties

    def _end_of_parsing(self):
        if self._ast and self._cur == len(self.src):
            return self._ast, self._runtime_warnings
        else:
            raise self._furthest_error
