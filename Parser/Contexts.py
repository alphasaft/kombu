from utils import time_alert
from Parser.Errors import Error
from Parser.AST import AST
from contextlib import contextmanager
from re import match
from time import time


class Contexts:
    def __init__(self):
        self._choices_groups_possibles_asts = []
        self._pos_in_ast = []
        self.src = ""
        self._recursion_guards = []
        self.errors_stack = []
        self._init_configs()

    def _init_configs(self):
        self._ast = {'ast': AST(entire_match=self.src, fields={}), 'cur': 0,
                                 'groups_matches_anchors': []}

    def _new_config(self, config):
        """Creates a new config. Needs the configuration's AST and the number of the current examined character in the
         source."""
        self._ast.append(config)
        cleared_configs = []
        for config in self._ast:
            if config not in cleared_configs:
                cleared_configs.append({
                    'ast': config['ast'],
                    'cur': config['cur'],
                    'groups_matches_anchors': config['groups_matches_anchors'].copy()})
        self._ast = cleared_configs.copy()

    def _del_config(self, config_number):
        """To delete an impossible configuration. Remember that the provided configuration was deleted. You need to use
         the _update_configs_stack() method to confirm that you really want to remove all the pre-deleted configs."""
        self._ast[config_number] = None

    def _update_configs_stack(self):
        """Remove definitively all the pre-deleted configurations."""
        self._ast = [e for e in self._ast if e]

    def _mod_config(self, config_number, new_ast, move):
        """Change the ast of the provided configuration into the new_ast and add the move parameter to the cur of the
         configuration."""
        self._ast[config_number] = {'ast': new_ast, 'cur': self._ast[config_number]['cur'] + move,
                                               'groups_matches_anchors': [i for i in self._ast[config_number]
                                               ['groups_matches_anchors']]}

    def _add_group_anchors(self):
        self._ast['groups_matches_anchors'].append(self._ast['cur'])

    def _del_group_anchors(self):
        del self._ast['groups_matches_anchors'][-1]

    def _get_ast(self, config_number):
        """Returns the ast of the provided configuration."""
        return self._ast[config_number]['ast']

    def _match(self, string, name=None, failure_msg=None):
        """For each configuration, look if the provided string corresponds with the begin of the source.
         If it isn't the case, it delete the configuration."""
        
        if self._ast:

            cur = self._ast['cur']

            if self.src[cur:cur+len(string)] == string:
                if name and self._pos_in_ast is not None:
                    self._record_in_ast(name, value)
                self._ast['cur'] += len(string)
            else:
                self._ast = None

        with self._optional():
            self._regex_match("[ \t]+")

    def _regex_match(self, pattern, name=None):
        """Similar as _match, but with a regular expression."""

        if self._ast:
            cur = self._ast['cur']
            m = match('^'+pattern, self.src[cur:])
            if m:
                if name and self._pos_in_ast is not None:
                    self._record_in_ast(name, m.group())
                self._ast['cur'] += m.end()
            else:
                self._ast = None

        if not self._properties['keep_whitespaces'] and pattern != '[ \t]+':
            with self._optional():
                self._regex_match('[ \t]+')
    
    def _record_in_ast(self, name, value):
        listed = name.startswith('+')
        if listed:
            name = name[1:]

        if self._pos_in_ast is not None:
            if not self._ast['ast'].get_node(self._pos_in_ast + [name]):
                if listed:
                    self._ast['ast'].add_node(self._pos_in_ast, name, [AST(type=None, fields={}, entire_match=value)])
                else:
                    self._ast['ast'].add_node(self._pos_in_ast, name, AST(type=None, fields={}, entire_match=value))

            else:
                if listed:
                    self._ast['ast'].add_node(self._pos_in_ast, name, self._ast['ast'].get_node(self._pos_in_ast + [name]) + [AST(type=None, fields={}, entire_match=value)])
                else:
                    self._ast['ast'].add_node(self._pos_in_ast, name, AST(type=None, fields={}, entire_match=value))

    @contextmanager
    def _group(self, name=None, type=None):
        if name == 'self':
            yield

        elif name:

                listed = name.startswith('+')
                if listed:
                    name = name[1:]

                if self._ast:
                    self._create_ast_node(name, listed, type)
                    self._add_group_anchors()

                if self._pos_in_ast is not None:
                    self._pos_in_ast.append(name)
                    if listed and not self._pos_in_ast[-1] == -1:
                        self._pos_in_ast.append(-1)

                yield

                if self._ast:

                    self._complete_ast_node(listed)
                    self._del_group_anchors()

                if self._pos_in_ast is not None:
                    if self._pos_in_ast[-1] == -1:
                        del self._pos_in_ast[-1]
                    del self._pos_in_ast[-1]

        else:
            old_pos_in_ast = self._pos_in_ast
            self._pos_in_ast = None

            yield

            self._pos_in_ast = old_pos_in_ast
    
    def _create_ast_node(self, name, listed, type):
        if self._ast:
            if self._pos_in_ast is not None and not self._ast['ast'].get_node(self._pos_in_ast + [name]):
                if listed:
                    self._ast['ast'].add_node(self._pos_in_ast, name, [AST(entire_match="", type=type, fields={})])
                else:
                    self._ast['ast'].add_node(self._pos_in_ast, name, AST(entire_match="", type=type, fields={}))
            elif self._pos_in_ast is not None and self._ast['ast'].get_node(self._pos_in_ast + [name]):
                if listed:
                    self._ast['ast'].get_node(self._pos_in_ast + [name]).append(AST(entire_match="", type=type, fields={}))
                else:
                    self._ast['ast'].add_node(self._pos_in_ast, name, AST(entire_match="", type=type, fields={}))
    
    def _complete_ast_node(self, listed):
        if self._ast:
            ast = self._ast['ast']
            if self._pos_in_ast is not None:
                ast.set_entire_match(self._pos_in_ast, self.src[self._ast['groups_matches_anchors'][-1]:self._ast["cur"]].strip())

    @contextmanager
    def _optional(self, name='self'):
        """All the code in this context manager is optional, it means that if something fail to match inside, it won't
        create an "Unvalid Syntax" error."""

        with self._group(name=name):
            if self._ast:
                old_ast = {'ast': self._ast['ast'].copy(self._pos_in_ast), 'cur': self._ast['cur'], 'groups_matches_anchors': self._ast['groups_matches_anchors'].copy()}

                # Executing 'with' block.
                yield

                if self._ast is None:
                    self._ast = old_ast

            else:
                yield

    @contextmanager
    def _option(self):
        """An option from a choices group. Must imperatively be directly inside an self._choices() with block."""
        if self._ast:
            old_ast = {'ast': self._ast['ast'].copy(from_node=self._pos_in_ast), 'cur': self._ast['cur'], 'groups_matches_anchors': self._ast['groups_matches_anchors'].copy()}

            # Executing 'with' block
            yield

            if self._ast:
                self._choices_groups_possibles_asts[-1].append({'ast': self._ast['ast'].copy(from_node=self._pos_in_ast), 'cur': self._ast['cur'],
                                                                    "groups_matches_anchors": self._ast["groups_matches_anchors"]
                                                                   .copy()})
            self._ast = old_ast

        else:
            yield

    @contextmanager
    def _choices(self, name='self'):
        """Composed of several self._option() with blocks, which represents the options."""

        with self._group(name=name):
            self._choices_groups_possibles_asts.append([])

            yield

            if self._choices_groups_possibles_asts[-1]:
                self._ast = self._choices_groups_possibles_asts[-1][0]
            else:
                self._ast = None

            del self._choices_groups_possibles_asts[-1]









