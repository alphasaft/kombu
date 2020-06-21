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
        self.filename = ""
        self.errors = []

        self.last_pos = 0
        self.last_fpos = (1, 1)
        self.pos = 0

    def _cur(self):
        """ Return the first character of the source, or an empty string if the source is empty."""
        try:
            return self.src[self.pos]
        except IndexError:
            return ""

    def fpos(self):  # Formatted pos : (line, column)
        i = self.last_pos
        line, column = self.last_fpos
        while len(self.src) > i and i < self.pos:
            if self.src[i] == '\n':
                line += 1
                column = 1
            else:
                column += 1
            i += 1

        self.last_pos = self.pos
        self.last_fpos = (line, column)

        return line, column

    def tokenize(self, src, filename):
        """Tokenize the input into a list of token objects. Every token has a name, a value, and a position."""
        self.__init__()
        self.src = src
        self.filename = filename
        while len(self.src) > self.pos:
            self._maketoken()

        self.tokenlist += [Token('newline', '\n', self.fpos()), Token('EOF', 'EOF', self.fpos()), Token('newline', '\n', self.fpos())]

        return self.tokenlist

    def _maketoken(self):
        """Returns a token if the begin of the source corresponds. If its doesn't correspond to any token regex,
        it remembers that there is a part of the source which isn't correct."""
        analysed = False
        for regex, name in self.tokendict.items():

            m = re.match(regex, self.src[self.pos:])
            if m:
                analysed = True
                t = Token(name, m.group(0), self.fpos())
                try:
                    new_t = getattr(self, 't_'+name)(t)
                    if new_t:
                        t = new_t
                except AttributeError:
                    pass

                if name != '!' and t != 'delete':
                    self.tokenlist.append(t)
                self.pos += m.end()
                break

        if not analysed:
            raise SyntaxError(
                    "File {} at {} : '{}' : Token wasn't recognized."
                    .format(self.filename, self.fpos, self._default_currenttoken())
            )

    def _default_currenttoken(self):
        """Returns the current token if this is not described, as a sort of .split(). Useful for debuging."""
        token = ""
        src = self.src[self.pos:]

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
            self.tokenlist.append(Token('newline', 'end of line', self.fpos()))
            self.pos += 1
