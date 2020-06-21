from exceptions import *
from Parsing.AST import AST
from contextlib import contextmanager
from re import match


class Contexts:
    def __init__(self):
        self._choices_groups_possibles_asts = []
        self._options_errors = []

        self._pos_in_ast = []
        self.src = ""
        self.recursion_guards_positions = [-1]
        self._furthest_error = None
        self._runtime_warnings = []

        self._ast = None
        self._cur = 0
        self._group_matches_anchors = None
        self._ctx = []

        self._init_parsing()

    def _init_parsing(self):
        self._ast = AST(entire_match=self.src, fields={})
        self._cur = 0
        self._group_matches_anchors = []

    def _add_group_anchors(self):
        self._group_matches_anchors.append(self._cur)

    def _del_group_anchors(self):
        del self._group_matches_anchors[-1]

    def _get_pos(self):
        to = self.src[:self._cur+1]
        line = to.count('\n')
        column = len(to.split('\n')[-1])
        return line, column

    def _get_token(self):
        i = self._cur
        token = ""

        if self.src[i:i+1] and self.src[i].isalnum():
            while self.src[i:i+1] and self.src[i].isalnum():
                token += self.src[i]
                i += 1
        elif self.src[i:i+1]:
            token = self.src[i]
        else:
            token = "<EOF>"

        return token

    def set_furthest_error(self, etype, *items, pos=None, ctx=None):
        if pos is None:
            pos = self._get_pos()

        if ctx is None:
            ctx = self._ctx.copy()

        raised_error = etype(*items, pos=pos, ctx=ctx)
        if not self._furthest_error or raised_error.is_furthest(self._furthest_error, strictly=False):
            self._furthest_error = raised_error

    def _make_capsule(self, copy=True):
        return {'ast': self._ast.copy() if copy else self._ast,
                'cur': self._cur,
                'group_matches_anchors': self._group_matches_anchors.copy(),
                'pos': self._pos_in_ast}

    def _merge(self, root, branch, pos):
        if pos:
            root.add_node(pos[:-1], pos[-1], branch)
        elif pos == []:
            root = branch

        self._ast = root
        self._pos_in_ast = pos

    def _restore(self, old):
        self._ast = old['ast']
        self._cur = old['cur']
        self._group_matches_anchors = old['group_matches_anchors']
        self._pos_in_ast = old['pos']

    def _match(self, string, name=None):
        if self._ast:
            cur = self._cur

            if self.src[cur:cur+len(string)] == string:
                if name and self._pos_in_ast is not None:
                    self._record_in_ast(name, string)
                self._cur += len(string)
            else:
                self._ast = None
                self.set_furthest_error(FailedMatch, string, self._get_token())

            with self._optional():
                self._regex_match("[ \t]+")

    def _regex_match(self, pattern, name=None):
        """Similar as _match, but with a regular expression."""

        if self._ast:
            cur = self._cur
            m = match('^'+pattern, self.src[cur:])
            if m:
                if name and self._pos_in_ast is not None:
                    self._record_in_ast(name, m.group())
                self._cur += m.end()
            else:
                self._ast = None
                self.set_furthest_error(FailedPattern, pattern, self._get_token())

        if not self._properties['keep_whitespaces'] and pattern != '[ \t]+':
            with self._optional():
                self._regex_match('[ \t]+')

    def _record_in_ast(self, name, value):
        listed = name.startswith('+')
        if listed:
            name = name[1:]

        if self._pos_in_ast is not None:
            if not self._ast.get_node(self._pos_in_ast + [name]):
                if listed:
                    self._ast.add_node(self._pos_in_ast, name, [AST(type=None, fields={}, entire_match=value)])
                else:
                    self._ast.add_node(self._pos_in_ast, name, AST(type=None, fields={}, entire_match=value))

            else:
                if listed:
                    self._ast.add_node(self._pos_in_ast, name, self._ast.get_node(self._pos_in_ast + [name]) + [AST(type=None, fields={}, entire_match=value)])
                else:
                    self._ast.add_node(self._pos_in_ast, name, AST(type=None, fields={}, entire_match=value))

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
            if self._pos_in_ast is not None and not self._ast.get_node(self._pos_in_ast + [name]):
                if listed:
                    self._ast.add_node(self._pos_in_ast, name, [AST(entire_match="", type=type, fields={})])
                else:
                    self._ast.add_node(self._pos_in_ast, name, AST(entire_match="", type=type, fields={}))
            elif self._pos_in_ast is not None and self._ast.get_node(self._pos_in_ast + [name]):
                if listed:
                    self._ast.get_node(self._pos_in_ast + [name]).append(AST(entire_match="", type=type, fields={}))
                else:
                    self._ast.add_node(self._pos_in_ast, name, AST(entire_match="", type=type, fields={}))

    def _complete_ast_node(self, listed):
        if self._ast:
            ast = self._ast
            if self._pos_in_ast is not None:
                ast.set_entire_match(self._pos_in_ast, self.src[self._group_matches_anchors[-1]:self._cur].strip())

    @contextmanager
    def _optional(self, name='self'):
        """All the nested code is optional, it means that if something fail to match inside, it won't
        create an "Unvalid Syntax" error."""

        with self._group(name=name):
            if self._ast:

                # The ast become the node we work on. We also cut the position too.
                # Memoization
                capsule = self._make_capsule(copy=False)
                # Cutting
                if self._pos_in_ast == []:
                    self._ast = self._ast.copy() # NOOOOOOON

                elif self._pos_in_ast is not None:
                    self._ast = self._ast.get_node(self._pos_in_ast)
                    self._pos_in_ast = []



                yield

                if self._ast:
                    self._merge(root=capsule['ast'], branch=self._ast, pos=capsule['pos'])
                else:
                    self._restore(capsule)

            else:
                yield

    @contextmanager
    def _option(self):
        """An option from a choices group. Must imperatively be directly inside an with self._choices(): block."""
        if self._ast:

            # The ast become the node we work on. We also cut the position too.
            # Memoization
            capsule = self._make_capsule(copy=False)
            # Cutting
            if self._pos_in_ast == []:
                self._ast = self._ast.copy()

            elif self._pos_in_ast is not None:
                self._ast = self._ast.get_node(self._pos_in_ast)
                self._pos_in_ast = []

            yield

            if self._ast:
                self._merge(root=capsule['ast'], branch=self._ast, pos=capsule['pos'])
                self._choices_groups_possibles_asts[-1].append(self._make_capsule(copy=False))
                self._ast = None
            else:
                self._restore(capsule)
                self._options_errors[-1].append(self._furthest_error)

        else:
            yield

    @contextmanager
    def _choices(self, name='self'):
        """Composed of several self._option() with blocks, which represents the options."""

        with self._group(name=name):
            self._choices_groups_possibles_asts.append([])
            self._options_errors.append([])

            yield

            if self._choices_groups_possibles_asts[-1]:
                selected = self._choices_groups_possibles_asts[-1][0]
                self._restore(selected)
            else:
                self._ast = None


                if self._options_errors[-1]:
                    furthest_error = self._options_errors[-1][0]
                    for error in self._options_errors[-1][1:]:
                        if error.is_furthest(furthest_error):
                            furthest_error = error

                    self._furthest_error = furthest_error

            del self._options_errors[-1]
            del self._choices_groups_possibles_asts[-1]

    @contextmanager
    def _error_trigger(self, nb, group_name='self', warn=False):
        was = self._ast is not None
        old_cur = self._cur
        pos = self._get_pos()

        if warn:
            with self._optional(group_name):
                yield
                if was and not self._ast:
                    self._runtime_warnings.append(Warning(nb, pos, self._ctx.copy()))

        else:
            yield
            if self._ast:
                self.set_furthest_error(GeneratedError, nb, self.src[old_cur:self._cur-1])
                self._ast = None
