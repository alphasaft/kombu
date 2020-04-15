from builtins import *
from KomBuInterpreter.KomBuLexer import KomBuLexer, KomBuGrammarError
from KomBuInterpreter.TokenClasses import *
from utils import replaces, tracecall, split, escape_quotes, time_alert
import re


class KomBuParser:

    def __init__(self, lexer=KomBuLexer()):
        self._lexer = lexer
        self.lineo = 1
        self.code = Code()
        self._toimport = []
        self.tokenlist = []
        self._base_filepath = ""
        self.filename = ""
        self.namespace = ""

    def _cur(self, expected=None):
        if len(self.tokenlist) >= 1:
            pcur = self.tokenlist[0]
            if not expected or pcur.name == expected:
                return pcur
            else:
                raise KomBuGrammarError("Line {} : '{}' : Expected {}.".format(self.lineo, self._cur().value, expected))
        else:
            if expected:
                raise KomBuGrammarError("Line {} : Expected {}, got end of file.".format(self.lineo, expected))

    def _tok(self, expected=None):
        if len(self.tokenlist) > 1:
            self.tokenlist = self.tokenlist[1:]
            return self._cur(expected=expected)
        else:
            self.tokenlist = self.tokenlist[1:]
            if expected:
                raise KomBuGrammarError("Line {} : Expected {}, got end of file.".format(self.lineo, expected))

    def _next(self, expected=None, failmsg="Expected {expected}, got {got}."):
        failmsg = "Line {line} : '{gotvalue}' : " + failmsg
        if len(self.tokenlist) > 1:
            pcur = self.tokenlist[1]
            if not expected or pcur.name == expected:
                return pcur
            else:
                raise KomBuGrammarError(replaces(failmsg, '{line}', self.lineo, '{gotvalue}', self.tokenlist[0].value,
                                                 '{expected}', expected, '{gottype}', pcur.name))
        else:
            if expected:
                raise KomBuGrammarError("Line {} : Expected {}, got end of file.".format(self.lineo, expected))

    def parse(self, src, base_filepath, filename):
        # We initialize the parser for each new source.
        self.__init__()
        self._base_filepath = base_filepath
        self.filename = filename
        self.namespace = filename[:-3]
        self.tokenlist = self._lexer.tokenize(src, filename)
        block = self._parse_block()
        self._cur('newline')
        self.lineo += 1
        self._tok()
        while block != EOF():
            self.code.add(block)
            block = self._parse_block()
            self._cur('newline')
            self._tok()
            self.lineo += 1
        self._import_libs()
        print([node.whole_name() for node in self.code.ast if type(node) in (RuleDefinition, RuleCall)])
        return self.code

    @tracecall(False, 0)
    def _parse_block(self):
        if self._cur().name == 'constantname':
            return self._parse_constant_declaration()
        elif self._cur().name == 'ident':
            return self._parse_rule_definition()
        elif self._cur().name == 'uni_line_comment':
            return self._parse_comment()
        elif self._cur().name == 'multi_lines_comment':
            return self._parse_comment()
        elif self._cur().name == 'keyword' and self._cur().value == 'with':
            return self._parse_import()
        elif self._cur().name == 'keyword' and self._cur().value == 'block':
            return self._parse_block_definition()
        elif self._cur().name == 'keyword' and self._cur().value == 'group':
            return self._parse_group()
        elif self._cur().name == 'keyword' and self._cur().value == 'inspect':
            return self._parse_inspection()
        elif self._cur().name == 'keyword' and self._cur().value == 'before':
            return self._parse_init_or_end_block(block_type='init')
        elif self._cur().name == 'keyword' and self._cur().value == 'after':
            return self._parse_init_or_end_block(block_type='end')
        elif self._cur().name == 'newline':
            return NewLine(self._cur().value)
        elif self._cur().name == 'EOF':
            self._tok()
            return EOF()
        elif re.match('R[A-Z]', self._cur().name):
            raise KomBuGrammarError("Line {} : '{}' : Got end char but there wasn't any begin char as (, or [.".format(self.lineo, self._cur().value))
        else:
            raise KomBuGrammarError("Line {} : '{}' : Unexpected line syntax.".format(self.lineo, self._cur().value))

    @tracecall(False, 0)
    def _parse_constant_declaration(self):
        option_name = self._cur().value
        value = True
        self._tok()
        if self._cur().name == 'option_assign':
            value = self._tok('string').value
            self._tok()
        return SetConstant(option_name, value)

    @tracecall(False, 0)
    def _parse_import(self):

        imports = [self._tok(expected='ident').value]
        from_file = None
        self._tok()
        while self._cur().name == 'coma':
            imports.append(self._tok(expected='ident').value)
            self._tok()

        if self._cur().name == 'keyword' and self._cur().value == 'from':
            from_file = self._tok().value
            self._tok()

        if from_file:
            self._toimport.append(FromImport(imports, from_file))
        else:
            [self._toimport.append(Import(toimport)) for toimport in imports]

        return NewLine()

    def _parse_comment(self):
        lines = len(self._cur().value.split('\n'))
        self.lineo += lines - 1
        self._tok()
        return [NewLine() for l in range(lines)]

    @tracecall(False, 0)
    def _parse_rule_definition(self):
        name = self._cur(expected='ident').value
        self._tok(expected='ruleassign')
        self._tok()
        definition = [self._parse_rule_definition_part()]
        while self._cur().name != 'newline' and self._cur().name != 'excl_point':
            definition.append(self._parse_rule_definition_part())

        error_handlers_stacker = None
        if self._cur().name == 'excl_point':
            error_handlers_stacker = ErrorHandlersStacker()
            while self._cur().name != 'newline':
                self._tok()
                error_handlers_stacker.add_error_handler(self._parse_error_handler())
                if self._cur().name not in ['ampersand', 'newline']:
                    raise KomBuGrammarError("Line {} : Unexpected syntax after error handler".format(self.lineo))

        return RuleDefinition(name, self.namespace, definition, error_handlers_stacker if error_handlers_stacker else None)

    @tracecall(False, 0)
    def _parse_rule_definition_part(self):
        if self._cur().name == 'rulecall':
            part = RuleCall(self._cur().value, self.namespace)
            self._tok()
        elif self._cur().name == 'LOptional':
            part = self._parse_optional_part()
        elif self._cur().name == 'LChoiceGroup':
            part = self._parse_group_part()
        elif self._cur().name == 'string':
            part = Match(self._cur().value)
            self._tok()
        elif self._cur().name == 'regex':
            regex = self._cur().value
            self._tok()
            part = RegexMatch(regex)
        else:
            errortoken = self._cur().value
            if errortoken == '|':
                errormsg = "Line {} : '|' is used outside of a choices group.".format(self.lineo)
            elif errortoken == ']':
                errormsg = "Line {} : Found ']' to close an optional group but no '[' to begin it.".format(self.lineo)
            elif errortoken == ')':
                errormsg = "Line {} : Found ')' to close a choices group but no '(' to begin it.".format(self.lineo)
            else:
                errormsg = "Line {} : '{}' : Syntax error in the rule definition.".format(self.lineo, self._cur().value)

            raise KomBuGrammarError(errormsg)

        name = self._cur().value if self._cur().name == 'groupname' else None
        if name:
            self._tok()
            part.group_name = name

        return part

    @tracecall(False, 0)
    def _parse_optional_part(self):
        self._tok()
        definition = []
        while self._cur().name != 'ROptional':
            if self._cur().name == 'EOF' or self._cur().name == 'newline':
                raise KomBuGrammarError("Line {} : Missing ']' to close the optional group.".format(self.lineo))
            definition.append(self._parse_rule_definition_part())
        self._tok()
        return OptionalGroup(definition)

    @tracecall(False, 0)
    def _parse_group_part(self):
        choices = Choices()
        while self._cur().name != 'RChoiceGroup':
            self._tok()
            option = Option()
            if self._cur().name == 'OptionsSeparator' or self._cur().name == 'RChoiceGroup':
                raise KomBuGrammarError("Line {} : An option cannot be empty.".format(self.lineo))
            option.add_code(self._parse_rule_definition_part())
            while self._cur().name != 'OptionsSeparator' and self._cur().name != 'RChoiceGroup':
                if self._cur().name == 'EOF' or self._cur().name == 'newline':
                    raise KomBuGrammarError("Line {} : Missing ')' to close the choices group.".format(self.lineo))
                option.add_code(self._parse_rule_definition_part())
            choices += option

        self._tok()
        return choices

    def _parse_error_handler(self):
        if self._cur(expected='keyword').value not in ['missing']:
            raise KomBuGrammarError("Error type for error handler should be 'missing'.")
        type = self._cur().value
        args = {}
        if type == 'missing':
            args['value'] = self._tok(expected='string')
        self._tok(expected='rarrow')
        msg = self._tok(expected='string')
        self._tok()

        return ErrorHandler(type=type, error_msg=msg, **args)

    def _parse_inspection(self):
        self._tok(expected='ident')
        if self._next().name == 'keyword' and self._next().value == 'return':
            return self._parse_uniline_inspection()
        if self._next().name == 'LBlock':
            return self._parse_multiline_inspection()

    def _parse_uniline_inspection(self):

        inspection_name = self._cur().value
        self._tok(expected='keyword')
        self._tok()

        inspection_code = []

        inspection_code_part = self._parse_inspection_code_part()[1]
        if inspection_code_part == NewLine():
            raise KomBuGrammarError("Line {} : Unilines inspections need a return value. Use None if you don't want to "
                                    "return anything.".format(self.lineo))

        inspection_code.append(inspection_code_part)
        previous_src = self.tokenlist.copy()
        while inspection_code_part != NewLine():
            previous_src = self.tokenlist.copy()
            inspection_code_part = self._parse_inspection_code_part()[1]
            inspection_code.append(inspection_code_part)

        self.tokenlist = previous_src.copy()

        return UnilineInspection(inspection_name, inspection_code)

    def _parse_multiline_inspection(self):
        inspection = MultilineInspection(name=self._cur().value, definition=[])
        self._tok(expected='LBlock')
        self._tok()
        imbrication_level = 1

        while imbrication_level > 0 and self._cur():
            imbrication_add, inspection_code_part = self._parse_inspection_code_part()
            imbrication_level += imbrication_add
            if inspection_code_part == NewLine():
                self.lineo += 1
            inspection.definition.append(inspection_code_part)

        if not self._cur():
            raise KomBuGrammarError("Line {} : Unexpected end of file while parsing multiline inspection.".format(self.lineo))

        self._tok(expected='newline')
        inspection.definition = inspection.definition[:-1]

        return inspection

    def _parse_inspection_code_part(self):
        imbrication_add = 0

        if (self._cur().name, self._cur().value) == ('keyword', 'node'):
            return imbrication_add, self._parse_node_keyword()

        elif self._cur().name == 'newline':
            indentation = self._cur().value
            self._tok()
            return imbrication_add, NewLine(indentation)

        elif self._cur().name == 'silcrow':
            name = self._tok(expected='ident').value
            self._tok()
            return imbrication_add, GlobalVar(name)

        else:

            if self._cur().name == 'LBlock':
                imbrication_add = 1
            if self._cur().name == 'RBlock':
                imbrication_add = -1

            if self._cur().name == 'string':
                raw_code = "'" + escape_quotes(self._cur().value) + "'"
            else:
                raw_code = self._cur().value
            self._tok()

            return imbrication_add, RawPythonCode(raw_code)

    def _python_format(self, node):
        if node.name == 'string':
            return "'" + node.value + "'"
        elif node.name == 'regex':
            raise SytaxError("Line {} : '/{}/' : Invalid python code.".format(self.lineo, node.value))
        else:
            return node.value

    def _parse_node_keyword(self):
        node_to_get = NodeCall()

        if self._next().name == 'ident' and self._next().value == 'ast' and self.tokenlist[2:3][0] and self.tokenlist[2:3][0].name != 'point':
            raise KomBuGrammarError("Line {} : 'node' keyword needs to be applied to a subnode of the ast.".format(self.lineo))

        self._tok(expected='ident')  # subnode

        while self._next().name == 'point':
            node_to_get.node_path.append(self._cur(expected='ident').value)
            self._tok(expected='point')
            self._tok(expected='ident')

        node_to_get.node_path.append(self._cur(expected='ident').value)
        self._tok()

        return node_to_get

    def _parse_init_or_end_block(self, block_type):

        if block_type == 'init':
            block = BeforeBlock()
        elif block_type == 'end':
            block = AfterBlock()

        self._tok(expected='LBlock')
        self._tok(expected='newline')
        self.lineo += 1
        imbrication_level = 1

        while self._cur() and imbrication_level > 0:
            added_code, imbrication_add = self._parse_init_or_end_block_part()
            imbrication_level += imbrication_add
            block.code.append(added_code)

        if not self._cur():
            if block_type == 'init':
                raise KomBuGrammarError("Line {} : Unexpected end of file while parsing 'before' block.".format(self.lineo))
            elif block_type == 'end':
                raise KomBuGrammarError("Line {} : Unexpected end of file while parsing 'after' block.".format(self.lineo))

        block.code.pop()
        block.code.pop()
        return block

    def _parse_init_or_end_block_part(self):

        imbrication_add = 0

        if self._cur().name == 'LBlock':
            imbrication_add = 1
        elif self._cur().name == 'RBlock':
            imbrication_add = -1

        if self._cur().name == 'silcrow':
            name = self._tok(expected='ident').value
            self._tok()
            return GlobalVar(name), 0

        elif self._cur().name == 'newline':
            self.lineo += 1
            indentation = self._cur().value
            self._tok()
            return NewLine(indentation), 0

        elif self._cur().name == 'string':
            code = "'"+escape_quotes(self._cur().value)+"'"

        else:
            code = self._cur().value.strip()

        self._tok()
        return RawPythonCode(code), imbrication_add

    def _parse_test(self):
        raise KomBuGrammarError("Line {} : Tests option isn't implemented.".format(self.lineo))

    def _parse_block_definition(self):
        raise KomBuGrammarError("Line {} : Blocks option isn't implemented.".format(self.lineo))

    def _parse_group(self):
        raise KomBuGrammarError("Line {} : Groups option isn't implemented.".format(self.lineo))

    def _import_libs(self):

        from KomBuInterpreter.KombuImporter import KombuImporter

        libspath = '{0} ; {0}/kblibs'.format(self._base_filepath)

        for node in self.code.ast:
            if type(node) is SetConstant and node.constantname == 'libspath':
                if node.value.startswith('/'):
                    libspath += ';' + node.value
                else:
                    libspath += ';' + self._base_filepath + '/' + node.value

        importer = KombuImporter(libspath)

        self._change_imported_rulecalls_namespaces()

        for toimport in self._toimport:
            if type(toimport) is Import:
                importer.import_lib(toimport.toimport)
            elif type(toimport) is FromImport:
                importer.import_rules_from_lib(toimport.from_file, toimport.toimport)

        importer.clean_imported_code()
        self.code.add(importer.imported_code)

    def _change_imported_rulecalls_namespaces(self):

        def change_node_namespaces(node, new_namespaces):
            if type(node) is RuleDefinition:
                for subnode in node.definition:
                    change_node_namespaces(subnode, new_namespaces)

            elif type(node) is Choices:
                for option in node.options:
                    for subnode in option.definition:
                        change_node_namespaces(subnode, new_namespaces)

            elif type(node) is OptionalGroup:
                for subnode in node.definition:
                    change_node_namespaces(subnode, new_namespaces)

            elif type(node) is RuleCall:
                if new_namespaces.get(node.name):
                    print(new_namespaces[node.name])
                    node.namespace = new_namespaces[node.name]

        new_namespaces = {}
        for toimport in [i for i in self._toimport if type(i) is FromImport]:
            for rule_to_import in toimport.toimport:
                new_namespaces[rule_to_import] = toimport.from_file

        for node in [r for r in self.code.ast if type(r) is RuleDefinition]:
            change_node_namespaces(node, new_namespaces)

