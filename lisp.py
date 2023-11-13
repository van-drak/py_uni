# Write a simple LISP (expression) parser, following this EBNF grammar:
#
#     expression  = atom | compound ;
#     compound    = '(', expression, { whitespace, expression }, ')' |
#                   '[', expression, { whitespace, expression }, ']' ;
#     whitespace  = ( ' ' | ? newline ? ), { ' ' | ? newline ? } ;
#     atom        = literal | identifier ;
#     literal     = number | string | bool ;
#
#     nonzero    = '1' | '2' | '3' | '4' |
#                  '5' | '6' | '7' | '8' | '9' ;
#     digit      = '0' | nonzero ;
#     sign       = '+' | '-' ;
#     digits     = '0' | ( nonzero, { digit } ) ;
#     number     = [ sign ], digits, [ '.', { digit } ] ;
#
#     bool       = '#f' | '#t' ;
#
#     string     = '"', { str_char }, '"' ;
#     str_lit    = ? any character except '"' and '\' ? ;
#     str_esc    = '\"' | '\\' ;
#     str_char   = str_lit | str_esc ;
#
#     identifier = id_init, { id_subseq } | sign ;
#     id_init    = id_alpha | id_symbol ;
#     id_symbol  = '!' | '$' | '%' | '&' | '*' | '/' | ':' | '<' |
#                  '=' | '>' | '?' | '_' | '~' ;
#     id_alpha   = ? alphabetic character ?
#     id_subseq  = id_init | digit | id_special ;
#     id_special = '+' | '-' | '.' | '@' | '#' ;
#
# Alphabetic characters are those for which ‹isalpha()› returns
# ‹True›. It is okay to accept additional whitespace where it makes
# sense. For the semantics of (ISO) EBNF, see e.g. wikipedia.
#
# The parser should be implemented as a toplevel function called
# ‹parse› that takes a single ‹str› argument. If the string does not
# conform to the above grammar, return ‹None›. Assuming ‹expr› is a
# string with a valid expression, the following should hold about
# ‹x = parse(expr)›:
#
#  • an ‹x.is_foo()› method is provided for each of the major
#    non-terminals: ‹compound›, ‹atom›, ‹literal›, ‹bool›, ‹number›,
#    ‹string› and ‹identifier› (e.g. there should be an ‹is_atom()›
#    method), returning a boolean,
#  • if ‹x.is_compound()› is true, ‹len(x)› should be a valid
#    expression and ‹x› should be iterable, yielding sub-expressions
#    as objects which also implement this same interface,
#  • if ‹x.is_bool()› is true, ‹bool(x)› should work,
#  • if ‹x.is_number()› is true, basic arithmetic (‹+›, ‹-›, ‹*›,
#    ‹/›) and relational (‹<›, ‹>›, ‹==›, ‹!=›) operators should
#    work (e.g.  ‹x < 7›, or ‹x * x›) as well as ‹int(x)› and
#    ‹float(x)›,
#  • ‹x == parse(expr)› should be true (i.e. equality should be
#    extensional),
#  • ‹x == parse(str(x))› should also hold.
#
# If a numeric literal ‹x› with a decimal dot is directly converted to
# an ‹int›, this should behave the same as ‹int( float( x ) )›. A few
# examples of valid inputs (one per line):
#
#     (+ 1 2 3)
#     (eq? [quote a b c] (quote a c b))
#     12.7
#     (concat "abc" "efg" "ugly \"string\"")
#     (set! var ((stuff) #t #f))
#     (< #t #t)
#
# Note that ‹str(parse(expr)) == expr› does «not» need to hold.
# Instead, ‹str› should always give a canonical representation,
# e.g. this must hold:
#
#     str( parse( '+7' ) ) == str( parse( '7' ) )


import string
STR_ESC = ['\"', '\\']
ID_SYMBOL = ['!', '$', '%', '&', '*', '/', ':', '<', '=', '>', '?', '_', '~']
ID_SPECIAL = ['+', '-', '.', '@', '#']
H_BOOL = ['#t', '#f']
SIGN = ['+', '-']
LITERALS = ["number", "string", "bool"]
ATOMS = LITERALS + ["identifier"]


