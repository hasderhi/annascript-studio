# Because we don't want users to do funny things with eval

import ast
import operator
import math
import re

def normalize_expr(expr):
    identifiers = "|".join([
        "x", "pi",
        "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
        "sinh", "cosh", "tanh",
        "sqrt", "log", "log2", "log10", "exp", "abs",
        "floor", "ceil", "sign", "hypot", "degrees", "radians", "pow",
    ])
    return re.sub(rf'(\d)({identifiers})\b', r'\1*\2', expr)


OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

CONSTANTS = {
    'pi': math.pi,
    'e': math.e,
    'tau': math.tau,
}


def _log(x, base=None):
    if base is None:
        return math.log(x)
    return math.log(x, base)


def _pow(a, b):
    # Yes, ** already exists as an operator. This is here because my testers are
    # people who insist on calling pow(x, 2) like it's 2004 and they're writing Java.
    return a ** b


def _sign(x):
    return (x > 0) - (x < 0)


FUNCS = {
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'asin': math.asin,
    'acos': math.acos,
    'atan': math.atan,
    'atan2': math.atan2,
    'sinh': math.sinh,
    'cosh': math.cosh,
    'tanh': math.tanh,
    'sqrt': math.sqrt,
    'log': _log,
    'log2': math.log2,
    'log10': math.log10,
    'exp': math.exp,
    'abs': abs,
    'floor': math.floor,
    'ceil': math.ceil,
    'sign': _sign,
    'hypot': math.hypot,
    'degrees': math.degrees,
    'radians': math.radians,
    'pow': _pow,
}


class ExpressionError(Exception):
    # nope, stop trying
    pass


def safe_eval(expr, x_value):
    try:
        node = ast.parse(expr, mode='eval')
    except SyntaxError:
        # Probably just a typo
        raise SyntaxError()

    def _eval(n):
        if isinstance(n, ast.Expression):
            return _eval(n.body)

        elif isinstance(n, ast.Constant): # numbers
            if not isinstance(n.value, (int, float)):
                # string/bytes/None
                raise ExpressionError()
            return n.value

        elif isinstance(n, ast.BinOp): # + - * / ** % //
            if type(n.op) not in OPS:
                raise ExpressionError()
            return OPS[type(n.op)](_eval(n.left), _eval(n.right))

        elif isinstance(n, ast.UnaryOp): # -x, +x
            if isinstance(n.op, (ast.USub, ast.UAdd)):
                return -_eval(n.operand) if isinstance(n.op, ast.USub) else _eval(n.operand)
            else:
                raise ExpressionError()

        elif isinstance(n, ast.Name):
            if n.id == "x":
                return x_value
            if n.id in CONSTANTS:
                return CONSTANTS[n.id]
            raise ExpressionError()

        elif isinstance(n, ast.Call):
            if not isinstance(n.func, ast.Name) or n.keywords:
                raise ExpressionError()
            func_name = n.func.id
            if func_name not in FUNCS:
                raise ExpressionError()
            args = [_eval(arg) for arg in n.args]
            return FUNCS[func_name](*args)

        else:
            raise ExpressionError()
        
    return _eval(node)