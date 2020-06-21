# -*- coding=utf-8 -*-


# Kombu syntax error

class KombuError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return str(self.msg)


# Superclass of all parsing exceptions

class ParsingError(Exception):
    def __init__(self, msg, pos, ctx):
        self.msg = msg
        self.pos = pos
        self.ctx = tuple(ctx)
        Exception.__init__(self)

    def __str__(self):
        format = self.pos + (self.ctx[-1].split('__')[-1][:-1],)
        return 'At (%i:%i) in %s : ' % format + self.msg

    def __eq__(self, other):
        return type(other) is ParsingError

    def is_furthest(self, other, strictly=True):
        if strictly:
            return self.pos[0] > other.pos[0] or (self.pos[0] == other.pos[0] and self.pos[1] > other.pos[1])
        else:
            return self.pos[0] > other.pos[0] or (self.pos[0] == other.pos[0] and self.pos[1] >= other.pos[1])


# Syntax errors

class ParsingSyntaxError(ParsingError):
    pass


class FailedMatch(ParsingSyntaxError):
    def __init__(self, expected, got, pos, ctx):
        self.expected = expected
        self.got = got
        self.pos = pos
        self.ctx = ctx
        ParsingSyntaxError.__init__(self, "Expected '%s', got '%s'" % (expected, got), pos, ctx)


class FailedPattern(ParsingSyntaxError):
    def __init__(self, expected, got, pos, ctx):
        self.expected = expected
        self.got = got
        ParsingSyntaxError.__init__(self, "Expected something that would match '%s', got '%s'" % (expected, got), pos, ctx)

    def __str__(self):
        return ParsingSyntaxError.__str__(self)


# Generated errors

class GeneratedError(ParsingError):
    def __init__(self, number, trigger, pos, ctx):
        self.number = number
        self.e_trigger = trigger
        ParsingError.__init__(self, "Generated error number %i ; Warning, it should be caught" % number, pos, ctx)


class RaisedError(ParsingError):
    pass


# Only a warning ; doesn't interrupt the parsing

class Warning:
    def __init__(self, nb, pos, ctx):
        self.nb = nb
        self.pos = pos
        self.ctx = ctx

    def __str__(self):
        format = (self.nb,) + self.pos + (self.ctx[-1].split('__')[-1][:-1],)
        return 'Warning number %i at (%i:%i) in %s ; Beware, it should be caught. ' % format


