from KomBuInterpreter.Kompilers.BaseKompiler import BaseKompiler
from KomBuInterpreter.TokenClasses import *
from utils import escape_quotes, split, replaces

TEMPLATE = """
class {0}ErrorCatcher:
    def __init__(self):
        self._warnings = {7}
        self._catchers = {8}
    
    def warn(self, w):
        for i in range(1, self._warnings+1):
            warning_msg = getattr(self, '_warning_'+str(i)+'_', None)(w)
            if warning_msg is not None:
                return warning_msg
    
        return str(w)
    
    def catch(self, e):
        for i in range(1, self._catchers+1):
            raised = getattr(self, '_error_'+str(i)+'_', None)(e)
            if raised is not None:
                return raised

        return e
"""


class KomBuErrorCatcherKompiler(BaseKompiler):
    def __init__(self):
        self.warnings = 1
        self.errors = 1
        BaseKompiler.__init__(self)

    def compile(self, ast):
        self._ast = ast.copy()
        self._write(TEMPLATE)
        self._indent()
        self._compile_ast()

        return self._compiled_python_code

    def _compile_ast(self):
        for node in self._ast:
            self._compile_node(node)

    def _compile_node(self, node):
        if type(node) is WarningCatcher:
            self._compile_warning_catcher(node)
        elif type(node) is ErrorCatcher:
            self._compile_error_catcher(node)

    def _compile_warning_catcher(self, node):
        self._write("@warning('{}', {})".format(node.ctx_rule, node.nb))
        self._write("def _warning_{}_(self, w):".format(self.warnings))
        self._indent()
        self._write("return 'Warning : At <LCB><RCB> : {}'.format(w.pos)".format(
            replaces(escape_quotes(node.msg), '{', '<LCB>', '}', '<RCB>'))
        )
        self._dedent()

        self._skip_line(1)
        self.warnings += 1

    def _compile_error_catcher(self, node):
        if node.etype == 'missing':
            self._compile_missing_catcher_header(node)
        elif node.etype == 'failed':
            self._compile_failed_catcher_header(node)
        elif node.etype == 'generated':
            self._compile_generated_catcher_header(node)

        self._write("def _error_{}_(self, e):".format(self.errors))
        self._indent()
        if node.etype == 'generated':
            self._write("return RaisedError('{}'.replace('%!', e.e_trigger), e.pos, e.ctx)".format(
                replaces(escape_quotes(node.msg), '{', '<LCB>', '}', '<RCB>')))

        else:
            self._write("return RaisedError('{}', e.pos, e.ctx)".format(
                replaces(escape_quotes(node.msg), '{', '<LCB>', '}', '<RCB>'))
            )

        self._dedent()

        self._skip_line(1)
        self.errors += 1

    def _compile_missing_catcher_header(self, node):
        self._write("@error('missing', '{}', '{}', '{}')".format(
            node.ctx_rule,
            node.arg(0).type,
            replaces(node.arg(0).value, '{', '<LCB>', '}', '<RCB>'))
        )

    def _compile_failed_catcher_header(self, node):
        self._write("@error('failed', '{}', '{}')".format(
            node.ctx_rule,
            replaces(node.arg(0).value, '{', '<LCB>', '}', '<RCB>'))
        )

    def _compile_generated_catcher_header(self, node):
        self._write("@error('generated', '{}', {})".format(
            node.ctx_rule,
            replaces(node.arg(0).value))
        )