class Expr:
    def __init__(self, str_value, value, subtype):
        self.str_value = str_value
        self.value = value
        self.type = subtype

    def is_compound(self):
        return self.type == "compound"

    def is_atom(self):
        return self.type in ATOMS

    def is_literal(self):
        return self.type in LITERALS

    def is_bool(self):
        return self.type == "bool"

    def is_number(self):
        return self.type == "number"

    def is_identifier(self):
        return self.type == "identifier"

    def is_string(self):
        return self.type == "string"

    def __bool__(self):
        if type(self.value) == bool:
            return self.value

        raise RuntimeError("You can not call bool() on non-bool object")

    def __int__(self):
        return int(self.value)

    def __float__(self):
        return float(self.value)

    def __str__(self):
        return self.str_value

    def __add__(self, other):
        return float(self) + float(other)

    def __sub__(self, other):
        return float(self) - float(other)

    def __mul__(self, other):
        return float(self) * float(other)

    def __truediv__(self, other):
        return float(self) / float(other)

    def __radd__(self, other):
        return float(other) + float(self)

    def __rsub__(self, other):
        return float(other) - float(self)

    def __rmul__(self, other):
        return float(other) * float(self)

    def __rtruediv__(self, other):
        return float(other) / float(self)

    def __lt__(self, other):
        return float(self) < float(other)

    def __gt__(self, other):
        return float(self) > float(other)

    def __eq__(self, other):
        if type(other) == Expr:
            if type(other.value) == list:
                if len(self.value) != len(other.value):
                    return False

                for value in self.value:
                    if value not in other.value:
                        return False

                return True

            return self.value == other.value

        if type(other) == str:
            return True if self.str_value == other else self == parse(other)

        return self.value == other

    def __neq__(self, other):
        return not self == other

    def __iter__(self):
        return iter(self.value)


def find_whitespace(input):
    for i in range(len(input)):
        if input[i] in string.whitespace:
            return i

    return len(input)


def dec_compound(input):
    res = Expr(input, [], "compound")
    tmp_str = input[1:-1]
    i = 0
    if len(tmp_str) == 0 or tmp_str[-1] in string.whitespace:
        return None

    while i < (len(tmp_str)):
        if tmp_str[i] in ['(', '[']:
            pos = find_pair(tmp_str[i:])
            if pos == None:
                return None

            value = dec_compound(tmp_str[i:pos + i + 1])
            if value == None or pos + i + 1 < len(tmp_str) and tmp_str[pos + i + 1] not in string.whitespace:
                return None

            res.value.append(value)
            i += pos + 2
            continue
        elif tmp_str[i] == '\"':
            pos = end_of_str(tmp_str[i:])
            if pos == None or (pos + i + 1 < len(tmp_str) and tmp_str[i + pos + 1] not in string.whitespace):
                return None

            pos += 1
        else:
            pos = find_whitespace(tmp_str[i:])

        if tmp_str[i:pos + i] == '':
            i += pos + 1
            continue

        value = dec_atom(tmp_str[i:pos + i])
        if value is None:
            return None

        res.value.append(value)
        i += pos + 1

    return res


def find_pair(tmp_str):
    bracket = tmp_str[0]
    pair = ')' if bracket == '(' else ']'
    count = 0
    count_off, slash = False, False
    for i in range(len(tmp_str)):
        if count_off:
            if tmp_str[i] == '\\':
                slash = not slash
            elif tmp_str[i] == '\"' and slash:
                slash = False
            elif tmp_str[i] == '\"' and not slash:
                count_off = False
            continue

        if tmp_str[i] == '"' and not slash:
            count_off = True
        if tmp_str[i] == bracket:
            count += 1
        elif tmp_str[i] == pair:
            count -= 1
        if count == 0:
            return i

    return None


def end_of_str(input):
    for i in range(1, len(input)):
        if input[i] == '\"' and input[i - 1] != '\\':
            return i

    return None


def dec_literal(input):
    if input == "#t":
        return Expr(input, True, "bool")
    elif input == "#f":
        return Expr(input, False, "bool")
    elif input[0] == '\"' and input[-1] == '\"' and input != '\"':
        value = dec_str(input)
        return Expr(input, input[1:-1], "string") if value is not None else None
    elif input[0] in SIGN or input[0].isdigit():
        tmp = input[:-1] if input[-1] == '.' and len(input) > 1 else input
        value = dec_number(tmp)
        return Expr(tmp, value, "number") if value is not None else None
    return None


def dec_number(input):
    tmp = input[1:] if input[0] in SIGN else input
    if tmp == '' or not tmp[0].isdigit() or tmp.count('.') > 1 or (len(tmp) > 1 and tmp[0] == '0' and tmp[1].isdigit()):
        return None

    for char in tmp:
        if not char.isdigit() and char != '.':
            return None

    return float(input)
    

def dec_str(input):
    tmp_str = input[1:-1]
    slash = False
    for i in range(len(tmp_str)):
        if tmp_str[i] == '\\':
            slash = not slash
        elif tmp_str[i] == '\"' and slash:
            slash = False
        elif tmp_str[i] == '\"' and not slash:
            return None

    return None if slash else input


def dec_atom(input):
    value = dec_literal(input)
    return value if value is not None else dec_identifier(input)


def dec_identifier(input):
    if input in SIGN:
        return Expr(input, input, "identifier")
    elif input[0].isalpha() or input[0] in ID_SYMBOL:
        for i in range(1, len(input)):
            if not (input[i].isalpha() or input[i] in ID_SYMBOL or input[i] in ID_SPECIAL or input[i].isdigit()):
                return None

        return Expr(input, input, "identifier")

    return None


def parse(expr):
    if expr is None or len(expr) == 0:
        return None
    if expr[0] in ['(', '['] and expr[-1] in [')', ']']:
        return dec_compound(expr)
    return dec_atom(expr)
