from Parser.Contexts import Contexts
from Parser.Errors import Error
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
        self.errors_stack.append(Error("Invalid Syntax (Got no other information)"))
        if self._ast:
            return self._ast['ast']
        else:
            raise self.errors_stack[0]
