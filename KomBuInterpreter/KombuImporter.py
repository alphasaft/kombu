from KomBuInterpreter.TokenClasses import *
from KomBuInterpreter.KomBuLexer import KombuError
from utils import get_rule


class KombuImporter:
    def __init__(self, libspath, imports_cache, filename):
        self.imported_code = Code()
        self.libspath = libspath
        self.filename = filename
        self.imports_cache = imports_cache
        self.new_namespaces = {}

    def import_(self, imports_list):
        for toimport in imports_list:
            if type(toimport) is Import and toimport.toimport not in self.imports_cache.keys():
                self.import_lib(toimport.toimport)
            elif type(toimport) is Import:

                cached_code = self.imports_cache.get(toimport.toimport)
                if cached_code:
                    for rule in [r for r in cached_code.ast if type(r) is RuleDefinition]:
                        self.new_namespaces[rule] = toimport.toimport

            elif type(toimport) is FromImport and toimport.from_file not in self.imports_cache.keys():
                self.import_rules_from_lib(toimport.from_file, toimport.toimport)

            elif type(toimport) is FromImport:
                for rule in toimport.toimport:
                    cached_code = self.imports_cache.get(toimport.from_file)
                    if cached_code and not get_rule(cached_code, toimport.from_file+'__'+rule):
                        raise NameError("File {} : 'with {} from {}' : Cannot import {} from file {}.kb".format(
                            self.filename, ", ".join(toimport.toimport), toimport.from_file, rule, toimport.from_file
                        ))
                    else:
                        self.new_namespaces[rule] = toimport.from_file

    def import_lib(self, lib_name):

        to_parse, directory_path = self._open_lib_file(lib_name)

        # Import is done here because else it provokes an recursive imports loop.
        from KomBuInterpreter.KomBuParser import KomBuParser

        imported_libs_parser = KomBuParser()
        imported_code = Code()
        imported_code.add([e for e in imported_libs_parser.parse(to_parse, directory_path, lib_name+'.kb', self.imports_cache).ast if type(e) in [RuleDefinition, UnilineInspection, MultilineInspection]])

        for rule in [r for r in imported_code.ast if type(r) is RuleDefinition]:
            self.new_namespaces[rule.whole_name] = lib_name

        self.imported_code.add(imported_code)
        self.imports_cache[lib_name] = imported_code

    def import_rules_from_lib(self, lib_name, rules):

        to_parse, directory_path = self._open_lib_file(lib_name)

        from KomBuInterpreter.KomBuParser import KomBuParser
        from KomBuInterpreter.KomBuChecker import KomBuChecker

        imported_libs_parser = KomBuParser()
        imported_code = imported_libs_parser.parse(to_parse, directory_path, lib_name+'.kb', self.imports_cache)

        for rule_to_import in rules:
            if not get_rule(imported_code, lib_name+'__'+rule_to_import):
                raise NameError("File {} : 'with {} from {}' : Cannot import {} from file {}.kb".format(
                            self.filename, ", ".join(rules), lib_name, rule_to_import, lib_name
                        ))
            else:
                self.new_namespaces[rule_to_import] = lib_name

        self.imports_cache[lib_name] = imported_code
        self.imported_code.add(imported_code)

    def _import_inspection(self, code, inspection_name):
        for node in code.ast:
            if type(node) in [UnilineInspection, MultilineInspection] and node.name == inspection_name:
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
            raise KombuError("'with {0}': The kombu file '{0}.kb' cannot be found".format(filename))

        result = ""
        for line in f.read():
            result += line

        return result, path

