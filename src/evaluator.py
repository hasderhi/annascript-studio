# Because we don't want users to do funny things with eval

import ast
import operator
import math
import re

def normalize_expr(expr):
    # "2x" -> "2*x"
    return re.sub(r'(\d)(x)', r'\1*\2', expr)

OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow
}

FUNCS = {
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'sqrt': math.sqrt
}

class HackAttempt(Exception):
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

        elif isinstance(n, ast.Constant):  # numbers
            return n.value

        elif isinstance(n, ast.BinOp):  # + - * / **
            if type(n.op) not in OPS:
                raise HackAttempt()
            return OPS[type(n.op)](_eval(n.left), _eval(n.right))

        elif isinstance(n, ast.UnaryOp):  # -x
            if isinstance(n.op, (ast.USub, ast.UAdd)):
                return -_eval(n.operand) if isinstance(n.op, ast.USub) else _eval(n.operand)
            else:
                raise HackAttempt()

        elif isinstance(n, ast.Name):
            if n.id == "x":
                return x_value
            raise HackAttempt()

        elif isinstance(n, ast.Call):
            if not isinstance(n.func, ast.Name):
                raise HackAttempt()
            func_name = n.func.id
            if func_name not in FUNCS:
                raise HackAttempt()
            args = [_eval(arg) for arg in n.args]
            return FUNCS[func_name](*args)

        else:
            # Any other node type is suspicious
            raise HackAttempt()

    try:
        return _eval(node)
    except HackAttempt:
        raise ValueError()