from KomBuInterpreter.Kompilers.BaseKompiler import BaseKompiler
from KomBuInterpreter.TokenClasses import *
from utils import escape_quotes, split


class KomBuSemanticsKompiler(BaseKompiler):
    def compile(self, ast, properties):
        self._properties = properties
        self._ast = ast.copy()
        self._write_header()
        self._compile_ast()

        return self._compiled_python_code

    def _write_header(self):
        self._write("class {0}NodeWalker:")
        self._indent()
        self._compile_initialization()
        self._write("def _inspect(self, ast):")
        self._indent()
        self._write("try:")
        self._indent()
        self._write("ast.type")
        self._dedent()
        self._write("except AttributeError:")
        self._indent()
        self._write("raise SyntaxError('Can only use \"node\" keyword on AST objects')")
        self._dedent()
        self._write("return getattr(self, '_'+ast.type+'_')(ast)")
        self._dedent()
        self._skip_line(1)
        if self._properties.get('get_time'):
            self._write("@get_time")
        self._write("def walk(self, ast):")
        self._indent()
        self._compile_ast_showing()
        self._write('try:')
        self._indent()
        self._write("self._{1}_(ast)")
        self._write("self.end()")
        self._dedent()
        self._write('except IndexError:')
        self._indent()
        self._write('print("/!\\ : AST wasn\'t evaluated.")')
        self._write('return ast')
        self._dedent()
        self._dedent()
        self._compile_end()
        self._skip_line(1)

    def _compile_ast_showing(self):
        if self._properties['show_ast']:
            self._write("print('Got AST :', ast)")

    def _compile_initialization(self):
        self._write("def __init__(self):")
        self._indent()

        if not [n for n in self._ast if type(n) is BeforeBlock]:
            self._write('pass')

        for node in [n for n in self._ast if type(n) is BeforeBlock]:

            definition = split(node.code, NewLine(), include_at_beginning=True)[1:]
            base_indentation = len(definition[0][0].indentation.replace('\t', ' '*16))

            for line in definition:
                self._write((len(line[0].indentation.replace('\t', ' '*16))-base_indentation)*' ')
                for subnode in line[1:]:
                    self._compile_node(subnode)

        self._dedent()
        self._skip_line(1)

    def _compile_end(self):
        self._write("def end(self):")
        self._indent()

        if not [n for n in self._ast if type(n) is AfterBlock]:
            self._write('pass')

        for node in [n for n in self._ast if type(n) is AfterBlock]:

            definition = split(node.code, NewLine(), include_at_beginning=True)[1:]
            base_indentation = len(definition[0][0].indentation.replace('\t', ' ' * 16))

            for line in definition:
                self._write((len(line[0].indentation.replace('\t', ' ' * 16)) - base_indentation) * ' ')
                for subnode in line[1:]:
                    self._compile_node(subnode)

        self._dedent()
        self._skip_line(1)

    def _compile_ast(self):
        for node in self._ast:
            self._compile_node(node)

    def _compile_node(self, node):
        if type(node) is UnilineInspection:
            self._compile_uniline_inspection(node)
        elif type(node) is MultilineInspection:
            self._compile_multiline_inspection(node)
        elif type(node) is RawPythonCode:
            self._compile_raw_python_code(node)
        elif type(node) is NodeCall:
            self._compile_nodecall(node)
        elif type(node) is GlobalVar:
            self._compile_global_var(node)
        elif type(node) is NewLine:
            pass
        elif type(node) is BeforeBlock:
            pass
        elif type(node) is AfterBlock:
            pass
        else:
            raise SyntaxError("Error in the SemanticsKompiler code.")

    def _compile_global_var(self, node):
        self._compiled_python_code += "self." + node.name

    def _compile_uniline_inspection(self, node):
        self._write("def _{}_(self, ast):".format(node.name))
        self._indent()
        self._write("return ")
        for subnode in node.definition:
            self._compile_node(subnode)
        self._dedent()
        self._skip_line(1)

    def _compile_multiline_inspection(self, node):
        self._write("def _{}_(self, ast):".format(node.name))
        self._indent()
        definition = split(node.definition, NewLine(), include_at_beginning=True)[1:]
        base_indentation = len(definition[0][0].indentation.replace('\t', ' '*16))
        for line in definition:
            self._write((len(line[0].indentation.replace('\t', ' '*16))-base_indentation)*' ')
            for subnode in line[1:]:
                self._compile_node(subnode)
        self._dedent()
        self._skip_line(1)

    def _compile_raw_python_code(self, node):
        self._compiled_python_code += node.code.replace('{', '<LCB>').replace('}', '<RCB>')

    def _compile_nodecall(self, node):
        self._compiled_python_code += 'self._inspect('+".".join(node.node_path) + ')'

