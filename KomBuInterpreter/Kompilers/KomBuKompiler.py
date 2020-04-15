from KomBuInterpreter.KomBuChecker import KomBuChecker
from KomBuInterpreter.Kompilers.KomBuParserKompiler import KomBuParserKompiler
from KomBuInterpreter.Kompilers.KomBuSemanticsKompiler import KomBuSemanticsKompiler
from KomBuInterpreter.Kompilers.BaseKompiler import BaseKompiler
from KomBuInterpreter.TokenClasses import *
from re import sub


class KomBuKompiler(BaseKompiler):
    def __init__(self, semantics_kompiler=KomBuSemanticsKompiler, parsing_kompiler=KomBuParserKompiler):
        BaseKompiler.__init__(self)
        self._parsing_kompiler = parsing_kompiler()
        self._semantics_kompiler = semantics_kompiler()
        self._ast = []

    def kompile(self, src, base_filepath, filename):
        # We split the semantics and the the parsing part and kompile it.

        self._ast = self._checker.check(src, base_filepath, filename).ast
        semantics = [i for i in self._ast if type(i) in [UnilineInspection, MultilineInspection, BeforeBlock, AfterBlock]]
        parsing = [i for i in self._ast if type(i) not in [UnilineInspection, MultilineInspection, BeforeBlock, AfterBlock]]

        compiled_parser_code, raw_properties = self._parsing_kompiler.compile(parsing)
        compiled_semantics_code = self._semantics_kompiler.compile(semantics, raw_properties)

        self._compiled_python_code = compiled_parser_code + "\n\n" + compiled_semantics_code + "\n\n"

        self._write("class {0}Compiler:")
        self._indent()
        self._write("def __init__(self, parsing={0}Parser, semantics={0}NodeWalker):")
        self._indent()
        self._write("self._parsing, self._semantics = parsing(), semantics()")
        self._dedent()
        self._skip_line(1)
        if raw_properties['get_time']:
            self._write("@get_time")
        self._write("def compile(self, src):")
        self._indent()
        self._write("ast = self._parsing.parse(src)")
        self._write("return self._semantics.walk(ast)")
        self._skip_line(1)
        self._dedent()
        self._dedent()
        self._skip_line(3)
        self._write('SRC = """[insert input here]""" # input')
        self._skip_line(1)
        self._write('myCompiler = {0}Compiler()')
        self._write('myCompiler.compile(SRC)')

        properties = ""
        for k, v in raw_properties.items():
            if not k in ['name', 'axiom']:
                if type(v) is bool:
                    properties += "\t\t\t" + k + "=" + str(v) + ',\n'
                if type(v) is str:
                    properties += "\t\t\t" + k + "='" + v + "',\n"

        c = self._compiled_python_code.format(
            raw_properties['name'],
            raw_properties['axiom'],
            properties
        ).replace('<LCB>', '{').replace('<RCB>', '}')

        return c, raw_properties
