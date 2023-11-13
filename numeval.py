# Write an evaluator based on the grammar from ‹t3/lisp.py›. The
# basic semantic rules are as follows: the first item in a compound
# expression is always an identifier, and the compound expression
# itself is interpreted as a function application.  Evaluation is
# eager, i.e.  innermost applications are evaluated first. Literals
# evaluate to themselves, i.e. ‹3.14› becomes a ‹real› with the
# value ‹3.14›. Only numeric literals are relevant in this homework,
# and all numeric literals represent reals (floats). Besides
# literals, implement the following objects:
#
#  • ‹(vector <real>+)› where <real>+ means 1 or more objects of
#    type ‹real›
#  • ‹(matrix <vector>+)› where each vector is one row, starting
#    from the top
#
# And these operations on them:
#
#  • ‹(+ <vector> <vector>)› vector addition, returns a ‹vector›
#  • ‹(dot <vector> <vector>)› dot product, returns a ‹real›
#  • ‹(cross <vector> <vector>)› cross product, returns a ‹vector›
#  • ‹(+ <matrix> <matrix>)› matrix addition, returns a ‹matrix›
#  • ‹(* <matrix> <matrix>)› matrix multiplication, returns a ‹matrix›
#  • ‹(det <matrix>)› determinant, returns a ‹real›
#  • ‹(solve <matrix>)› solve a system of linear equations, returns
#    a ‹vector›
#
# For ‹solve›, the argument is a matrix of coefficients and the result
# is an assignment of variables -- if there are multiple solutions,
# return a non-zero one.
#
#     system  │ matrix │ written as
#  x + y = 0  │  1  1  │ (matrix (vector 1  1)
#     -y = 0  │  0 -1  │         (vector 0 -1))
#
# Expressions with argument type mismatches (both in object
# constructors and in operations), attempts to construct a matrix
# where the individual vectors (rows) are not of the same length,
# addition of differently-shaped matrices, multiplication of
# incompatible matrices, addition or dot product of different-sized
# vectors, and so on, should evaluate to an ‹error› object. Attempt to
# get a cross product of vectors with dimension other than 3 is an
# ‹error›. Any expression with an ‹error› as an argument is also an
# ‹error›.
#
# The evaluator should be available as ‹evaluate()› and take a string
# for an argument. The result should be an object with methods
# ‹is_real()›, ‹is_vector()›, ‹is_matrix()› and ‹is_error()›.
# Iterating vectors gives reals and iterating matrices gives
# vectors. Both should also support indexing.  ‹float(x)› for
# ‹x.is_real()› should do the right thing.
#
# You can use ‹numpy› in this task (in addition to standard
# modules).


from __future__ import annotations
from math import isclose
from random import randint, random
from typing import Iterator, List, Optional, Set, Tuple, Union
import numpy as np


ID_SYMBOL = {'!', '$', '%', '&', '*', '/', ':', '<', '=', '>', '?', '_', '~'}
ID_SPECIAL = {'+', '-', '.', '@', '#'}
SIGN = {'+', '-'}
LEFT_BR = {'(', '['}
RIGHT_BR = {')', ']'}
V_OPS = {'+', 'dot', 'cross'}
M_OPS = {'+', '*', 'det', 'solve'}
OPS = V_OPS.union(M_OPS)


