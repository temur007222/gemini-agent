"""Tests for CalculatorTool — validates safe arithmetic, error paths, no eval access."""

import ast

import pytest

from tools import CalculatorTool


@pytest.fixture
def calc() -> CalculatorTool:
    return CalculatorTool()


def test_valid_arithmetic(calc: CalculatorTool) -> None:
    out = calc.execute(expression="17 * 23 + 5")
    assert out["status"] == "success"
    assert out["result"] == 17 * 23 + 5


def test_parentheses_and_power(calc: CalculatorTool) -> None:
    out = calc.execute(expression="2 * (3 + 4) ** 2")
    assert out["status"] == "success"
    assert out["result"] == 98


def test_unary_minus(calc: CalculatorTool) -> None:
    out = calc.execute(expression="-5 + 10")
    assert out["status"] == "success"
    assert out["result"] == 5


def test_division_by_zero(calc: CalculatorTool) -> None:
    out = calc.execute(expression="10 / 0")
    assert out["status"] == "error"
    assert "Invalid expression" in out["error"]


def test_floor_div_and_mod(calc: CalculatorTool) -> None:
    assert calc.execute(expression="17 // 5")["result"] == 3
    assert calc.execute(expression="17 % 5")["result"] == 2


def test_syntax_error(calc: CalculatorTool) -> None:
    out = calc.execute(expression="2 +")
    assert out["status"] == "error"


def test_empty_expression(calc: CalculatorTool) -> None:
    out = calc.execute(expression="")
    assert out["status"] == "error"


def test_no_eval_access_names_blocked(calc: CalculatorTool) -> None:
    """Bare names must not resolve — proves we are not using eval()."""
    out = calc.execute(expression="__import__('os').system('echo HACKED')")
    assert out["status"] == "error"


def test_no_eval_access_function_call_blocked(calc: CalculatorTool) -> None:
    out = calc.execute(expression="abs(-5)")
    assert out["status"] == "error"


def test_no_eval_access_attribute_blocked(calc: CalculatorTool) -> None:
    out = calc.execute(expression="(1).__class__")
    assert out["status"] == "error"


def test_safe_execute_with_wrong_args(calc: CalculatorTool) -> None:
    """safe_execute (called by registry) wraps TypeError on missing args."""
    out = calc.safe_execute()  # missing required 'expression'
    assert out["status"] == "error"
    assert "Invalid arguments" in out["error"]


def test_declaration_shape(calc: CalculatorTool) -> None:
    decl = calc.get_declaration()
    assert decl["name"] == "calculator"
    assert "expression" in decl["parameters"]["properties"]
    assert "expression" in decl["parameters"]["required"]


def test_internal_safe_eval_only_handles_whitelist() -> None:
    """Confirm whitelist: any AST node outside allowed set raises."""
    from tools.calculator_tool import _safe_eval

    tree = ast.parse("[1, 2, 3]", mode="eval")
    with pytest.raises(ValueError):
        _safe_eval(tree)
