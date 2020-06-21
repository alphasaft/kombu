from KomBuInterpreter.KomBuChecker import KomBuChecker
from KomBuInterpreter.TokenClasses import *
from KomBuInterpreter.Kompilers.BaseKompiler import BaseKompiler
from utils import escape_quotes, common, get_rule


TEMPLATE = """
class {0}Parsing(BaseParser):
    def __init__(self):
        BaseParser.__init__(self)

    {3}
    def parse(self, src):
        self.src = src
        self._init_parsing()
        self._init_properties(
{2})
        
        # Call of the awiom rule
        self._{1}_(name='self')
        return self._end_of_parsing()

"""


class KomBuParserKompiler(BaseKompiler):

    def __init__(self):
        self._calls_loops = {}
        BaseKompiler.__init__(self)

    def compile(self, src):
        """Compile the kombu program input into a valid python parser. Return the parser code."""

        self._ast = src
        self._checker.code.ast = self._ast.copy()
        self._calls_loops = self._checker.get_loops()
        self._compiled_python_code = TEMPLATE
        self._compile_ast()

        return self._compiled_python_code, self._properties

    def _compile_ast(self):
        self._indent()
        for node in self._ast:
            self._compile_node(node)
            self._lineo += 1
        self._dedent()

    def _compile_node(self, node):
        if type(node) is SetConstant:
            self._compile_constant_declaration(node)
        elif type(node) is NewLine:
            pass
        elif type(node) is RuleDefinition:
            self._compile_rule_definition(node)
        elif type(node) is RuleCall:
            self._compile_rule_call(node)
        elif type(node) is Match:
            self._compile_string_match(node)
        elif type(node) is OptionalGroup:
            self._compile_optional_group(node)
        elif type(node) is RegexMatch:
            self._compile_regex_match(node)
        elif type(node) is Choices:
            self._compile_choices(node)
        elif type(node) is Group:
            self._compile_group(node)
        elif type(node) is Option:
            self._compile_option(node)
        elif type(node) is ErrorTrigger:
            self._compile_error_trigger(node)
        elif type(node) is WarningTrigger:
            self._compile_warning_trigger(node)

    def _compile_constant_declaration(self, node):
        """Compile a constant declaration. """
        if node.constantname in ['libspath']:
            self._properties[node.constantname] += ' ; ' + node.value
        else:
            self._properties[node.constantname] = node.value

    def _compile_rule_definition(self, node):
        """Compile an rule definition as a method of the parser produced by this compiler."""

        left_calls = self._checker.left_calls(node)
        if common(left_calls, self._calls_loops[node.whole_name]):
            guards = self._find_recursion_guards(node)
            if type(guards) is list:
                self._write("@rule(guards={})".format(replaces(str(guards), '{', '<LCB>', '}', '<RCB>')))
            elif type(guards) is str:
                self._write("@rule(guards='{}')".format(replaces(guards), '{', '<LCB>', '}', '<RCB>'))
        else:
            self._write("@rule()")
        self._write("def _{}_(self):".format(node.whole_name))
        self._indent()
        for subnode in node.definition:
            self._compile_node(subnode)
        self._dedent()
        self._skip_line(1)

    def _compile_rule_call(self, node):
        if node.group_name:
            self._write("self._{}_(name='{}')".format(node.whole_name, node.group_name))
        else:
            self._write("self._{}_()".format(node.whole_name))

    def _find_recursion_guards(self, node, base_rule=None):
        self._checker.code.ast = self._ast

        if type(node) is RuleDefinition:
            definition = get_rule(Code(self._ast), node.whole_name).definition
            guards = None
            i = 1
            while not guards == '{!ARR}' and not guards and i <= len(definition):
                guards = self._find_recursion_guards(definition[-i], base_rule=node.whole_name if not base_rule else base_rule)
                i += 1
            if guards != '{!ARR}':
                return guards
            else:
                return ""

        elif type(node) is Match:
            return escape_quotes(node.string)

        elif type(node) is RegexMatch:
            return 'REGEX~' + node.regex

        elif type(node) is Choices:
            guards = []
            for option in node.options:
                for subnode in option.definition:
                    option_guards = self._find_recursion_guards(subnode, base_rule=base_rule)
                    if type(option_guards) is list:
                        guards += option_guards
                    elif type(option_guards) is str and option_guards != '{!ARR}':
                        guards.append(option_guards)
            return guards

        elif type(node) is RuleCall:
            # If there is left recursives calls, it means this rule'll need recursions guards and cannot be used
            # To set recursions guards for the father rule.
            left_calls = self._checker.left_calls(get_rule(Code(self._ast), node.whole_name))
            if not common(left_calls, self._calls_loops[node.whole_name]) and base_rule not in self._calls_loops[node.whole_name]:
                # Use this recursions guards.
                return self._find_recursion_guards(get_rule(Code(self._ast), node.whole_name))
            else:
                return '{!ARR}'  # Already Recursive Rulecall.

    def _compile_string_match(self, node):
        self._write(("self._match('{}'".format(escape_quotes(node.string)).replace('{', '<LCB>').replace('}', '<RCB>')+(", name='"+node.group_name+"')" if node.group_name else ")"))
                    )

    def _compile_optional_group(self, node):
        self._write("with self._optional("+("name='"+node.group_name+"'):" if node.group_name else '):'))
        self._indent()
        for subnode in node.definition:
            self._compile_node(subnode)
        self._dedent()

    def _compile_regex_match(self, node):
        self._write("self._regex_match('{}'".format(escape_quotes(node.regex)).replace('{', '<LCB>').replace('}', '<RCB>')+(", name='"+node.group_name+"')" if node.group_name else ')'))

    def _compile_group(self, node):
        self._write("with self._group(name='{}'):".format(escape_quotes(node.group_name)))
        self._indent()
        for subnode in node.definition:
            self._compile_node(subnode)
        self._dedent()

    def _compile_choices(self, node):
        self._write("with self._choices("+("name='"+node.group_name+"'):" if node.group_name else '):'))
        self._indent()
        for subnode in node.options:
            self._compile_node(subnode)
        self._dedent()

    def _compile_option(self, node):
        self._skip_line(1)
        self._write("with self._option():")
        self._indent()
        for subnode in node.definition:
            self._compile_node(subnode)
        self._dedent()

    def _compile_error_trigger(self, node):
        if node.group_name is None:
            group_name = 'None'
        else:
            group_name = "'" + escape_quotes(node.group_name) + "'"

        self._write("with self._error_trigger({}, group_name={}, warn=False):".format(node.nb, group_name))
        self._indent()
        self._compile_node(node.link)
        self._dedent()
        self._skip_line(1)

    def _compile_warning_trigger(self, node):
        if node.group_name is None:
            group_name = 'None'
        else:
            group_name = "'" + escape_quotes(node.group_name) + "'"

        self._write("with self._error_trigger({}, group_name={}, warn=True):".format(node.nb, group_name))
        self._indent()
        for subnode in node.link.definition:
            self._compile_node(subnode)
        self._dedent()
