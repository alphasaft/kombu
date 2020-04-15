from time import sleep, time
from re import search
import io
import sys
from contextlib import contextmanager


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


def time_alert(max_time=0.005):
    def decorator(funct):
        def timed_funct(*args, **kwargs):
            bef = time()
            result = funct(*args, **kwargs)
            end = time()
            if end - bef > max_time:
                print("Warning : funct", funct.__name__, "takes more than", max_time, "secs to be executed (", end - bef,
                      "s).")
            return result

        return timed_funct

    return decorator


def get_time(funct):

    def timed_funct(*args, **kwargs):
        bef = time()
        result = funct(*args, **kwargs)
        aft = time()
        print("The function", funct.__name__, "takes", aft-bef, 'seconds to be executed.')
        return result

    return timed_funct


@contextmanager
def get_time_cm(name):
    bef = time()
    yield
    aft = time()
    print("The section", name, "takes", aft - bef, 'seconds to be executed.')


def tracecall(active, waittime):
    def tracer(funct):
        def wrapper(*args, **kwargs):
            if active:
                print(funct.__name__)
                sleep(waittime)
            return funct(*args, **kwargs)
        return wrapper
    return tracer


def trace(funct):
    def tracer(object, *args, **kwargs):
        result = funct(object, *args, **kwargs)
        object.trace.append(result)
        return result
    return trace


def isinorder(iterable, string):
    regex = ""
    for element in iterable:
        regex += "("
        for choice in element[:-1]:
            if choice[:6] == 'REGEX~':
                choice = choice[6:]
                regex += choice + '|'
            else:
                regex += "".join([('\\'+l if l in '[()]-^$*?+' else l) for l in choice]) + '|'
        regex += "".join([("\\"+l if l in '[({}!<>)]^$*-?+' else l) for l in element[-1]]) + ')'
        regex += '(.|\n)*'

    if search(regex, string):
        return True
    else:
        return False


def rule(guards=None):
    def decorator(rule_definition):
        """Decorator for each rule, which permits to call the provided rule only if she can be applied."""
        def wrapper(self, name=None, *args, **kwargs):
            """Manage recursion guards and call the rule decorated."""
            if guards:
                self._recursion_guards.append(guards)
                if self._ast and isinorder(reversed(self._recursion_guards), self.src):
                    with self._group(name=name, type=rule_definition.__name__[1:-1]):
                        rule_definition(self, *args, **kwargs)
                else:
                    self._ast = None

                del self._recursion_guards[-1]

            else:
                if self._ast:
                    with self._group(name=name, type=rule_definition.__name__[1:-1]):
                        rule_definition(self, *args, **kwargs)

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

