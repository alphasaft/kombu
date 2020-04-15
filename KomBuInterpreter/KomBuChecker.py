from KomBuInterpreter.KomBuParser import KomBuParser, KomBuGrammarError
from KomBuInterpreter.TokenClasses import *
from utils import common, split, time_alert


class KomBuChecker:

    def __init__(self, parser=KomBuParser):
        self.parser = parser()
        self.lineo = 1
        self.code = Code()
        self._current_inpected_rule = None
        self._calls_loops = {}

    def get_rule(self, rule_name):
        """Returns the asked rule definition."""
        rules = [r for r in self.code.ast if type(r) is RuleDefinition]
        for rule in rules:
            if rule.name == rule_name:
                return rule

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
                return [node.name]

            else:
                return []

        loops = {}

        rules = [r for r in self.code.ast if type(r) is RuleDefinition]
        for rule in rules:

            loops[rule.name] = []
            calls = rulecalls_of(rule)

            for call in calls:

                subcalls = rulecalls_of(self.get_rule(call))
                calls_trace = subcalls.copy()
                while subcalls and rule.name not in subcalls:

                    new_subcalls = []
                    for subcall in subcalls:
                        new_subcalls += rulecalls_of(self.get_rule(subcall))
                    subcalls = [c for c in new_subcalls.copy() if c not in calls_trace]
                    calls_trace += new_subcalls.copy()

                if rule.name in subcalls:
                    loops[rule.name].append(call)

        return loops

    def left_calls(self, rule):

        def get_left_calls(node):

            if type(node) is Choices:
                left_calls = []
                for option in node.options:
                    left_calls += get_left_calls(option)
                return left_calls

            elif type(node) in [Option, RuleDefinition, OptionalGroup]:
                left_calls = []

                for subnode in node.definition:
                    if type(subnode) is RuleCall:
                        return left_calls + [subnode.name]

                    elif type(subnode) in [Match, RegexMatch]:
                        return left_calls

                    elif type(subnode) is Choices:
                        return left_calls + get_left_calls(subnode)

                    elif type(subnode) is OptionalGroup:
                        left_calls += get_left_calls(subnode)

        return get_left_calls(rule)

    def left_recursive_calls(self, rule):
        return common(self._calls_loops[rule], self.left_calls(rule))

    def check(self, src, base_filepath, filename):
        self.__init__()
        self.code = self.parser.parse(src, base_filepath, filename)
        self._calls_loops = self.get_loops()
        for node in self.code.ast:
            self._check_node(node)
            self.lineo += 1

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
        elif type(node) is RawPythonCode:
            pass
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
            raise KomBuGrammarError("Error in the checker code.")

    def _check_rule_definition(self, node):
        assert type(node) is RuleDefinition, "Error in the Checker code."
        self._check_left_recursive_loop(node)
        for subnode in node.definition:
            self._check_node(subnode)

    def _check_constant_declaration(self, node):
        assert type(node) is SetConstant, "Error in the Checker code."
        if node.constantname == 'axiom':
            self._check_option_value(node, True)
            found = self.get_rule(node.value)
            assert found, "Line {} : Axiom is defined by {}, but that rule doesn't exist.".format(self.lineo, node.value)
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
            raise KomBuGrammarError("Line {} : '{}' isn't an option name.".format(self.lineo, node.constantname))

    def _check_option_value(self, node, expected_value):
        if expected_value:
            assert type(node.value) is str, "Line {} : '{}' option should have a value.".format(self.lineo, node.constantname)
        else:
            assert type(node.value) is bool, "Line {} : '{}' option shouldn't have a value".format(self.lineo, node.constantname)

    def _check_optional_group(self, node):
        assert type(node) is OptionalGroup, "Error in the checker code."
        assert len(node.definition) > 0, "Line {} : Optional group cannot be empty.".format(self.lineo)
        assert not (len(node.definition) == 1 and type(node.definition[0]) == OptionalGroup), \
            "Line {} : Optional group cannot be defined directly inside an other optional group.".format(self.lineo)
        for subnode in node.definition:
            self._check_node(subnode)

    def _check_uniline_inspection(self, node):
        assert type(node) is UnilineInspection, "Error in the checker code."
        self._current_inpected_rule = self.get_rule(node.name)
        if not self.get_rule(node.name):
            raise KomBuGrammarError("Line {} : 'inspect {}' : Cannot define an inspection on a not-existing rule."
                                    .format(self.lineo, node.name))

        for node in [n for n in node.definition if type(n) in [NodeCall]]:
            self._check_node(node)

    def _check_multiline_inspection(self, node):
        assert type(node) is MultilineInspection, "Error in the checker code."
        self._current_inpected_rule = self.get_rule(node.name)
        if not self._current_inpected_rule:
            raise KomBuGrammarError("Line {} : 'inspect {}' : Cannot define an inspection on a not-existing rule."
                                    .format(self.lineo, node.name))

        inspection_definition = split(node.definition, NewLine(), include_at_beginning=True)[1:]
        base_indentation = len(inspection_definition[0][0].indentation.replace('\t', ' '*16))
        for i, line in enumerate(inspection_definition):
            indentation = len(line[0].indentation.replace('\t', ' '*16))
            if indentation < base_indentation and len(line) > 1:
                raise KomBuGrammarError("Line {} : This line is under-indented.".format(self.lineo + i + 1))

        self.lineo += len(node.definition)

    def _check_node_call(self, node):
        pass  # How to check a nodecall ?

    def _check_choices(self, node):
        assert type(node) is Choices, "Error in the checker code."
        assert len(node.options) > 1, "Line {} : Choices groups have to comport at least 2 options.".format(self.lineo)
        for subnode in node.options:
            assert type(subnode) is Option, "Error in the parser code."
            assert not (len(subnode.definition) == 1 and type(subnode.definition[0]) is OptionalGroup), \
                "Line {} : Optional group cannot be directly defined as an option. Just set the choices group in the" \
                " optional group.".format(self.lineo)
            assert not (len(subnode.definition) == 1 and type(subnode.definition[0]) is Choices), \
                "Line {} : Choices group cannot be directly defined as an option. Use its options directly as options" \
                " of the father choices group.".format(self.lineo)
            for def_part in subnode.definition:
                self._check_node(def_part)

    def _check_rulecall(self, node):
        """Check that the rule call is a reference to an existing rule, und that it won't provoke an endless recursion
         loop."""
        assert type(node) is RuleCall, "Error in the checker code."
        self._check_rule_exist(node)

    def _check_rule_exist(self, node):
        if not self.get_rule(node.name):
            raise KomBuGrammarError("Line {} : '{}' : Trying to invoke a not-existing rule.".format(self.lineo,
                                                                                          '<'+node.name+'>'))

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
                        return self.get_rule(node.name)
                    return None

        left_recursive_call = find_left_recursive_rule_call(node)
        while left_recursive_call:
            if left_recursive_call.name == node.name:
                raise KomBuGrammarError("Line {} : This rule definition'll provoke an endless recursive loop."
                                        .format(self.lineo))
            else:
                left_recursive_call = find_left_recursive_rule_call(left_recursive_call)


a = KomBuChecker()
