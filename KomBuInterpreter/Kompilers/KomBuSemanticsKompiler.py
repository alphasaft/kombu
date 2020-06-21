from KomBuInterpreter.Kompilers.BaseKompiler import BaseKompiler
from KomBuInterpreter.TokenClasses import *
from utils import escape_quotes, split


TEMPLATE = """
class {0}NodeWalker:
    {5}
    
    {6}
    
    def _inspect(self, ast):
        try:
            ast.type
        except AttributeError:
            raise TypeError('Can only use \"node\" keyword on AST objects')
            
        return getattr(self, '_'+ast.type+'_')(ast)
    
    {3}
    def walk(self, ast):
        {4}
        try:
            self._{1}_
        except AttributeError:
            print("AST wasn't evaluated.")
        
        self.start()
        self._{1}_(ast)
        self.end()
        
        return ast
"""


class KomBuSemanticsKompiler(BaseKompiler):
    def compile(self, ast):
        self._ast = ast.copy()
        self._write(TEMPLATE)
        self._indent()
        self._compile_ast()

        return self._compiled_python_code

    def compile_initialization(self):
        self._compiled_python_code = ""

        self._write("def start(self):")
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

        return self._compiled_python_code

    def compile_end(self):
        self._compiled_python_code = ""
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

        return self._compiled_python_code

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
        self._compiled_python_code += "self." + node.name + " "

    def _compile_uniline_inspection(self, node):
        self._write("def _{}_(self, ast):".format(node.whole_name))
        self._indent()
        self._write("return ")
        for subnode in node.definition:
            self._compile_node(subnode)
        self._dedent()
        self._skip_line(1)

    def _compile_multiline_inspection(self, node):
        self._write("def _{}_(self, ast):".format(node.whole_name))
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

