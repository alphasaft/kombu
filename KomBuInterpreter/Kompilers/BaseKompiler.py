from KomBuInterpreter.KomBuChecker import KomBuChecker
from KomBuInterpreter.TokenClasses import Code


class BaseKompiler(object):
    def __init__(self, checker=KomBuChecker):
        self._checker = checker()
        self._identation = 0
        self._compiled_python_code = ""
        self._ast = Code()
        self._properties = {
            'name': 'UnknownLanguage',
            'libspath': '. ; kblibs',
            'axiom': 'code',
            'keep_whitespaces': False,
            'cut_end': False,
            'get_time': False,
            'show_ast': False,
        }
        self._lineo = 1

    def _indent(self):
        """Indent the next lines."""
        self._identation += 1

    def _dedent(self):
        """Dedent the next lines."""
        self._identation -= 1

    def _write(self, string):
        """Write the provided string in the compiled code as a new line, with indentation at the beginning."""
        self._compiled_python_code += '\n' + ('    ' * self._identation) + string

    def _skip_line(self, n=1):
        """Write an empty line in the compiled code."""
        self._compiled_python_code += '\n' * n
