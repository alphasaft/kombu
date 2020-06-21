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
    def __init__(self, pos):
        self.pos = pos

    @classmethod
    def equals(cls, other):
        return type(other) is EOF


class Code(BaseToken):
    def __init__(self, ast=None):
        self.ast = [] if ast is None else ast

    def add(self, block):
        if type(block) is list:
            self.ast += block
        elif type(block) is Code:
            self.ast += block.ast
        elif block:
            self.ast.append(block)


class SetConstant(BaseToken):
    def __init__(self, constantname, value, pos):
        self.constantname = constantname
        self.value = value
        self.pos = pos


class Import(BaseToken):
    def __init__(self, toimport, pos):
        self.toimport = toimport
        self.pos = pos


class FromImport(BaseToken):
    def __init__(self, toimport, from_file, pos):
        self.toimport = toimport
        self.from_file = from_file
        self.pos = pos


class Group(BaseToken):
    def __init__(self, definition, group_name, pos):
        self.definition = definition
        self.group_name = group_name
        self.pos = pos


class Choices(BaseToken):
    def __init__(self, pos):
        self.options = []
        self.group_name = 'self'
        self.pos = pos

    def __add__(self, other):
        assert type(other) is Option, TypeError("must be Option, not {}".format(str(other.__class__).split('.')[-1][:-3]))
        self.options.append(other)
        return self


class Option(BaseToken):
    def __init__(self, pos):
        self.definition = []
        self.pos = pos

    def add_code(self, definition):
        self.definition.append(definition)


class RuleCall(BaseToken):
    def __init__(self, name, namespace, pos, group_name=None):
        self.name = name
        self.namespace = namespace
        self.group_name = group_name
        self.pos = pos

    @property
    def whole_name(self):
        return self.namespace + '__' + self.name


class OptionalGroup(BaseToken):
    def __init__(self, definition, pos):
        self.definition = definition
        self.group_name = 'self'
        self.pos = pos


class RuleDefinition(BaseToken):
    def __init__(self, name, namespace, definition, pos):
        self.name, self.namespace, self.definition = name, namespace, definition
        self.pos = pos

    @property
    def whole_name(self):
        return self.namespace + '__' + self.name


class RegexMatch(BaseToken):
    def __init__(self, regex, pos):
        self.regex = regex
        self.group_name = None
        self.pos = pos


class Match(BaseToken):
    def __init__(self, string, pos):
        self.string = string
        self.group_name = None
        self.pos = pos


class UnilineInspection(BaseToken):
    def __init__(self, name, namespace, definition, pos):
        self.name = name
        self.namespace = namespace
        self.definition = definition
        self.pos = pos

    @property
    def whole_name(self):
        return self.namespace + '__' + self.name


class MultilineInspection(BaseToken):
    def __init__(self, name, namespace, definition, pos):
        self.name = name
        self.namespace = namespace
        self.definition = definition
        self.pos = pos

    @property
    def whole_name(self):
        return self.namespace + '__' + self.name


class RawPythonCode(BaseToken):
    def __init__(self, code, pos):
        self.code = code + ' ' if code[-1:].isalpha() else code
        self.pos = pos


class NodeCall(BaseToken):
    def __init__(self, pos):
        self.node_path = []
        self.pos = pos


class NewLine(BaseToken):
    def __init__(self, pos=("-", 1, 1), indentation=''):
        self.indentation = indentation
        self.pos = pos

    def __eq__(self, other):
        return type(other) is NewLine


class BeforeBlock(BaseToken):
    def __init__(self, pos):
        self.code = []
        self.pos = pos


class AfterBlock(BaseToken):
    def __init__(self, pos):
        self.code = []
        self.pos = pos


class GlobalVar(BaseToken):
    def __init__(self, name, pos):
        self.name = name
        self.pos = pos


class ImportBlock(BaseToken):
    def __init__(self, main_rule, dependencies, pos):
        self.main_rule, self.dependencies = main_rule, dependencies
        self.pos = pos


class ErrorTrigger(BaseToken):
    def __init__(self, nb, link, pos):
        """
        NB is the reference to the generated error.
        LINK is the part of the rule definition the trigger is bound to.
        """
        self.nb = nb
        self.link = link
        self.group_name = link.group_name
        self.pos = pos


class WarningTrigger(BaseToken):
    def __init__(self, nb, link, pos):
        """
        NB is the reference to the generated error.
        LINK is the part of the rule definition the trigger is bound to.
        """
        self.nb = nb
        self.link = link
        self.group_name = link.group_name
        self.pos = pos


class ErrorCatcher(BaseToken):
    def __init__(self, msg, etype, ctx_rule, args, pos):
        self.msg = msg
        self.etype = etype
        self.ctx_rule = ctx_rule
        self.args = args
        self.pos = pos

    def arg(self, n):
        return self.args[n]


class ErrorCatcherArg(BaseToken):
    def __init__(self, atype, value, pos):
        self.type = atype
        self.value = value
        self.pos = pos


class WarningCatcher(BaseToken):
    def __init__(self, msg, ctx_rule, nb, pos):
        self.msg = msg
        self.ctx_rule = ctx_rule
        self.nb = nb
        self.pos = pos
