"""CalculatorTool - safe arithmetic evaluator."""

import ast
import operator
from typing import Any, Callable, Dict, Type, Union

from .base_tool import BaseTool


Number = Union[int, float]

# Whitelisted AST nodes & operators (no eval, no name lookups).
_BIN_OPS: Dict[Type[ast.AST], Callable[[Number, Number], Number]] = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.FloorDiv: operator.floordiv,
}
_UNARY_OPS: Dict[Type[ast.AST], Callable[[Number], Number]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _safe_eval(node: ast.AST) -> Number:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        bin_op = _BIN_OPS[type(node.op)]
        return bin_op(_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        unary_op = _UNARY_OPS[type(node.op)]
        return unary_op(_safe_eval(node.operand))
    raise ValueError("Unsupported expression")


class CalculatorTool(BaseTool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluate a mathematical expression with +, -, *, /, %, **, //."

    # The Strategy pattern declares each concrete tool's parameters explicitly.
    # mypy --strict treats this as a Liskov violation (the supertype takes **kwargs);
    # at runtime safe_execute() converts the resulting TypeError into a structured
    # error, which is the contract the registry relies on.
    def execute(self, expression: str) -> Dict[str, Any]:  # type: ignore[override]
        if not isinstance(expression, str) or not expression.strip():
            return {"status": "error", "error": "expression must be a non-empty string"}
        try:
            tree = ast.parse(expression, mode="eval")
            value = _safe_eval(tree)
        except (SyntaxError, ValueError, ZeroDivisionError) as e:
            return {"status": "error", "error": f"Invalid expression: {e}"}
        return {"status": "success", "result": value, "expression": expression}

    def get_declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression, e.g. '2 * (3 + 4) ** 2'",
                    }
                },
                "required": ["expression"],
            },
        }
