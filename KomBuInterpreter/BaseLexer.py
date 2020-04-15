import re

BLANKS = ' \t'
ALONECHARS = """()[]{}<>-\\@#|$"""


class Token(object):
    def __init__(self, name, value, pos):
        self.name, self.value, self.pos = name, value, pos

    def __repr__(self):
        return "{} token with value '{}' at line {}".format(self.name, self.value, self.pos)

    def changevalue(self, value):
        self.value = value


class BaseLexer:

    def __init__(self):
        """Initialize all the globals variables which the Lexer needs."""
        self.src = ""
        self.tokendict = {}
        self.tokenlist = []
        self.errors = []
        self.lineo = 1

    def _cur(self):
        """ Return the first character of the source, or an empty string if the source is empty."""
        try:
            return self.src[0]
        except IndexError:
            return ""

    def tokenize(self, src, filename):
        """Tokenize the input into a list of token objects. Every token has a name, a value, and a line-position."""
        self.src = src
        self.tokenlist = []
        self.lineo = 1
        self.filename = filename
        while len(self.src) > 0:
            if len(self.src) == 0:
                break
            self._maketoken()

        self.tokenlist += [Token('newline', '\n', self.lineo), Token('EOF', 'EOF', self.lineo), Token('newline', '\n', self.lineo)]

        return self.tokenlist

    def _maketoken(self):
        """Returns a token if the begin of the source corresponds. If its doesn't correspond to any token regex,
        it remembers that there is a part of the source which isn't correct."""
        analysed = False
        for regex, name in self.tokendict.items():

            m = re.match("^" + regex, self.src)
            if m:
                analysed = True
                t = Token(name, m.group(0), self.lineo)
                try:
                    new_t = getattr(self, 't_'+name)(t)
                    if new_t:
                        t = new_t
                except AttributeError:
                    pass

                if name != '!' and t != 'delete':
                    self.tokenlist.append(t)
                self.src = self.src[m.end():]
                break

        if not analysed:
            raise SyntaxError(
                        "File {}, line {} : '{}' : Token wasn't recognized.".format(self.filename, self.lineo, self._default_currenttoken()))

    def _default_currenttoken(self):
        """Returns the curent token if this is not descripted, as a sort of .split(). Useful for debuging."""
        token = ""
        src = self.src

        if len(src) > 0 and src[0] in BLANKS:
            token = src[0]

        if len(src) > 0 and src[0].isalnum():
            while src[0].isalnum():
                token += src[0]
                src = src[1:]

        elif len(src) > 0 and src[0] in ALONECHARS:
            token = src[0]

        else:
            token = self._cur()

        return token

    def _skipnewlines(self):
        """Just skip the \n chars and count the line number with them."""

        while self._cur() == '\n':
            self.src = self.src[1:]
            self.tokenlist.append(Token('newline', 'end of line', self.lineo))
            self.lineo += 1