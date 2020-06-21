from time import sleep, time
from re import search
from contextlib import contextmanager
from debug import cumulated_time, get_time_cm
from exceptions import *
import io
import sys


@contextmanager
def catch_output(self):
    sys.stdout = io.StringIO()
    yield
    self._output_message = sys.stdout.getvalue()
    sys.stdout.close()
    sys.stdout = sys.__stdout__


def replaces(text, *replaces):
    i = 0
    while i < len(replaces):
        text = text.replace(str(replaces[i]), str(replaces[i+1]))
        i += 2
    return text


def guards_are_present(guards, string):
    if type(guards) is list:
        for guard_choice in guards:
            if guard_choice[:6] == 'REGEX~':
                m = search("(.|\n)*(?P<match>"+guard_choice[6:]+')', string)
                if m:
                    return m.start('match')
            else:
                m = search("(.\n)*(?P<match>"+"".join(('\\'+l if not l.isalpha() else l for l in guard_choice))+')', string)
                if m:
                    return m.start('match')
    else:
        if guards[:6] == 'REGEX~':
            m = search("(.|\n)*(?P<match>"+guards[6:]+")", string)
            if m:
                return m.start('match')
        else:
            m = search("(.|\n)*(?P<match>"+"".join(('\\' + l if not l.isalpha() else l for l in guards))+")", string)
            if m:
                return m.start('match')


def rule(guards=None):
    def decorator(rule_definition):
        """Decorator for each rule, which permits to call the provided rule only if it can be applied."""
        def wrapper(self, name=None, *args, **kwargs):
            """Manage recursion guards and call the rule decorated."""

            self._ctx.append(rule_definition.__name__)

            if guards:
                can_call = guards_are_present(guards, (self.src+" ")[:self.recursion_guards_positions[-1]])
                if not can_call:
                    self.errors_stack.append(Error('%s expected' % guards))
                else:
                    self.recursion_guards_positions.append(can_call)

                if self._ast and can_call is not None:
                    with self._group(name=name, type=rule_definition.__name__[1:-1]):
                        rule_definition(self, *args, **kwargs)
                else:
                    self._ast = None

                del self.recursion_guards_positions[-1]

            else:
                if self._ast:
                    with self._group(name=name, type=rule_definition.__name__[1:-1]):
                        rule_definition(self, *args, **kwargs)

            del self._ctx[-1]

        return wrapper
    return decorator


def escape_quotes(string):
    return string.replace("'", "\\'")


def common(iterable1, iterable2):
    return [i for i in iterable1 if i in iterable2]


def split(iterable, spliter, include=False, include_at_beginning=False):
    if include and include_at_begining:
        raise Exception("Inculde and inculde at beginning options cannot be activated at the same time.")

    new_iterable = []
    subiterable = []
    for element in iterable:

        if element == spliter:
            if include:
                subiterable.append(element)
            new_iterable.append(subiterable)
            if include_at_beginning:
                subiterable = [element]
            else:
                subiterable = []
        else:
            subiterable.append(element)

    new_iterable.append(subiterable)

    return new_iterable


def get_rule(code, rule_name):
    from KomBuInterpreter.TokenClasses import RuleDefinition
    rules = [r for r in code.ast if type(r) is RuleDefinition]
    for rule in rules:
        if rule.whole_name == rule_name:
            return rule


def warning(ctx_rule, nb):
    def warning_checker(funct):
        def wrapper(self, w):
            if w.ctx[-1][1:-1] == ctx_rule and w.nb == nb:
                return funct(self, w)

        return wrapper
    return warning_checker


def error(etype, ctx_rule, *args):
    def error_checker(funct):
        def wrapper(self, e):
            if etype == 'missing':
                if args[0] == 'string':
                    if isinstance(e, FailedMatch) and e.ctx[-1] == '_'+ctx_rule+'_' and e.expected == args[1]:
                        return funct(self, e)
                elif args[1] == 'regex':
                    if isinstance(e, FailedPattern) and e.ctx[-1][1:-1] == '_'+ctx_rule+'_' and e.expected == args[1]:
                        return funct(self, e)

            elif etype == 'failed':
                if not isinstance(e, GeneratedError) and '_'+ctx_rule+'_' in e.ctx[:-1]:
                    if e.ctx[e.ctx.index('_'+ctx_rule+'_')+1][1:-1].split('__')[-1] == args[0]:
                        return funct(self, e)

            elif etype == 'generated':
                if isinstance(e, GeneratedError) and '_'+ctx_rule+'_' == e.ctx[-1] and e.number == args[0]:
                    return funct(self, e)


        return wrapper
    return error_checker

