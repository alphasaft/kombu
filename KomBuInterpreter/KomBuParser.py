from exceptions import KombuError
from KomBuInterpreter.KomBuLexer import KomBuLexer
from KomBuInterpreter.TokenClasses import *
from KomBuInterpreter.KombuImporter import KombuImporter
from utils import replaces, split, escape_quotes
import re


class KomBuParser:
    def __init__(self, lexer=KomBuLexer()):
        self._lexer = lexer
        self.i = 0
        self.code = Code()
        self._toimport = []
        self.tokenlist = []
        self._base_filepath = ""
        self.filename = ""
        self.namespace = ""

    def _cur(self, expected=None):
        if len(self.tokenlist) > self.i:
            cur = self.tokenlist[self.i]
            if not expected or cur.name == expected:
                return cur
            else:
                raise KombuError("{} : '{}' : Expected {}.".format(self._pos(formatted=True), self._cur().value, expected))
        else:
            if expected:
                raise KombuError("{} : Expected {}, got end of file.".format(self._pos(formatted=True), expected))

    def _tok(self, expected=None):
        if len(self.tokenlist) > self.i + 1:
            self.i += 1
            return self._cur(expected=expected)
        else:
            self.i += 1
            if expected:
                raise KombuError("{} : Expected {}, got end of file.".format(self._pos(formatted=True), expected))

    def _next(self, expected=None, failmsg="Expected {expected}, got {got}."):
        failmsg = "Line {line} : '{gotvalue}' : " + failmsg
        if len(self.tokenlist) > self.i + 1:
            pcur = self.tokenlist[self.i+1]
            if not expected or pcur.name == expected:
                return pcur
            else:
                raise KombuError(replaces(failmsg, '{line}', self._pos(), '{gotvalue}', self.tokenlist[self.i].value,
                                                 '{expected}', expected, '{gottype}', pcur.name))
        else:
            if expected:
                raise KombuError("{} : Expected {}, got end of file.".format(self._pos(formatted=True), expected))

    def _bef(self):
        if self.i > 0:
            self.i -= 1
        else:
            raise ValueError("Cannot use bef.")

    def _pos(self, formatted=False):
        if formatted:
            return "In {}, at {}".format(self.filename, self._pos()[1:])
        else:
            return (self.filename,) + self._cur().pos

    def parse(self, src, base_filepath, filename, imports_cache):
        # We initialize the parser for each new source.
        self.__init__()
        self._base_filepath = base_filepath
        self.filename = filename
        self.namespace = filename[:-3]
        self.tokenlist = self._lexer.tokenize(src, filename)
        self.i = 0
        block = self._parse_block()
        self._cur('newline')
        self._tok()
        while not EOF.equals(block):
            self.code.add(block)
            block = self._parse_block()
            self._cur('newline')
            self._tok()
        self._import_libs(imports_cache)
        return self.code

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
        elif self._cur().name == 'keyword' and self._cur().value == 'catch':
            return self._parse_error_catcher()
        elif self._cur().name == 'newline':
            return NewLine(self._pos(), self._cur().value)
        elif self._cur().name == 'EOF':
            self._tok()
            return EOF(self._pos())
        elif re.match('R[A-Z]', self._cur().name):
            raise KombuError("{} : '{}' : Got end char but there wasn't any begin char as (, or [.".format(self._pos(formatted=True), self._cur().value))
        else:
            raise KombuError("{} : '{}' : Unexpected line syntax.".format(self._pos(formatted=True), self._cur().value))

    def _parse_constant_declaration(self):
        pos = self._pos()
        option_name = self._cur().value
        value = True
        self._tok()
        if self._cur().name == 'option_assign':
            value = self._tok('string').value
            self._tok()
        return SetConstant(option_name, value, pos)

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
            self._toimport.append(FromImport(imports, from_file, self._pos()))
        else:
            [self._toimport.append(Import(toimport, self._pos())) for toimport in imports]

        return NewLine(self._pos())

    def _parse_comment(self):
        lines = len(self._cur().value.split('\n'))
        self._tok()
        return [NewLine(self._pos()) for l in range(lines)]

    def _parse_rule_definition(self):
        name = self._cur(expected='ident').value
        self._tok(expected='ruleassign')
        self._tok()
        definition = [self._parse_rule_definition_part()]
        while self._cur().name != 'newline' and self._cur().name != 'excl_point':
            definition.append(self._parse_rule_definition_part())

        return RuleDefinition(name, self.namespace, definition, self._pos())

    def _parse_rule_definition_part(self):
        if self._cur().name == 'rulecall':
            part = RuleCall(self._cur().value, self.namespace, self._pos())
            self._tok()
        elif self._cur().name == 'LOptional':
            part = self._parse_optional_part()
        elif self._cur().name == 'LGroup':
            part = self._parse_group_or_choices_group()
        elif self._cur().name == 'string':
            part = Match(self._cur().value, self._pos())
            self._tok()
        elif self._cur().name == 'regex':
            regex = self._cur().value
            self._tok()
            part = RegexMatch(regex, self._pos())
        else:
            errortoken = self._cur().value
            if errortoken == '|':
                errormsg = "{} : '|' used outside of a choices group.".format(self._pos(formatted=True))
            elif errortoken == ']':
                errormsg = "{} : Found ']' to close an optional group but no '[' to begin it.".format(self._pos(formatted=True))
            elif errortoken == ')':
                errormsg = "{} : Found ')' to close a choices group but no '(' to begin it.".format(self._pos(formatted=True))
            else:
                errormsg = "{} : '{}' : Syntax error in the rule definition.".format(self._pos(formatted=True), self._cur().value)

            raise KombuError(errormsg)

        name = self._parse_name()
        if name:
            self._tok()
            part.group_name = name
            if type(part) is Choices:
                part = self._apply_choices_groupname_to_options(part)

        error_trigger = self._parse_error_trigger()
        if error_trigger:
            self._tok()
            if type(part) is OptionalGroup:
                part = WarningTrigger(error_trigger, part, self._pos())
            else:
                part = ErrorTrigger(error_trigger, part, self._pos())

        return part

    def _parse_name(self):
        if self._cur().name == 'groupname':
            return self._cur().value
        else:
            return None

    def _parse_error_trigger(self):
        if self._cur().name == 'error':
            return self._cur().value
        else:
            return None

    def _apply_choices_groupname_to_options(self, node):
        for option in node.options:
            if len(option.definition) == 1 and not option.definition[0].group_name:
                option.definition[0].group_name = node.group_name
            else:
                option.definition = [Group(option.definition, node.group_name, self._pos())]

        node.group_name = "self"
        return node

    def _parse_optional_part(self):
        definition = []
        self._tok()
        while self._cur().name != 'ROptional':
            if self._cur().name == 'EOF' or self._cur().name == 'newline':
                raise KombuError("{} : Missing ']' to close the optional group.".format(self._pos(formatted=True)))
            definition.append(self._parse_rule_definition_part())
        self._tok()
        return OptionalGroup(definition, self._pos())

    def _parse_group_or_choices_group(self):
        is_choices_group = False
        i = self.i
        while not (self.tokenlist[i].name == 'RGroup' or self.tokenlist[i-1].name == 'OptionsSeparator'):
            if self.tokenlist[i].name == 'OptionsSeparator':
                is_choices_group = True
            if self.tokenlist[i].name in ["newline", 'EOF']:
                raise KombuError("{} : Missing ')' to close the choices group".format(self._pos(formatted=True)))
            i += 1

        if is_choices_group:
            return self._parse_choices_group()
        else:
            return self._parse_group()

    def _parse_choices_group(self):
        choices = Choices(self._pos())
        while self._cur().name != 'RGroup':
            self._tok()
            option = Option(self._pos())
            if self._cur().name == 'OptionsSeparator' or self._cur().name == 'RGroup':
                raise KombuError("{} : An option cannot be empty.".format(self._pos(formatted=True)))
            option.add_code(self._parse_rule_definition_part())
            while self._cur().name != 'OptionsSeparator' and self._cur().name != 'RGroup':
                option.add_code(self._parse_rule_definition_part())
            choices += option

        self._tok()
        return choices

    def _parse_group(self):
        group = Group([], "self", self._pos())
        self._tok()
        while self._cur().name != 'RGroup':
            group.definition.append(self._parse_rule_definition_part())

        self._tok()
        return group

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
            raise KombuError("{} : Unilines inspections need a return value. Use None if you don't want to "
                                    "return anything.".format(self._pos(formatted=True)))

        inspection_code.append(inspection_code_part)
        while inspection_code_part != NewLine():
            inspection_code_part = self._parse_inspection_code_part()[1]
            inspection_code.append(inspection_code_part)

        self._bef()

        return UnilineInspection(inspection_name, self.namespace, inspection_code, self._pos())

    def _parse_multiline_inspection(self):
        inspection = MultilineInspection(name=self._cur().value, namespace=self.namespace, definition=[], pos=self._pos())
        self._tok(expected='LBlock')
        self._tok()
        imbrication_level = 1

        while imbrication_level > 0 and self._cur():
            imbrication_add, inspection_code_part = self._parse_inspection_code_part()
            imbrication_level += imbrication_add
            inspection.definition.append(inspection_code_part)

        if not self._cur():
            raise KombuError("{} : Unexpected end of file while parsing multiline inspection.".format(self.tokenlist[-1].pos))

        self._cur(expected='newline')
        inspection.definition = inspection.definition[:-1]

        return inspection

    def _parse_inspection_code_part(self):
        imbrication_add = 0

        if (self._cur().name, self._cur().value) == ('keyword', 'node'):
            return imbrication_add, self._parse_node_keyword()

        elif (self._cur().name, self._cur().value) == ('keyword', 'it'):
            pos = self._pos()
            self._tok()
            return imbrication_add, RawPythonCode("ast.get()", pos)

        elif self._cur().name == 'newline':
            indentation = self._cur().value
            self._tok()
            return imbrication_add, NewLine(self._pos(), indentation)

        elif self._cur().name == 'silcrow':
            name = self._tok(expected='ident').value
            self._tok()
            return imbrication_add, GlobalVar(name, self._pos())

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

            return imbrication_add, RawPythonCode(raw_code, self._pos())

    def _python_format(self, node):
        if node.name == 'string':
            return "'" + node.value + "'"
        elif node.name == 'regex':
            raise SytaxError("{} : '/{}/' : Invalid python code.".format(self._pos(formatted=True), node.value))
        else:
            return node.value

    def _parse_node_keyword(self):
        node_to_get = NodeCall(self._pos())

        if self._next().name == 'ident' and self._next().value == 'ast' and self.tokenlist[self.i+2:self.i+3][0] and self.tokenlist[self.i+2:self.i+3][0].name != 'point':
            raise KombuError("{} : 'node' keyword needs to be applied to a subnode of the ast.".format(self._pos(formatted=True)))

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
            block = BeforeBlock(self._pos())
        elif block_type == 'end':
            block = AfterBlock(self._pos())
        else:
            block = None

        self._tok(expected='LBlock')
        self._tok(expected='newline')
        imbrication_level = 1

        while self._cur() and imbrication_level > 0:
            added_code, imbrication_add = self._parse_init_or_end_block_part()
            imbrication_level += imbrication_add
            block.code.append(added_code)

        if not self._cur():
            if block_type == 'init':
                raise KombuError("{} : Unexpected end of file while parsing 'before' block.".format(self._pos(formatted=True)))
            elif block_type == 'end':
                raise KombuError("{} : Unexpected end of file while parsing 'after' block.".format(self._pos(formatted=True)))

        block.code.pop()
        block.code.pop()
        return block

    def _parse_init_or_end_block_part(self):

        imbrication_add = 0

        if self._cur().name == 'LBlock':
            imbrication_add = 1
        elif self._cur().name == 'RBlock':
            imbrication_add = -1

        if (self._cur().name, self._cur().value) == ('keyword', 'node'):
            return self._parse_node_keyword(), imbrication_add

        if self._cur().name == 'silcrow':
            name = self._tok(expected='ident').value
            self._tok()
            return GlobalVar(name, self._pos()), 0

        elif self._cur().name == 'newline':
            indentation = self._cur().value
            self._tok()
            return NewLine(self._pos(), indentation), 0

        elif self._cur().name == 'string':
            code = "'"+escape_quotes(self._cur().value)+"'"

        else:
            code = self._cur().value.strip()

        self._tok()
        return RawPythonCode(code, self._pos()), imbrication_add

    def _parse_error_catcher(self):
        pos = self._pos()
        args = []

        etype = self._tok(expected="error").value
        if etype.isnumeric():
            args.append(ErrorCatcherArg('int', etype, self._pos()))
            etype = 'generated'

        self._tok()
        while not (self._cur().name == 'keyword' and self._cur().value == 'in') and self._cur().name not in ['newline', 'rarrow', 'keyword']:
            args.append(ErrorCatcherArg(self._cur().name, self._cur().value, self._pos()))
            self._tok()

        ctx_rules = [self._tok(expected='ident').value]
        while self._tok().name == 'coma':
            ctx_rules.append(self._tok(expected='ident').value)

        self._cur(expected='rarrow')
        msg = self._tok(expected="string").value

        self._tok()
        if self._cur().name == "coma":
            self._tok()
            if not (self._cur().name == 'keyword' and self._cur().value == "continue"):
                raise KombuError("{} : ',' not expected. Or do you mean ', continue' ?"
                                 .format(self._pos(formatted=True)))

            if not etype == "generated":
                raise KombuError("{} : ', continue' create a warning catcher, but you seem to need an "
                                 "error catcher".format(self._pos(formatted=True)))
            warn = True
            self._tok()
        else:
            warn = False

        if warn:
            if len(args) > 1:
                raise KombuError("{} : 'catch !{} {}' : Warning does not need any arguments."
                                 .format(self._pos(formatted=True), args[0].value, " ".join([a.value for a in args[1:]])))

            return [WarningCatcher(msg, self.filename[:-3]+'__'+ctx_rule, args[0].value, pos) for ctx_rule in ctx_rules]
        else:
            return [ErrorCatcher(msg, etype, self.filename[:-3]+'__'+ctx_rule, args, pos) for ctx_rule in ctx_rules]

    def _parse_test(self):
        raise KombuError("{} : Tests option isn't implemented.".format(self._pos(formatted=True)))

    def _parse_block_definition(self):
        raise KombuError("{} : Blocks option isn't implemented.".format(self._pos(formatted=True)))

    def _import_libs(self, imports_cache):

        libspath = '{0} ; {0}/kblibs'.format(self._base_filepath)

        for node in self.code.ast:
            if type(node) is SetConstant and node.constantname == 'libspath':
                if node.value.startswith('/'):
                    libspath += ';' + node.value
                else:
                    libspath += ';' + self._base_filepath + '/' + node.value

        importer = KombuImporter(libspath, imports_cache, self.filename)

        importer.import_(self._toimport)

        self._change_imported_objects_namespaces(importer.new_namespaces)

        self.code.add(importer.imported_code)

    def _change_imported_objects_namespaces(self, new_namespaces):

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
                    node.namespace = new_namespaces[node.name]

            elif type(node) in [WarningTrigger, ErrorTrigger]:
                change_node_namespaces(node.link, new_namespaces)

            elif type(node) in [WarningCatcher, ErrorCatcher]:
                if new_namespaces.get(node.ctx_rule):
                    node.ctx_rule = new_namespaces[node.ctx_rule] + '__' + node.ctx_rule

        for node in self.code.ast:
            if type(node) in [RuleDefinition, WarningCatcher, ErrorCatcher]:
                change_node_namespaces(node, new_namespaces)
            elif type(node) in [UnilineInspection, MultilineInspection] and new_namespaces.get(node.name):
                node.namespace = new_namespaces[node.name]

