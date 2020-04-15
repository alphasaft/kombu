from KomBuInterpreter.TokenClasses import *
from KomBuInterpreter.KomBuChecker import KomBuChecker
from KomBuInterpreter.KomBuLexer import KomBuGrammarError


class KombuImporter:
    def __init__(self, libspath):
        self.imported_code = Code()
        self.libspath = libspath

    def import_lib(self, lib_name):

        to_parse, directory_path = self._open_lib_file(lib_name)

        # Import is done here because else it provokes an recursive imports loop.
        from KomBuInterpreter.KomBuChecker import KomBuChecker

        imported_libs_checker = KomBuChecker()
        self.imported_code.add([e for e in imported_libs_checker.check(to_parse, directory_path, lib_name+'.kb').ast if type(e) in [RuleDefinition, UnilineInspection, MultilineInspection]])

    def import_rules_from_lib(self, lib_name, rules):

        to_parse, directory_path = self._open_lib_file(lib_name)

        imported_libs_checker = KomBuChecker()
        imported_code = imported_libs_checker.check(to_parse, directory_path, lib_name+'.kb')

        for rule_to_import in rules:
            if not imported_libs_checker.get_rule(rule_to_import):
                raise NameError("'with {} from {}' : Cannot import {} from file {}.kb".format(", ".join(rules), lib_name, rule_to_import, lib_name))

        for node in imported_code.ast:
            if type(node) is RuleDefinition and node.name in rules:

                dependencies = self._dependencies_of(node, imported_libs_checker)
                for dependencies_node in imported_code.ast:
                    if type(dependencies_node) is RuleDefinition and dependencies_node.name in dependencies:
                        self._import_inspection(imported_code, dependencies_node.name, rename=lib_name)
                        dependencies_node.name = lib_name + '__' + dependencies_node.name
                        self.imported_code.add(self._rename_rulecalls(dependencies_node, lib_name))

                self.imported_code.add(RuleDefinition(name=node.name, namespace=node.namespace, definition=[RuleCall(lib_name + '__' + node.name, 'self')], error_handlers=None))
                self._import_inspection(imported_code, node.name)
                node.name = lib_name + '__' + node.name
                self.imported_code.add(self._rename_rulecalls(node, lib_name))

    def _rename_rulecalls(self, node, lib_name):

        if type(node) is RuleDefinition:
            return RuleDefinition(node.name, node.namespace, [self._rename_rulecalls(subnode, lib_name) for subnode in node.definition], node.error_handlers)

        elif type(node) is Choices:
            renamed_choices = Choices()
            for option in node.options:
                renamed_option = Option()
                for subnode in option.definition:
                    renamed_option.add_code(self._rename_rulecalls(subnode, lib_name))
                renamed_choices += renamed_option
            return renamed_choices

        elif type(node) is OptionalGroup:
            return OptionalGroup([self._rename_rulecalls(subnode, lib_name) for subnode in node.definition])

        elif type(node) is RuleCall:
            return RuleCall(lib_name + '__' + node.name, node.group_name)

        else:
            return node

    def _import_inspection(self, code, inspection_name, rename=None):
        for node in code.ast:
            if type(node) in [UnilineInspection, MultilineInspection] and node.name == inspection_name:
                if rename:
                    node.name = rename + '__' + node.name
                self.imported_code.add(node)

    def _open_lib_file(self, filename):
        """Search the provided file name in all paths in the libspath property. If it founds it, returns the code
         inside, else raises an error."""

        f = None
        path = None
        for path in self.libspath.split(';'):
            path = path.strip()
            try:
                f = open(path + '/' + filename + '.kb', 'r')
                break
            except FileNotFoundError:
                continue

        if not f:
            raise KomBuGrammarError("'with {0}': The kombu file '{0}.kb' cannot be found".format(filename))

        result = ""
        for line in f.read():
            result += line

        return result, path

    def _dependencies_of(self, node, import_checker):

        def direct_dependencies_of(node):
            dependencies = []

            if type(node) is RuleDefinition:
                for subnode in node.definition:
                    dependencies += direct_dependencies_of(subnode)

            elif type(node) is Choices:
                for option in node.options:
                    for subnode in option.definition:
                        dependencies += direct_dependencies_of(subnode)

            elif type(node) is OptionalGroup:
                for subnode in node.definition:
                    dependencies += direct_dependencies_of(subnode)

            elif type(node) is RuleCall:
                dependencies += [node.name]

            else:
                pass

            return dependencies

        direct_dependencies = direct_dependencies_of(node)
        dependencies = direct_dependencies.copy()
        dependencies_trace = []
        while direct_dependencies:
            direct_dependencies = []

            for dependence in [call for call in dependencies if not call in dependencies_trace + [node.name]]:
                direct_dependencies += direct_dependencies_of(import_checker.get_rule(dependence))
                dependencies_trace += [dependence]

            dependencies += direct_dependencies

        return dependencies

    def clean_imported_code(self):
        imported_rules = []
        imported_inspections = []
        for i, rule in enumerate(self.imported_code.ast):
            if type(rule) is RuleDefinition:
                if rule.name not in imported_rules:
                    imported_rules.append(rule.name)
                else:
                    del self.imported_code.ast[i]
            elif type(rule) in [MultilineInspection, UnilineInspection]:
                if rule.name not in imported_inspections:
                    imported_inspections.append(rule.name)
                else:
                    del self.imported_code[i]
