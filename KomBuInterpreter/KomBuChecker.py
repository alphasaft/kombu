from exceptions import KombuError
from KomBuInterpreter.KomBuParser import KomBuParser
from KomBuInterpreter.TokenClasses import *
from utils import common, split, get_rule


class KomBuChecker:

    def __init__(self, parser=KomBuParser):
        self.parser = parser()
        self.code = Code()
        self._current_inspected_rule = None
        self._calls_loops = {}

    def _find_node(self, condition, rule=None, expected=1):
        def search_in(node, condition):
            found = []
            if condition(node):
                found.append(node)

            if type(node) in [RuleDefinition, OptionalGroup, Option]:
                for subnode in node.definition:
                    result = search_in(subnode, condition)
                    if result:
                        found.extend(result)

            elif type(node) is Choices:
                for option in node.options:
                    result = search_in(option, condition)
                    if result:
                        found.extend(result)

            elif type(node) in [WarningTrigger, ErrorTrigger]:
                found.extend(search_in(node.link, condition))

            return found

        if rule:
            result = search_in(get_rule(self.code, rule), condition)
        else:
            result = []
            for rule in [r for r in self.code.ast if type(r) is RuleDefinition]:
                result.extend(search_in(rule, condition))

        if expected == 0:
            return result
        elif expected == 1:
            return result[0] if result else None
        else:
            return result[:expected] if len(result) >= expected else None

    def get_loops(self):
        """Return the recursives loops in the rules definitions of the source AST. For example, a rule A which calls to
        a rule B provokes a recursive loop if that rule B calls the rule A."""

        def rulecalls_of(node):

            if type(node) is RuleDefinition:
                rulecalls = []
                for subnode in node.definition:
                    rulecalls += rulecalls_of(subnode)
                return rulecalls

            elif type(node) is Choices:
                rulecalls = []
                for option in node.options:
                    for subnode in option.definition:
                        rulecalls += rulecalls_of(subnode)
                return rulecalls

            elif type(node) is OptionalGroup:
                rulecalls = []
                for subnode in node.definition:
                    rulecalls += rulecalls_of(subnode)
                return rulecalls

            elif type(node) is RuleCall:
                return [node.whole_name]

            else:
                return []

        loops = {}

        rules = [r for r in self.code.ast if type(r) is RuleDefinition]
        for rule in rules:

            loops[rule.whole_name] = []
            calls = rulecalls_of(rule)

            for call in calls:

                subcalls = rulecalls_of(get_rule(self.code, call))
                calls_trace = subcalls.copy()
                while subcalls and rule.whole_name not in subcalls:

                    new_subcalls = []
                    for subcall in subcalls:
                        new_subcalls += rulecalls_of(get_rule(self.code, subcall))
                    subcalls = [c for c in new_subcalls.copy() if c not in calls_trace]
                    calls_trace += new_subcalls.copy()

                if rule.whole_name in subcalls:
                    loops[rule.whole_name].append(call)

        return loops

    def left_calls(self, rule):
        def get_left_calls(node):

            if type(node) is Choices:
                left_calls = []
                for option in node.options:
                    left_calls += get_left_calls(option)
                return left_calls

            elif type(node) in [Option, RuleDefinition, OptionalGroup, Group]:
                left_calls = []

                for subnode in node.definition:
                    if type(subnode) is RuleCall:
                        return left_calls + [subnode.whole_name]

                    elif type(subnode) in [Match, RegexMatch]:
                        return left_calls

                    elif type(subnode) is Choices:
                        return left_calls + get_left_calls(subnode)

                    elif type(subnode) is OptionalGroup:
                        left_calls += get_left_calls(subnode)

                    elif type(subnode) is Group:
                        return left_calls + get_left_calls(subnode)

                    elif type(subnode) is ErrorTrigger:
                        return left_calls + get_left_calls(subnode.link)

            elif type(node) is ErrorTrigger:
                left_calls = []
                return left_calls + get_left_calls(node.link)

            elif type(node) in [Match, RegexMatch]:
                return []

        return get_left_calls(rule)

    def left_recursive_calls(self, rule):
        return common(self._calls_loops[rule], self.left_calls(rule))

    def formatted_pos(self, pos):
        return "In {}, at {}".format(pos[0], pos[1:])

    def check(self, src, base_filepath, filename):
        self.__init__()
        self.code = self.parser.parse(src, base_filepath, filename, {filename[:-3]: None})
        self.filename = filename
        self._calls_loops = self.get_loops()
        for node in self.code.ast:
            self._check_node(node)

        print([n.code.replace(' ', '[s]') for n in self.code.ast if isinstance(n, RawPythonCode)])
        return self.code

    def _check_node(self, node):
        if type(node) is RuleDefinition:
            self._check_rule_definition(node)
        elif type(node) is SetConstant:
            self._check_constant_declaration(node)
        elif type(node) is OptionalGroup:
            self._check_optional_group(node)
        elif type(node) is Choices:
            self._check_choices(node)
        elif type(node) is RuleCall:
            self._check_rulecall(node)
        elif type(node) is UnilineInspection:
            self._check_uniline_inspection(node)
        elif type(node) is MultilineInspection:
            self._check_multiline_inspection(node)
        elif type(node) is NodeCall:
            self._check_node_call(node)
        elif type(node) is Import or type(node) is FromImport:
            self._check_import(node)
        elif type(node) is Group:
            self._check_group(node)
        elif type(node) in [WarningTrigger, ErrorTrigger]:
            self._check_error_or_warning_trigger(node)
        elif type(node) is WarningCatcher:
            self._check_warning_catcher(node)
        elif type(node) is ErrorCatcher:
            self._check_error_catcher(node)
        elif type(node) is RawPythonCode:
            print(node.code.replace(' ', '[s]'))
        elif type(node) is Match:
            pass
        elif type(node) is NewLine:
            pass
        elif type(node) is RegexMatch:
            pass
        elif type(node) is BeforeBlock:
            pass
        elif type(node) is AfterBlock:
            pass
        else:
            raise KombuError("Error in the checker code.")

    def _check_rule_definition(self, node):
        assert type(node) is RuleDefinition, "Error in the Checker code."
        self._check_left_recursive_loop(node)
        self._current_inspected_rule = node
        for subnode in node.definition:
            self._check_node(subnode)

    def _check_constant_declaration(self, node):
        assert type(node) is SetConstant, "Error in the Checker code."
        if node.constantname == 'axiom':
            self._check_option_value(node, True)
            found = get_rule(self.code, node.value)
            assert found, "{} : Axiom is defined by {}, but that rule doesn't exist.".format(self.formatted_pos(node.pos), node.value)
        elif node.constantname == 'libspath':
            self._check_option_value(node, True)
        elif node.constantname == 'name':
            self._check_option_value(node, True)
        elif node.constantname == 'keep_whitespaces':
            self._check_option_value(node, False)
        elif node.constantname == 'cut_end':
            self._check_option_value(node, False)
        elif node.constantname == 'get_time':
            self._check_option_value(node, False)
        elif node.constantname == 'show_ast':
            self._check_option_value(node, False)
        else:
            raise KombuError("{} : '{}' isn't an option name.".format(self.formatted_pos(node.pos), node.constantname))

    def _check_option_value(self, node, expected_value):
        if expected_value:
            assert type(node.value) is str, "{} : '{}' option should have a value.".format(self.formatted_pos(node.pos), node.constantname)
        else:
            assert type(node.value) is bool, "{} : '{}' option shouldn't have a value".format(self.formatted_pos(node.pos), node.constantname)

    def _check_group(self, node):
        for subnode in node.definition:
            self._check_node(subnode)

    def _check_optional_group(self, node):
        assert type(node) is OptionalGroup, "Error in the checker code."
        assert len(node.definition) > 0, "{} : Optional group cannot be empty.".format(self.formatted_pos(node.pos))
        assert not (len(node.definition) == 1 and type(node.definition[0]) == OptionalGroup), \
            "{} : Optional group cannot be defined directly inside an other optional group.".format(self.formatted_pos(node.pos))
        for subnode in node.definition:
            self._check_node(subnode)

    def _check_uniline_inspection(self, node):
        assert type(node) is UnilineInspection, "Error in the checker code."
        self._current_inspected_rule = get_rule(self.code, node.whole_name)
        if not get_rule(self.code, node.whole_name):
            raise KombuError("{} : 'inspect {}' : Cannot define an inspection on a not-existing rule."
                                    .format(self.formatted_pos(node.pos), node.name))

        for node in [n for n in node.definition if type(n) in [NodeCall]]:
            self._check_node(node)

    def _check_multiline_inspection(self, node):
        assert type(node) is MultilineInspection, "Error in the checker code."
        self._current_inspected_rule = get_rule(self.code, node.whole_name)
        if not self._current_inspected_rule:
            raise KombuError("{} : 'inspect {}' : Cannot define an inspection on a not-existing rule."
                                    .format(self.formatted_pos(node.pos), node.name))

        inspection_definition = split(node.definition, NewLine(), include_at_beginning=True)[1:]
        base_indentation = len(inspection_definition[0][0].indentation.replace('\t', ' '*16))
        for i, line in enumerate(inspection_definition):
            indentation = len(line[0].indentation.replace('\t', ' '*16))
            if indentation < base_indentation and len(line) > 1:
                raise KombuError("{} : This line is under-indented.".format(self.formatted_pos(line[0].pos) + i + 1))

    def _check_node_call(self, node):
        pass  # How to check a nodecall ?

    def _check_choices(self, node):
        assert type(node) is Choices, "Error in the checker code."
        assert len(node.options) > 1, "{} : Choices groups have to comport at least 2 options.".format(self.formatted_pos(node.pos))
        for subnode in node.options:
            assert type(subnode) is Option, "Error in the parser code."
            assert not (len(subnode.definition) == 1 and type(subnode.definition[0]) is OptionalGroup), \
                "{} : Optional group cannot be directly defined as an option. Just set the choices group in the" \
                " optional group.".format(self.formatted_pos(subnode.pos))
            assert not (len(subnode.definition) == 1 and type(subnode.definition[0]) is Choices), \
                "{} : Choices group cannot be directly defined as an option. Use its options directly as options" \
                " of the father choices group.".format(self.formatted_pos(subnode.pos))
            for def_part in subnode.definition:
                self._check_node(def_part)

    def _check_rulecall(self, node):
        """Check that the rule call is a reference to an existing rule, und that it won't provoke an endless recursion
         loop."""
        assert type(node) is RuleCall, "Error in the checker code."
        self._check_rule_exist(node.name)

    def _check_rule_exist(self, rule):
        if rule not in [r.name for r in self.code.ast if type(r) is RuleDefinition]:
            raise KombuError("'<{}>' : Trying to invoke a non-existing rule.".format(rule))

    def _check_left_recursive_loop(self, node):
        """Check that this rule definition won't provoke an endless recursive loop by rule calls.
         Raises an KomBuGrammarError if so."""

        def find_left_recursive_rule_call(rule):
            for node in rule.definition:
                if type(node) is Match:
                    return None
                elif type(node) is Choices:
                    for option in node.options:
                        for subnode in option.definition:
                            if type(subnode) is Match:
                                return None
                elif type(node) is RuleCall:
                    if not [s for s in rule.definition if type(s) is Match]:
                        return get_rule(self.code, node.whole_name)
                    return None

        left_recursive_call = find_left_recursive_rule_call(node)
        while left_recursive_call:
            if left_recursive_call.whole_name == node.whole_name:
                raise KombuError("{} : This rule definition'll provoke an endless recursive loop."
                                        .format(self.formatted_pos(node.pos)))
            else:
                left_recursive_call = find_left_recursive_rule_call(left_recursive_call)

    def _check_error_or_warning_trigger(self, node):
        if self._find_node(lambda n: type(n) in [WarningTrigger, ErrorTrigger] and n.nb == node.nb,
                           rule=self._current_inspected_rule.whole_name, expected=2):
            raise SyntaxError("{} : '!{}' : Cannot define several times the same error trigger"
                              " in the same rule".format(self.formatted_pos(node.pos), node.nb))

        self._check_node(node.link)

    def _check_error_catcher(self, node):
        def check_args(e_catcher, expected):
            if len(e_catcher.args) > expected:
                raise ValueError("{} : '{}' : To many arguments for the error ; type !{} expects {} arguments"
                                 .format(self.formatted_pos(e_catcher.args[expected].pos),
                                         e_catcher.args[expected].value, e_catcher.etype, expected))
            if len(e_catcher.args) < expected:
                raise ValueError('{} : To few arguments for the error : type !{} expects {} arguments'
                                 .format(self.formatted_pos(e_catcher.pos), e_catcher.etype, expected))

        if node.etype == "generated":
            check_args(node, 1)
            if not self._find_node(lambda n: type(n) is ErrorTrigger and n.nb == node.arg(0).value, rule=node.ctx_rule):
                raise ValueError("{} : catch !{} in {} : Cannot try to catch an error that won't be "
                                 "raised.".format(self.formatted_pos(node.pos), node.arg(0).value,
                                                    node.ctx_rule.split('__')[-1]))

        elif node.etype == "missing":
            check_args(node, 1)
            if node.arg(0).type == "string":
                found = self._find_node(lambda n: type(n) is Match and n.string == node.arg(0).value, rule=node.ctx_rule)
            elif node.arg(0).type == 'regex':
                found = self._find_node(lambda n: type(n) is RegexMatch and n.pattern == node.arg(0).value, rule=node.ctx_rule)
            else:
                raise KombuError("{} : Pattern or string expected after !missing, not {}"
                                 .format(self.formatted_pos(node.arg(0).pos), node.arg(0).type))

            if not found:
                raise KombuError("{} : Define a catcher on a !missing error that cannot be raised."
                                 .format(self.formatted_pos(node.pos)))

        elif node.etype == "failed":
            check_args(node, 1)
            if not node.arg(0).type == 'ident':
                raise KombuError("{} : Rule name expected for error !failed, not {}"
                                 .format(self.formatted_pos(node.pos), node.arg(0).type))

            if not self._find_node(lambda n: type(n) is RuleCall and n.name == node.arg(0).value, rule=node.ctx_rule):
                raise KombuError("{} : catch !failed {} : Cannot find a call to that rule in {}"
                                 .format(self.formatted_pos(node.pos), node.arg(0).value, node.ctx_rule))

        else:
            raise NameError("{} : catch !{} : Invalid error name.".format(self.formatted_pos(node.pos), node.etype))

    def _check_warning_catcher(self, node):
        # Looking for an WarningTrigger that have self.nb = our_warning_catcher.nb
        if not self._find_node(lambda n: type(n) is WarningTrigger and n.nb == node.nb, rule=node.ctx_rule):
            raise NameError("{} : catch !{} in {} : Cannot try to catch a warning if that warning doesn't"
                            " exist.".format(self.formatted_pos(node.pos), node.nb, node.ctx_rule.split('__')[-1]))


a = KomBuChecker()