class Lisp:
    def __init__(self, str_values: List[str]) -> None:
        self.values: List[Union[str, float, Lisp]] = convert(str_values)
        self.complete_check()
        self.pos = 1

    def length(self) -> int:
        return len(self.values)

    def is_error(self) -> bool:
        return self.values == []

    def is_real(self) -> bool:
        return not self.is_error() and type(self.values[0]) == float and self.length() == 1

    def __float__(self) -> float:
        if self.is_real():
            return float(self.values[0])

        raise ValueError('Lisp is not float')

    def __iter__(self) -> Iterator[Union[str, float, Lisp]]:
        if self.is_error() or self.is_real():
            raise ValueError('This lisp can not be iterated')

        if self.is_vector() or self.is_matrix():
            return iter(self.values[1:])

        return iter(self.values)

    def __getitem__(self, i: int) -> Union[str, float, Lisp]:
        if self.is_error() or self.is_real():
            raise ValueError('This lisp can not be indexed')

        if self.is_vector() or self.is_matrix():
            return self.values[i + 1]

        return self.values[i]

    def is_vector(self) -> bool:
        return not self.is_error() and self.values[0] == 'vector'

    def is_matrix(self) -> bool:
        return not self.is_error() and self.values[0] == 'matrix'

    def set_error(self) -> None:
        self.values = []

    def check_compound(self) -> None:
        if self.is_error() or self.is_real():
            return

        if type(self.values[0]) != str or not is_identifier(self.values[0]) or self.length() < 2:
            self.set_error()
            return

        for value in self.values[1:]:
            if (type(value) == Lisp and value.is_error()) or (type(value) not in [Lisp, float]):
                self.set_error()
                return

    def check_error(self) -> None:
        if self.values == []:
            return

        for value in self.values[1:]:
            if value == 'error' or (type(value) == Lisp and value.is_error()):
                self.set_error()
                return

    def check_vector(self) -> None:
        if self.is_error() or self.values[0] != 'vector':
            return

        if self.length() == 1:
            self.set_error()
            return

        for number in self.values[1:]:
            if type(number) != float:
                self.set_error()
                return

    def check_matrix(self) -> None:
        if self.is_error() or self.values[0] != 'matrix':
            return

        if self.length() == 1 or type(self.values[1]) != Lisp or not self.values[1].is_vector():
            self.set_error()
            return

        vec_len = self.values[1].length()
        for vector in self.values[2:]:
            if type(vector) != Lisp or not vector.is_vector() or vector.length() != vec_len:
                self.set_error()
                return

    def check_operations(self) -> None:
        if self.is_error() or (op := self.values[0]) not in OPS:
            return

        if not (self.length() == 3 or (op in {'solve', 'det'} and self.length() == 2)) \
                or type(self.values[1]) != Lisp:
            self.set_error()
            return

        a = vec_or_mat(self.values[1])
        if op in {'solve', 'det'}:
            if type(a) != Matrix:
                self.set_error()
                return

            self.values = det_matrix(a) if op == 'det' else solve_matrix(a)
            return

        if type(self.values[2]) != Lisp:
            self.set_error()
            return

        b = vec_or_mat(self.values[2])
        if type(a) == Vector and type(b) == Vector:
            if op == '+':
                self.values = add_vectors(a, b)
            elif op == 'dot':
                self.values = dot_product(a, b)
            elif op == 'cross':
                self.values = cross_product(a, b)
            else:
                self.set_error()
                return
        elif type(a) == Matrix and type(b) == Matrix:
            if op == '+':
                self.values = add_matrices(a, b)
            elif op == '*':
                self.values = mul_matrices(a, b)
            else:
                self.set_error()
                return
        else:
            self.set_error()
            return

        self.check_vector()
        self.check_matrix()

    def complete_check(self) -> None:
        self.check_error()
        self.check_compound()
        self.check_matrix()
        self.check_vector()
        self.check_operations()


class Vector:
    def __init__(self, lisp: Lisp) -> None:
        self.numbers: List[float] = []
        for num in lisp.values[1:]:
            if type(num) == float:
                self.numbers.append(num)

    def length(self) -> int:
        return len(self.numbers)


class Matrix:
    def __init__(self, lisp: Lisp) -> None:
        self.vectors: List[List[float]] = []
        for vec in lisp.values:
            if type(vec) == Lisp:
                self.vectors.append(Vector(vec).numbers)

    def size_r_c(self) -> Tuple[int, int]:
        return (len(self.vectors), len(self.vectors[0]))


def vec_or_mat(arg: Lisp) -> Union[Vector, Matrix]:
    return Vector(arg) if arg.is_vector() else Matrix(arg)


# I had to do it this way because of mypy
def list_to_vec(arr: List[float]) -> List[Union[str, float, Lisp]]:
    res: List[Union[Lisp, str, float]] = ['vector']
    res += [float(x) for x in arr]
    return res if arr != [] else []


def list_to_mat(arr: List[List[float]]) -> List[Union[str, Lisp, float]]:
    res: List[Union[str, Lisp, float]] = ['matrix']
    for row in arr:
        clean_lisp = Lisp([])
        clean_lisp.values = list_to_vec(list(row))
        res.append(clean_lisp)

    return res if arr != [] else []


def add_vectors(v1: Vector, v2: Vector) -> List[Union[str, float, Lisp]]:
    if v1.length() != v2.length():
        return []

    return list_to_vec(list(np.add(v1.numbers, v2.numbers)))


def dot_product(v1: Vector, v2: Vector) -> List[Union[float, str, Lisp]]:
    if v1.length() != v2.length():
        return []

    return [float(np.dot(v1.numbers, v2.numbers))]


def cross_product(v1: Vector, v2: Vector) -> List[Union[str, float, Lisp]]:
    if v1.length() != 3 or v2.length() != 3:
        return []

    return list_to_vec(list(np.cross(v1.numbers, v2.numbers)))


def add_matrices(m1: Matrix, m2: Matrix) -> List[Union[str, Lisp, float]]:
    if m1.size_r_c() != m2.size_r_c():
        return []

    return list_to_mat(list(np.add(m1.vectors, m2.vectors)))


def mul_matrices(m1: Matrix, m2: Matrix) -> List[Union[str, Lisp, float]]:
    r, _ = m1.size_r_c()
    _, c = m2.size_r_c()
    if r != c:
        return []

    return list_to_mat(list(np.matmul(m1.vectors, m2.vectors)))


def det_matrix(m: Matrix) -> List[Union[float, Lisp, str]]:
    r, c = m.size_r_c()
    if r != c:
        return []

    if len(m.vectors) == 1:
        return [float(m.vectors[0][0])]

    return [float(np.linalg.det(m.vectors))]


