"""Calculadora segura basada en ast."""

from __future__ import annotations

import ast
import math
import operator

from telegram import Update
from telegram.ext import ContextTypes

from handlers.auth import require_auth

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_FUNCS: dict[str, object] = {
    "sqrt": math.sqrt,
    "abs": abs,
    "ceil": math.ceil,
    "floor": math.floor,
    "round": round,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
}

_CONSTS: dict[str, float] = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}


def _eval(node: ast.expr) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError("Tipo no soportado")
    if isinstance(node, ast.Name):
        if node.id in _CONSTS:
            return _CONSTS[node.id]
        raise ValueError(f"Nombre desconocido: {node.id}")
    if isinstance(node, ast.BinOp):
        op_fn = _OPS.get(type(node.op))
        if op_fn is None:
            raise ValueError("Operador no soportado")
        return op_fn(_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op_fn = _OPS.get(type(node.op))
        if op_fn is None:
            raise ValueError("Operador unario no soportado")
        return op_fn(_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = _FUNCS.get(node.func.id)
        if callable(fn):
            return fn(*[_eval(a) for a in node.args])
        raise ValueError(f"Función no permitida: {node.func.id}")
    raise ValueError(f"Expresión no soportada: {type(node).__name__}")


def evaluate(expr: str) -> str:
    try:
        tree = ast.parse(expr.strip(), mode="eval")
        result = _eval(tree.body)
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return f"{result:.10g}"
    except ZeroDivisionError:
        return "❌ División por cero"
    except (ValueError, TypeError) as exc:
        return f"❌ {exc}"
    except SyntaxError:
        return "❌ Expresión inválida"


@require_auth
async def calc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "Uso: `/calc <expresión>`\n\n"
            "*Ejemplos:*\n"
            "`/calc 2 + 2`\n"
            "`/calc 15 * 8 / 3`\n"
            "`/calc 2 ** 10`\n"
            "`/calc sqrt(144)`\n"
            "`/calc sin(pi / 2)`\n"
            "`/calc log(e)`",
            parse_mode="Markdown",
        )
        return

    expr = " ".join(args)
    result = evaluate(expr)
    await update.message.reply_text(f"`{expr}` = `{result}`", parse_mode="Markdown")
