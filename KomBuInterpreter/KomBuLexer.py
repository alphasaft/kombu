# -*- coding=utf-8 -*-

from KomBuInterpreter.BaseLexer import BaseLexer, Token


class KomBuGrammarError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return str(self.msg)


class KomBuLexer(BaseLexer):
    def __init__(self):
        BaseLexer.__init__(self)
        self.tokendict = {
              '(?<![a-zA-Z])(with|block|test|group|from|inspect|return|node|before|after|missing)(?![a-zA-Z\?!])': 'keyword',
              '[\t ]+': '!',
              '//\*(.|\n)*?\*//': 'comment',
              '//[^\n]*': 'comment',
              '\+?:\w+': 'groupname',
              '\$\w+': 'constantname',
              '\$[^\w\n]+': 'unexpected_option_name',
              '\$': 'missing_option_name',
              '<\w+>': 'rulecall',
              '::': 'ruleassign',
              ':': 'option_assign',
              '".*?(?!\\\\)"': 'string',
              "'.*?(?!\\\\)'": 'string',
              ',': 'coma',
              '\|': 'OptionsSeparator',
              '\w+': 'ident',
              '\[': 'LOptional',
              '\]': 'ROptional',
              '/.*?/': 'regex',
              '\(': 'LChoiceGroup',
              '\)': 'RChoiceGroup',
              '\{': 'LBlock',
              '\}': 'RBlock',
              '!': 'excl_point',
              '->': 'rarrow',
              '&': 'ampersand',
              '§': 'silcrow',
              '\.': 'point',
              '\n[\t ]*': 'newline',
              '[^\s{}!\?§&£]+': 'PyChars',
              }

    def lexeme(self, t):
        print(t)

    def t_constantname(self, t):
        t.changevalue(t.value[1:])
        return t

    def t_regex(self, t):
        t.changevalue(t.value[1:-1])
        return t

    def t_string(self, t):
        t.changevalue(t.value[1:-1])
        return t

    def t_rulecall(self, t):
        t.changevalue(t.value[1:-1])
        return t

    def t_groupname(self, t):
        if t.value.startswith('+'):
            t.changevalue('+'+t.value[2:])
        else:
            t.changevalue(t.value[1:])
        return t

    def t_newline(self, t):
        t.changevalue(t.value[1:])
        self.lineo += 1
        return t

    def t_comment(self, t):
        lines = len(t.value.split('\n')) - 1
        self.tokenlist += [Token('newline', '', self.lineo) for l in range(lines)]
        self.lineo += lines
        return "delete"

    def t_missing_option_name(self, t):
        raise SyntaxError("Line {} : '$' : Expected an option name.".format(t.pos))

    def t_unexpected_option_name(self, t):
        raise SyntaxError("Line {} : '{}' : Option name should only be composed of alphanumerics characters.".format(
            t.pos, t.value))