def max_nonzero_pos(arr: List[float]) -> int:
    pos = 0
    for i in range(len(arr)):
        if arr[i] > arr[pos] and arr[i] != 0:
            pos = i

    return pos


def find_nonzero(m: np.ndarray, col: int, used: List[int]) -> int:
    for i in range(len(m)):
        if m[i][col] != 0 and i not in used:
            return i

    return -1


def solve_no_inf(matrix: Matrix) -> List[float]:
    if matrix.vectors == []:
        return []

    r, c = matrix.size_r_c()
    m: np.ndarray = np.array(matrix.vectors, float)
    for _ in range(r, c):
        np.append(m, np.zeros(c))

    used: List[int] = []
    row_count = len(m)
    for col in range(c):
        if (row := find_nonzero(m, col, used)) == -1:
            continue

        used.append(row)
        m[row] = np.array(np.true_divide(m[row], m[row][col]), float)
        for i in range(row_count):
            if i != row:
                m[i] = m[i] - m[row] * m[i][col]
                m[i] = np.array(
                    [0 if np.isclose(num, 0) else num for num in m[i]])

    fixed_cols: Set[int] = set()
    rows_of_fixed: Set[int] = set()
    for col in range(c):
        r = -1
        for row in range(len(m)):
            if m[row][col] == 0:
                continue
            elif m[row][col] != 1 or (m[row][col] == 1 and r != -1):
                r = -1
                break
            r = row

        if r != -1 and r not in rows_of_fixed:
            fixed_cols.add(col)
            rows_of_fixed.add(r)

    if used == []:
        return list(np.zeros(c, float))

    res: np.ndarray = np.array([-1.0 for _ in range(c)], float)
    for col in fixed_cols:
        row = find_nonzero(m, col, [])
        res[col] = float(np.sum(m[row]) - 1)

    return list(res)


def solve_matrix(m: Matrix) -> List[Union[float, Lisp, str]]:
    r, c = m.size_r_c()

    if c == 1:
        return ['vector', 0]

    if r != c or det_matrix(m) == [0]:
        return list_to_vec(solve_no_inf(m))

    return list_to_vec(list(np.linalg.solve(m.vectors, [0 for _ in range(r)])))


def is_number(expr: str) -> bool:
    tmp_expr = expr[1:] if expr[0] in SIGN else expr

    if tmp_expr == '' or tmp_expr[0] == '.':
        return False

    if tmp_expr != '0' and tmp_expr[0] == '0' and tmp_expr[1] != '.':
        return False

    dot = False
    for char in tmp_expr:
        if char.isnumeric():
            continue
        elif char == '.':
            if dot:
                return False
            dot = True
        else:
            return False

    return True


def is_identifier(expr: str) -> bool:
    if expr == '' or not (expr[0].isalpha() or expr[0] in ID_SYMBOL or expr in SIGN):
        return False

    for i in range(1, len(expr)):
        if not (expr[i].isalnum() or expr[i] in ID_SPECIAL or expr[i] in ID_SYMBOL):
            return False

    return True


def get_right_bracket(left: str) -> str:
    if left == '(':
        return ')'
    elif left == '[':
        return ']'

    raise ValueError(f'Invalid bracket: {left}')


def bracket_white_check(expr: str) -> bool:
    brackets: List[str] = []
    space = True

    for char in expr:
        if (not space and char in LEFT_BR) or (space and (char.isspace() or char in RIGHT_BR)):
            return False

        if char in LEFT_BR:
            brackets.append(char)
            space = True
        elif char.isspace():
            space = True
        elif char in RIGHT_BR:
            if len(brackets) == 0 or char != get_right_bracket(brackets.pop(-1)):
                return False
        else:
            space = False

    return not space


def decompose(expr: str) -> List[str]:
    if expr == '':
        return []

    if not expr[0] in LEFT_BR:
        return [expr]

    expr = expr[1: -1]
    res: List[str] = ['']
    count = 0
    for char in expr:
        if char.isspace() and count == 0:
            res.append('')
            continue
        elif char in LEFT_BR:
            count += 1
        elif char in RIGHT_BR:
            count -= 1
        res[-1] += char

    return res


def convert(values: List[str]) -> List[Union[str, float, Lisp]]:
    if values == []:
        return []

    res: List[Union[str, float, Lisp]] = []
    for value in values:
        if value == '':
            return []

        if is_identifier(value):
            res.append(value)
        elif is_number(value):
            res.append(float(value))
        elif value[0] in LEFT_BR and value[-1] in RIGHT_BR:
            if (tmp := Lisp(decompose(value))).is_error():
                return []
            res.append(tmp)
        else:
            return []

    return res


def evaluate(expr: str) -> Lisp:
    if expr is None or expr == '' or not bracket_white_check(expr):
        return Lisp([''])

    return Lisp(decompose(expr))
