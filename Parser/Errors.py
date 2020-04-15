# -*- coding=utf-8 -*-


class Error(Exception):
    def __init__(self, msg=None):
        self.msg = msg if msg else ""

    def __str__(self):
        return self.msg

    def __eq__(self, other):
        return type(other) is Error


