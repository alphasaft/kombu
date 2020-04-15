from contextlib import contextmanager
from re import match
from Parser.AST import AST
from time import time
from utils import time_alert


# Ce project m'aura appris de toujours faire list.copy(), voire deepcopy(list). Toujours.


class Contexts:
    def __init__(self):
        self._choices_groups_possibles_asts = []
        self._pos_in_ast = []
        self.src = ""
        self._recursion_guards = []
        self._init_configs()

    def _init_configs(self):
        self._configurations = [{'ast': AST(entire_match=self.src, fields={}), 'cur': 0,
                                 'groups_matches_anchors': [], 'root_number': None}]

    def _new_config(self, config):
        """Creates a new config. Needs the configuration's AST and the number of the current examined character in the
         source."""
        self._configurations.append(config)
        cleared_configs = []
        for config in self._configurations:
            if config not in cleared_configs:
                cleared_configs.append({
                    'ast': config['ast'],
                    'cur': config['cur'],
                    'groups_matches_anchors': config['groups_matches_anchors']})
        self._configurations = cleared_configs.copy()

    def _del_config(self, config_number):
        """To delete an impossible configuration. Remember that the provided configuration was deleted. You need to use
         the _update_configs_stack() method to confirm that you really want to remove all the pre-deleted configs."""
        self._configurations[config_number] = None

    def _update_configs_stack(self):
        """Remove definitively all the pre-deleted configurations."""
        self._configurations = [e for e in self._configurations if e]

    def _mod_config(self, config_number, new_ast, move):
        """Change the ast of the provided configuration into the new_ast and add the move parameter to the cur of the
         configuration."""
        self._configurations[config_number] = {'ast': new_ast,
                                               'cur': self._configurations[config_number]['cur'] + move,
                                               'groups_matches_anchors': self._configurations[config_number][
                                                   'groups_matches_anchors'].copy(),
                                               'root_number': self._configurations[config_number].get('root_number')}

    def _add_group_anchors(self):
        for i in range(len(self._configurations)):
            self._configurations[i]['groups_matches_anchors'].append(self._configurations[i]['cur'])

    def _del_group_anchors(self):
        for i in range(len(self._configurations)):
            self._configurations[i]['groups_matches_anchors'] = self._configurations[i]['groups_matches_anchors'][:-1]

    def _get_ast(self, config_number):
        """Returns the ast of the provided configuration."""
        return self._configurations[config_number]['ast']

    def _match(self, string, name=None):
        """For each configuration, look if the provided string corresponds with the begin of the source.
         If it isn't the case, it delete the configuration."""
        for i, configuration in enumerate(self._configurations):
            ast = configuration['ast']
            cur = configuration['cur']
            if self.src[cur:cur + len(string)] == string:
                if name and self._pos_in_ast is not None:
                    self._record_in_ast(name, string)
                self._mod_config(i, ast, len(string))
            else:
                self._del_config(i)
        self._update_configs_stack()

        with self._optional():
            self._regex_match("\s+")

    def _regex_match(self, pattern, name=None):
        """Similar as _match, but with a regular expression."""
        for i, configuration in enumerate(self._configurations):
            ast = configuration['ast']
            cur = configuration['cur']
            m = match('^' + pattern, self.src[cur:])
            if m:
                if name and self._pos_in_ast is not None:
                    self._record_in_ast(name, m.group())
                self._mod_config(i, ast, m.end())
            else:
                self._del_config(i)
        self._update_configs_stack()

        if not self._properties['keep_whitespaces'] and not pattern == '\s+':
            with self._optional():
                self._regex_match('\s+')

    def _record_in_ast(self, name, value):
        listed = name.startswith('+')
        if listed:
            name = name[1:]

        for i, config in enumerate(self._configurations):
            if self._pos_in_ast is not None:
                if not config['ast'].get_node(self._pos_in_ast + [name]):
                    if listed:
                        config['ast'].add_node(self._pos_in_ast, name, [value])
                    else:
                        config['ast'].add_node(self._pos_in_ast, name, value)

                else:
                    if listed:
                        config['ast'].add_node(self._pos_in_ast, name,
                                               config['ast'].get_node(self._pos_in_ast + [name]) + [value])
                    else:
                        config['ast'].add_node(self._pos_in_ast, name,
                                               config['ast'].get_node(self._pos_in_ast + [name]) + value)

    @contextmanager
    def _group(self, name=None, type=None):
        if name == 'self':
            yield

        elif name:

            listed = name.startswith('+')
            if listed:
                name = name[1:]

            for config in self._configurations:
                self._create_ast_node(name, listed, config['ast'], type)

            if self._pos_in_ast is not None:
                self._pos_in_ast.append(name)
                if listed and not self._pos_in_ast[-1] == -1:
                    self._pos_in_ast.append(-1)
                self._add_group_anchors()

            yield

            for config in self._configurations:
                self._complete_ast_node(listed, config)

            if self._pos_in_ast is not None:
                if self._pos_in_ast[-1] == -1:
                    del self._pos_in_ast[-1]
                del self._pos_in_ast[-1]
                self._del_group_anchors()

    def _create_ast_node(self, name, listed, ast, type):
        if self._pos_in_ast is not None and not ast.get_node(self._pos_in_ast + [name]):
            if listed:
                ast.add_node(self._pos_in_ast, name, [AST(entire_match="", type=type, fields={})])
            else:
                ast.add_node(self._pos_in_ast, name, AST(entire_match="", type=type, fields={}))
        else:
            if listed:
                ast.get_node(self._pos_in_ast + [name]).append(AST(entire_match="", type=type, fields={}))
            else:
                ast.add_node(self._pos_in_ast, name, AST(entire_match="", type=type, fields={}))

    def _complete_ast_node(self, listed, config):
        ast = config['ast']
        if self._pos_in_ast is not None:
            ast.set_entire_match(self._pos_in_ast, self.src[config['groups_matches_anchors'][-1]:config["cur"]].strip())

    @contextmanager
    def _optional(self, name='self'):
        """All the code in this context manager is optional, it means that if something fail to match inside, it won't
        create an "Unvalid Syntax" error."""

        with self._group(name=name):

            if name and name != "self":

                # Cut of the position
                root_pos = self._pos_in_ast
                self._pos_in_ast = []

                # Cut of the ast to keep only the active branch
                root_configs = [config.copy() for config in self._configurations]
                for i, config in enumerate(root_configs):
                    self._configurations[i]['ast'] = config['ast'].cut_branch(root_pos)
                    self._configurations[i]['root_number'] = i

                # Executing 'with' block.
                yield

                self._pos_in_ast = root_pos
                remaining_configs = []
                for config in self._configurations:
                    remaining_configs.append(config['root_number'])
                    root_configs[config['root_number']]['ast'].add_node(root_pos[:-1], root_pos[-1], config['ast'])
                    root_configs[config['root_number']]['cur'] = config['cur']

                self._configurations = root_configs

            elif name == 'self':
                if self._pos_in_ast and len(self._pos_in_ast) > 0:

                    # Cut of the position
                    root_pos = self._pos_in_ast
                    self._pos_in_ast = []

                    # Cut of the ast to keep only the active branch
                    root_configs = [config.copy() for config in self._configurations]
                    for i, config in enumerate(root_configs):
                        self._configurations[i]['ast'] = config['ast'].cut_branch(root_pos)
                        self._configurations[i]['root_number'] = i

                    # Executing 'with' block.
                    yield

                    self._pos_in_ast = root_pos
                    remaining_configs = []
                    for config in self._configurations:
                        remaining_configs.append(config['root_number'])
                        root_configs[config['root_number']]['ast'].add_node(root_pos[:-1], root_pos[-1], config['ast'])
                        root_configs[config['root_number']]['cur'] = config['cur']

                    self._configurations = root_configs

                else:
                    old_configurations = [{'ast': config['ast'].copy(), 'cur': config['cur'], 'groups_matches_anchors':
                        config['groups_matches_anchors'].copy()} for config in list(self._configurations)]

                    # Executing 'with' block.
                    yield

                    # If at least one configuration remains, it means it's ok.
                    # All the remaining configurations are the configurations which match.
                    for config in old_configurations:
                        self._new_config(config)

            else:
                old_configurations = [{'ast': config['ast'].copy(), 'cur': config['cur'], 'groups_matches_anchors':
                    config['groups_matches_anchors'].copy()} for config in list(self._configurations)]

                # Executing 'with' block.
                yield

                # If at least one configuration remains, it means it's ok.
                # All the remaining configurations are the configurations which match.
                for config in old_configurations:
                    self._new_config(config)

    @contextmanager
    def _option(self):
        """An option from a choices group. Must imperatively be directly inside an self._choices() with block."""
        old_configurations = [{'ast': config['ast'].copy(), 'cur': config['cur'], 'groups_matches_anchors':
            config['groups_matches_anchors'].copy()} for config in self._configurations]

        if self._pos_in_ast is not None:
            old_pos_in_ast = self._pos_in_ast.copy()
        else:
            old_pos_in_ast = None

        # Executing 'with' block
        yield

        self._pos_in_ast = old_pos_in_ast
        for config in self._configurations:
            self._choices_groups_possibles_asts[-1].append({'ast': config['ast'].copy(), 'cur': config['cur'],
                                                            "groups_matches_anchors": config["groups_matches_anchors"]
                                                           .copy()})

        self._configurations = [{'ast': config['ast'].copy(), 'cur': config['cur'], 'groups_matches_anchors':
            config['groups_matches_anchors']} for config in list(old_configurations)]

    @contextmanager
    def _choices(self, name='self'):
        """Composed of several self._option() with blocks, which represents the options."""

        with self._group(name=name):
            self._choices_groups_possibles_asts.append([])

            yield

            self._configurations = self._choices_groups_possibles_asts[-1]
            del self._choices_groups_possibles_asts[-1]

