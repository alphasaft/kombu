from utils import replaces


class BaseToken(object):

    def _getattrs(self):
        attrs = []
        for attr in self.__dir__():
            if attr[:2] == '__' and attr[-2:] == '__':
                break
            else:
               attrs.append(getattr(self, attr))
        return attrs

    def _gettokentype(self):
        raw_classname = str(self.__class__)
        classname = ""
        i = -3
        while raw_classname[i].isalnum():
            classname = raw_classname[i] + classname
            i -= 1
        return classname

    def __repr__(self):
        return '< '+self._gettokentype()+' '+replaces(str(self._getattrs()), '[', '', ']', '')+' >'


class EOF(BaseToken):
    def __eq__(self, other):
        return type(other) is EOF


class EOL(BaseToken):
    def __eq__(self, other):
        return type(other) is EOL


class Code(BaseToken):
    def __init__(self):
        self.ast = []

    def add(self, block):
        if type(block) is list:
            self.ast += block
        elif type(block) is Code:
            self.ast += block.ast
        elif block:
            self.ast.append(block)


class SetConstant(BaseToken):
    def __init__(self, constantname, value):
        self.constantname = constantname
        self.value = value


class Import(BaseToken):
    def __init__(self, toimport):
        self.toimport = toimport


class FromImport(BaseToken):
    def __init__(self, toimport, from_file):
        self.toimport = toimport
        self.from_file = from_file


class Choices(BaseToken):
    def __init__(self):
        self.options = []
        self.group_name = 'self'

    def __add__(self, other):
        assert type(other) is Option, TypeError("must be Option, not {}".format(str(other.__class__).split('.')[-1][:-3]))
        self.options.append(other)
        return self


class Option(BaseToken):
    def __init__(self):
        self.definition = []

    def add_code(self, definition):
        self.definition.append(definition)


class RuleCall(BaseToken):
    def __init__(self, name, namespace, group_name=None):
        self.name = name
        self.namespace = namespace
        self.group_name = group_name

    def whole_name(self):
        return self.namespace + '__' + self.name


class OptionalGroup(BaseToken):
    def __init__(self, definition):
        self.definition = definition
        self.group_name = 'self'


class RuleDefinition(BaseToken):
    def __init__(self, name, namespace, definition, error_handlers):
        self.name, self.namespace, self.definition, self.error_handlers = name, namespace, definition, error_handlers

    def whole_name(self):
        return self.namespace + '__' + self.name


class RegexMatch(BaseToken):
    def __init__(self, regex):
        self.regex = regex
        self.group_name = None


class Match(BaseToken):
    def __init__(self, string):
        self.string = string
        self.group_name = None


class UnilineInspection(BaseToken):
    def __init__(self, name, definition):
        self.name = name
        self.definition = definition


class MultilineInspection(BaseToken):
    def __init__(self, name, definition):
        self.name = name
        self.definition = definition


class RawPythonCode(BaseToken):
    def __init__(self, code):
        self.code = code + ' ' if code[-1:].isalpha() else code


class NodeCall(BaseToken):
    def __init__(self):
        self.node_path = []


class NewLine(BaseToken):
    def __init__(self, indentation=''):
        self.indentation = indentation

    def __eq__(self, other):
        return type(other) is NewLine


class BeforeBlock(BaseToken):
    def __init__(self):
        self.code = []


class AfterBlock(BaseToken):
    def __init__(self):
        self.code = []


class GlobalVar(BaseToken):
    def __init__(self, name):
        self.name = name


class ErrorHandlersStacker(BaseToken):
    def __init__(self):
        self.error_handlers = []

    def add_error_handler(self, error_handler):
        self.error_handlers.append(error_handler)


class ErrorHandler(BaseToken):
    def __init__(self, type, error_msg, **args):
        self.error_type = type
        self.args = args
        self.error_msg = error_msg


class ImportBlock(BaseToken):
    def __init__(self, main_rule, dependencies):
        self.main_rule, self.dependencies = main_rule, dependencies