import ast
import importlib.util
import os
import pathlib
import pint
import pytest
import re
import sys
import warnings
import numpy as np
import pandas as pd
from pype_schema.units import u
from pype_schema import operations
from pype_schema.utils import parse_units
from pype_schema.parse_json import JSONParser

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False

# set default pint registry so that custom units like MGD are understood
pint.set_application_registry(u)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "variable, kwargs, expected",
    [
        (
            np.arange(5),
            {"delta_t": 2, "split": False},
            np.array([0.5, 0.5, 0.5, 0.5, np.nan]),
        ),
        (
            np.arange(5),
            {"delta_t": 1, "split": False},
            np.array([1, 1, 1, 1, np.nan]),
        ),
        (
            np.concatenate([np.arange(3), np.arange(1, -1, -1)]),
            {"delta_t": 5, "split": True},
            (
                np.array([0, 0, 0.2, 0.2, np.nan]),
                np.array([0.2, 0.2, 0, 0, np.nan]),
            ),
        ),
        (
            np.array([1]),
            {"delta_t": 1, "split": False},
            np.array([np.nan]),
        ),
        (
            np.array([1]),
            {"delta_t": 1, "split": True},
            (np.array([np.nan]), np.array([np.nan])),
        ),
    ],
)
def test_get_change(variable, kwargs, expected):
    result = operations.get_change(variable, **kwargs)
    assert np.array_equal(result, expected, equal_nan=True)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, expected",
    [
        ("data/no_bin_op_algebraic.json", "ValueError"),
        ("data/invalid_bin_op_algebraic.json", "ValueError"),
        ("data/invalid_bin_op_list_algebraic.json", "ValueError"),
        ("data/wrong_bin_len_algebraic.json", "ValueError"),
        ("data/invalid_un_op_algebraic.json", "ValueError"),
        ("data/invalid_un_op_list_algebraic.json", "ValueError"),
        ("data/invalid_un_op_nested_list_algebraic.json", "ValueError"),
        ("data/wrong_un_len_algebraic.json", "ValueError"),
    ],
)
def test_init_errors(json_path, expected):
    try:
        JSONParser(json_path).initialize_network()
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, csv_path, tag_name, data_type, expected_path, expected_units",
    [
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "GrossGasProduction",
            "DataFrame",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "ElectricityProductionByGasVolume",
            "DataFrame",
            "data/electrical_efficiency.csv",
            "kilowatt * hour * minute / (feet ** 3)",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "GrossGasProduction",
            "Dict",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "ElectricityProductionByGasVolume",
            "Dict",
            "data/electrical_efficiency.csv",
            "kilowatt * hour * minute / (feet ** 3)",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/array_division.csv",
            "ElectricityProductionByGasVolume",
            "Array",
            "data/electrical_efficiency.csv",
            "kilowatt * hour * minute / (feet ** 3)",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/array_division.csv",
            "ElectricityProductionByGasVolume",
            "List",
            "data/electrical_efficiency.csv",
            "kilowatt * hour * minute / (feet ** 3)",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "GrossGasProduction",
            "Array",
            "ValueError",
            "SCFM",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_array.csv",
            "GrossGasProduction",
            "Array",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_array.csv",
            "GrossGasProduction",
            "List",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_array.csv",
            "GrossGasProduction",
            "Invalid",
            "TypeError",
            "SCFM",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "NoGasPurchases",
            "DataFrame",
            "data/no_gas_bool.csv",
            None,
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "NoGasPurchases",
            "Dict",
            "data/no_gas_bool.csv",
            None,
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/gas_purchases.csv",
            "NoGasPurchases",
            "Array",
            "data/no_gas_bool.csv",
            None,
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/gas_purchases.csv",
            "NoGasPurchases",
            "List",
            "data/no_gas_bool.csv",
            None,
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "ElectricityGeneration_RShift2",
            "DataFrame",
            "data/gen_rshift2.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_RShift2",
            "Array",
            "data/gen_rshift2.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_RShift2",
            "List",
            "data/gen_rshift2.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_LShift1",
            "Dict",
            "data/gen_lshift1.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_LShift1",
            "List",
            "data/gen_lshift1.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_LShift1",
            "Array",
            "data/gen_lshift1.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_LShift1",
            "Invalid",
            "TypeError",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGenDelta",
            "Dict",
            "data/gen_delta.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "ElectricityGenNegated",
            "DataFrame",
            "data/gen_negate.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGenNegated",
            "Array",
            "data/gen_negate.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGenNegated",
            "List",
            "data/gen_negate.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGenNegated",
            "Dict",
            "data/gen_negate.csv",
            "kWh",
        ),
        (
            "data/unit_incompat_algebraic.json",
            "data/sample_array.csv",
            "GrossGasProduction",
            "Array",
            "ValueError",
            None,
        ),
        (
            "data/unit_convert_algebraic.json",
            "data/sample_array.csv",
            "GrossGasProduction",
            "Array",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "data/totalized_warning_algebraic.json",
            "data/sample_array.csv",
            "GrossGasProduction",
            "Array",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_Plus1.5",
            "Array",
            "data/elec_gen_plus1point5.csv",
            "kilowatt * hour",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_Plus1.5",
            "List",
            "data/elec_gen_plus1point5.csv",
            "kilowatt * hour",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_Plus1.5",
            "Dict",
            "data/elec_gen_plus1point5.csv",
            "kilowatt * hour",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_Plus1.5",
            "DataFrame",
            "data/elec_gen_plus1point5.csv",
            "kilowatt * hour",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_Divide2",
            "Array",
            "data/elec_gen_divide2.csv",
            "kilowatt * hour",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_Divide2",
            "List",
            "data/elec_gen_divide2.csv",
            "kilowatt * hour",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_Divide2",
            "Dict",
            "data/elec_gen_divide2.csv",
            "kilowatt * hour",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_Divide2",
            "DataFrame",
            "data/elec_gen_divide2.csv",
            "kilowatt * hour",
        ),
    ],
)
def test_calculate_values(
    json_path, csv_path, tag_name, data_type, expected_path, expected_units
):
    parser = JSONParser(json_path)
    if isinstance(expected_path, str) and os.path.isfile(expected_path):
        expected = pd.read_csv(expected_path)
    else:
        expected = expected_path
    try:
        result = parser.initialize_network()
        tag = result.get_tag(tag_name, recurse=True)

        data = pd.read_csv(csv_path)
        if data_type == "DataFrame":
            pd.testing.assert_series_equal(
                tag.calculate_values(data), expected[tag_name]
            )
        elif data_type == "Array":
            data = data.to_numpy()
            assert np.allclose(
                tag.calculate_values(data),
                expected.to_numpy().flatten(),
                equal_nan=True,
            )
        elif data_type == "List":
            data = data.values.T.tolist()
            assert np.allclose(
                np.array(tag.calculate_values(data)),
                expected.values.flatten(),
                equal_nan=True,
            )
        elif data_type == "Dict":
            data = data.to_dict(orient="series")
            pd.testing.assert_series_equal(
                tag.calculate_values(data), expected[tag_name]
            )
        elif data_type == "Invalid":
            data = pd.Series([])
            tag.calculate_values(data)
    except Exception as err:
        result = type(err).__name__
        assert result == expected

    if not (isinstance(expected, str) and expected == "ValueError"):
        if expected_units is not None:
            assert parse_units(expected_units) == tag.units
        else:
            assert tag.units is None


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "constant0, constant1, expected",
    [
        (operations.Constant(-1), operations.Constant(0), True),
        (operations.Constant(0), operations.Constant(-1), False),
        (operations.Constant(100.1), operations.Constant(100.1), False),
        (operations.Constant(1.0), operations.Constant(1), False),
        (operations.Constant(1), operations.Constant(1.0), True),
        (operations.Constant(1, parent_id="ABC"), operations.Constant(1), False),
        (operations.Constant(1), operations.Constant(1, parent_id="XYZ"), True),
        (
            operations.Constant(1, parent_id="ABC"),
            operations.Constant(1, parent_id="XYZ"),
            True,
        ),
        (
            operations.Constant(1, parent_id="ABC"),
            operations.Constant(1, parent_id="ABC"),
            False,
        ),
    ],
)
def test_constant_less_than(constant0, constant1, expected):
    assert (constant0 < constant1) == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "data, un_op, expected_error",
    [
        ("invalid_string", "<<", TypeError),
        (123, ">>", TypeError),
    ],
)
def test_unary_helper(data, un_op, expected_error):
    """
    Simple test for error,
    since value functionality is covered in test_calculate_values
    """
    with pytest.raises(expected_error):
        operations.unary_helper(data, un_op)


# ---------------------------------------------------------------------------
# Custom operations: validate_custom_operation / build_custom_operation
# ---------------------------------------------------------------------------


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "func_str, expected",
    [
        # allowed expressions are returned unchanged
        ("lambda x, y: x + y", "lambda x, y: x + y"),
        ("lambda x: x == 0", "lambda x: x == 0"),
        ("lambda x: x.diff()", "lambda x: x.diff()"),
        ("lambda x: x.shift(-1)", "lambda x: x.shift(-1)"),
        ("lambda x: x[1:] + ['nan']", "lambda x: x[1:] + ['nan']"),
        (
            "lambda x, y: [sum(z) for z in zip(x, y)]",
            "lambda x, y: [sum(z) for z in zip(x, y)]",
        ),
        ("lambda x, y: np.where(x > 0, x, y)", "lambda x, y: np.where(x > 0, x, y)"),
        ("lambda x: x.sum()", "lambda x: x.sum()"),
        ("lambda x: x.rolling(3).mean()", "lambda x: x.rolling(3).mean()"),
        # function application: callable specs and allow-listed string specs
        ("lambda x: x.apply(lambda v: v + 1)", "lambda x: x.apply(lambda v: v + 1)"),
        ("lambda x: x.apply(np.sqrt)", "lambda x: x.apply(np.sqrt)"),
        ("lambda x: x.agg(['sum', 'mean'])", "lambda x: x.agg(['sum', 'mean'])"),
        # nested lambda parameter is scoped (bug fix), not an unknown name
        (
            "lambda x: x.where(x > 0, (lambda v: v))",
            "lambda x: x.where(x > 0, (lambda v: v))",
        ),
        # rejected with a ValueError: not a lambda, or disallowed name/attribute/call
        ("42", "ValueError"),
        ("lambda x: __import__('os').system('id')", "ValueError"),
        ("lambda x: ().__class__.__bases__[0].__subclasses__()", "ValueError"),
        ("lambda x: x.__class__", "ValueError"),
        ("lambda x: open('secrets.txt')", "ValueError"),
        ("lambda x: eval('1')", "ValueError"),
        ("lambda x: getattr(x, 'y')", "ValueError"),
        ("lambda x: pd.read_pickle('payload.pkl')", "ValueError"),
        ("lambda x: np.load('payload.npy', allow_pickle=True)", "ValueError"),
        ("lambda x: x.query('a')", "ValueError"),
        ("lambda x: x.to_csv('out.csv')", "ValueError"),
        # dispatch methods can't name a blocked method via a string spec
        ("lambda x: x.apply('to_pickle')", "ValueError"),
        ("lambda x: x.agg(['sum', 'to_pickle'])", "ValueError"),
        # ... nor by building the name at runtime, nor by passing the method around
        ("lambda x: x.agg('to_' + 'csv')", "ValueError"),
        ("lambda x: (lambda f: f('to_csv'))(x.agg)", "ValueError"),
        ("lambda x: list(map(x.agg, ['to_csv']))", "ValueError"),
        # comprehension/lambda binding may not monkeypatch or leak (bug fixes)
        ("lambda x: [0 for np.where in [1]]", "ValueError"),
        ("lambda x: ([0 for open in x], open)", "ValueError"),
        # default argument values are not allowed (bug fix)
        ("lambda x, y=open: x", "ValueError"),
        # rejected with a SyntaxError: not a valid single expression
        ("", "SyntaxError"),
        ("lambda x: x +", "SyntaxError"),
        ("lambda x: )", "SyntaxError"),
        ("import os", "SyntaxError"),
    ],
)
def test_validate_custom_operation(func_str, expected):
    try:
        result = operations.validate_custom_operation(func_str)
        assert result == expected
    except Exception as err:
        result = type(err).__name__
        assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "func_str, args, expected",
    [
        # correctly-built functions: compiled, called, and result checked
        ("lambda x, y: x + y", (2, 3), 5),
        ("lambda x: x * 2", (4,), 8),
        ("lambda x: abs(x)", (-5,), 5),
        ("lambda x, y: [sum(z) for z in zip(x, y)]", ([1, 2], [10, 20]), [11, 22]),
        # rejected before/at compilation (args unused)
        ("lambda x: __import__('os').system('id')", None, "ValueError"),
        ("lambda x: open('secrets.txt')", None, "ValueError"),
        ("lambda x: x.to_csv('out.csv')", None, "ValueError"),
        ("import os", None, "SyntaxError"),
    ],
)
def test_build_custom_operation(func_str, args, expected):
    try:
        func = operations.build_custom_operation(func_str)
    except Exception as err:
        assert type(err).__name__ == expected
    else:
        assert func(*args) == expected


def tag_sum(n):
    """Same shape of string as get_tag_sum_lambda_func(n units)."""
    args = ",".join(f"tag{i + 1}" for i in range(n))
    body = "+".join(f"tag{i + 1}" for i in range(n))
    return f"lambda {args}: {body}"


# expressions that must be accepted
ACCEPTED = [
    # methods and indexing
    "lambda x: x.diff()",
    "lambda x: x.shift(-1)",
    "lambda x: x.rolling(3).mean()",
    "lambda x: x.rolling(3).mean().fillna(0)",
    "lambda x: x.pct_change()",
    "lambda x: x.sum()",
    "lambda x: x.sort_values()",
    "lambda x: x.interpolate()",
    "lambda df: df.dtypes",
    "lambda x: x.iloc[0]",
    "lambda x: x.T",
    "lambda x: x[::2]",
    "lambda x: x[1:, 0]",
    "lambda x: x[..., 0]",
    "lambda x: x[:, np.newaxis]",
    "lambda x, y: x if y else -x",
    "lambda x: x.str.upper()",
    "lambda x: x.str.extract('(a)')",
    "lambda x: x.dt.hour",
    "lambda x: x.groupby('b').sum()",
    "lambda x: x.resample('2D').mean()",
    # operators, including bitwise and shifts
    "lambda x: (x > 0) & (x < 10)",
    "lambda x: (x > 0) | (x < 10)",
    "lambda x: (x > 0) ^ (x < 10)",
    "lambda x: ~(x > 0)",
    "lambda x: x << 1",
    "lambda x: x >> 1",
    # numpy: top level and submodules
    "lambda a, b: np.where(a > b, a, b)",
    "lambda x: np.sqrt(x)",
    "lambda x: np.log(x) / np.log(10)",
    "lambda x: x * np.pi",
    "lambda x: np.interp(x, [0, 1], [0, 10])",
    "lambda x: np.linalg.norm(x)",
    "lambda x: np.fft.fft(x)",
    "lambda x: np.random.default_rng(0).normal(size=3)",
    "lambda x: np.polynomial.polynomial.polyval(x, [1, 2])",
    "lambda x: np.ma.masked_invalid(x).compressed()",
    "lambda x: np.vectorize(lambda v: v + 1)(x)",
    "lambda x: np.apply_along_axis(lambda r: r.sum(), 0, x)",
    # math / pandas / scipy
    "lambda x: math.sqrt(x)",
    "lambda x: math.pi * x",
    "lambda x: pd.Series(x).rolling(5).mean()",
    "lambda x: pd.to_numeric(x)",
    "lambda x: x + pd.offsets.MonthEnd()",
    "lambda x: sp.stats.zscore(x)",
    "lambda x: scipy.stats.zscore(x)",
    "lambda x: sp.stats.norm.pdf(x)",
    "lambda x: sp.stats.norm.stats(moments='mv')",
    "lambda x, y: sp.stats.linregress(x, y).slope",
    "lambda x: sp.signal.savgol_filter(x, 5, 2)",
    "lambda x: sp.signal.windows.hann(5)",
    "lambda x: sp.optimize.minimize(lambda v: (v[0] - 1) ** 2, [0.0]).x",
    "lambda x: sp.integrate.trapezoid(x)",
    "lambda x: sp.interpolate.interp1d(x, x)(x)",
    "lambda x: sp.ndimage.gaussian_filter1d(x, 1)",
    "lambda x: sp.special.gamma(x)",
    "lambda x: sp.linalg.solve(x, x)",
    "lambda x: sp.sparse.csr_array(x).data",
    "lambda x: sp.spatial.distance.cdist(x, x)",
    "lambda x: sp.constants.g * x",
    # nested lambdas get their own scope
    "lambda x: (lambda r: r + 1)(x)",
    "lambda x: (lambda y: y + x)(1)",
    # comprehensions
    "lambda x: [a + b for a, b in zip(x, x)]",
    "lambda x: [a for a, *rest in x]",
    "lambda x: {a: a for a in x}",
    "lambda x: {a for a in x}",
    "lambda x: sum(a for a in x if a > 0)",
    "lambda x: [b for a in x for b in a]",
    "lambda x: [(lambda: z)() for z in x]",
    # parameters
    "lambda _: _",
    "lambda *a, **k: a",
    # a library name shadowed by a parameter is an ordinary object, so only
    # ALLOWED_ATTRIBUTES applies to it
    "lambda np: np.mean()",
    "lambda x: (lambda m: m.mean())(x)",
    # guarded methods, called directly with a visible function or method name
    "lambda x: x.apply(lambda v: v + 1)",
    "lambda df: df.apply(lambda r: r.sum(), axis=1)",
    "lambda x: x.apply(abs)",
    "lambda x: x.apply(np.sqrt)",
    "lambda x: x.apply(sp.stats.zscore)",
    "lambda x: x.apply('mean')",
    "lambda x: x.agg(np.mean)",
    "lambda x: x.agg(sum)",
    "lambda x: x.agg('sum')",
    "lambda x: x.agg(func='sum')",
    "lambda x: x.agg([np.mean, np.std])",
    "lambda x: x.agg(['sum', 'mean'])",
    "lambda x: x.agg(['sum', np.mean])",
    "lambda x: x.agg({'a': np.mean, 'b': [np.min, np.max]})",
    "lambda x: x.agg({'a': 'sum', 'b': ['min', 'max']})",
    "lambda x: x.aggregate(lambda v: v.max())",
    "lambda x: x.aggregate('mean')",
    "lambda x: x.transform(np.abs)",
    "lambda x: x.transform('cumsum')",
    "lambda x: x.transform(func=lambda v: v - v.mean())",
    "lambda x: x.groupby('b').agg(np.sum)",
    "lambda x: x.groupby('b').agg('sum')",
    "lambda x: x.groupby('b').apply(lambda g: g.sum())",
    "lambda x: x.rolling(3).apply(lambda w: w.max(), raw=True)",
    "lambda x: x.rolling(3).agg(np.mean)",
    "lambda x: x.rolling(3).agg('sum')",
    "lambda x: x.resample('D').agg('sum')",
    "lambda x: x.apply(lambda v: v, axis='columns')",
]


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize("expr", ACCEPTED)
def test_custom_operation_accepted(expr):
    assert operations.validate_custom_operation(expr) == expr
    assert callable(operations.build_custom_operation(expr))


# expressions that must be rejected
REJECTED = [
    # --- regressions from earlier review rounds ---
    "lambda x: [0 for np.sum in [1]]",  # attribute comprehension target
    "lambda x: [0 for x[0] in [1]]",  # subscript comprehension target
    "lambda x: [0 for eval.foo in x]",  # names inside a store target
    "lambda x, y=1: x",  # default values
    "lambda x, *, y=1: x",
    "lambda x, y=globals: x",
    "lambda x: ([0 for open in x], open)",  # comprehension var leaking scope
    "lambda x: ([z for z in x], z)",
    "lambda x: [y for y in y]",  # first iterable sees the enclosing scope
    "lambda x: [a for a in x if b for b in x]",  # b not bound yet in the `if`
    "lambda x: [b for a in x for b in b]",  # a generator's own target
    # --- shadowing does not widen what a library name can do ---
    "lambda np: np.meshgrid(np)",  # a numpy function, not an object attribute
    "lambda x: (lambda m: m.meshgrid(x))(np)",
    "lambda x: (lambda m: m.load('f'))(np)",
    # --- I/O ---
    "lambda x: pd.read_csv('f.csv')",
    "lambda x: pd.read_pickle('f')",
    "lambda x: pd.to_pickle(x, 'f')",
    "lambda x: x.to_csv('f.csv')",
    "lambda x: x.to_pickle('f')",
    "lambda x: x.to_string()",
    "lambda x: x.to_clipboard()",
    "lambda x: x.info()",
    "lambda x: pd.io.common",
    "lambda x: pd.HDFStore('f')",
    "lambda x: np.load('f')",
    "lambda x: np.loadtxt('f')",
    "lambda x: np.fromfile('f')",
    "lambda x: np.savetxt('f', x)",
    "lambda x: np.memmap('f')",
    "lambda x: np.zeros(3).tofile('f')",
    "lambda x: np.zeros(3).dump('f')",
    "lambda x: np.lib.npyio",
    "lambda x: np.lib.stride_tricks.as_strided(x)",
    "lambda x: np.rec.fromfile",
    "lambda x: sp.io.loadmat('f')",
    "lambda x: sp.io.wavfile",
    "lambda x: sp.datasets.face()",
    "lambda x: sp.sparse.load_npz('f')",
    "lambda x: sp.sparse.save_npz('f', x)",
    # --- evaluation / dispatch by string ---
    "lambda x: pd.eval('1')",
    "lambda x: x.eval('a + 1')",
    "lambda x: x.query('a > 1')",
    "lambda x: pd.pivot_table(x)",
    "lambda x: x.pivot_table()",
    "lambda x: pd.crosstab(x, x)",
    "lambda x: np.bmat('a b')",
    "lambda x: np.f2py",
    "lambda x: '{0}'.format(x)",
    "lambda x: '{0}'.format_map(x)",
    # --- process-wide state ---
    "lambda x: np.random.seed(0)",
    "lambda x: np.random.set_state(0)",
    "lambda x: np.seterr(all='ignore')",
    "lambda x: np.errstate(all='ignore')",
    "lambda x: np.set_printoptions()",
    "lambda x: pd.set_option('a', 1)",
    "lambda x: pd.options",
    "lambda x: pd.api",
    "lambda x: sp.fft.set_workers(2)",
    "lambda x: sp.constants.physical_constants",
    "lambda x: np.typecodes",
    # --- raw memory / native code ---
    "lambda x: x.ctypes",
    "lambda x: x.resize(3)",
    "lambda x: x.setflags(write=True)",
    "lambda x: np.random.PCG64().cffi",
    "lambda x: np.random.PCG64().ctypes",
    "lambda x: np.ctypeslib",
    "lambda x: np.from_dlpack(x)",
    "lambda x: np.ma.masked_array(x).ids()",
    "lambda x: sp.LowLevelCallable",
    "lambda x: sp.linalg.blas",
    "lambda x: sp.linalg.get_blas_funcs",
    "lambda x: sp.special.cython_special",
    # --- environment / plotting / internals ---
    "lambda x: np.show_config()",
    "lambda x: np.info(x)",
    "lambda x: np.testing",
    "lambda x: pd.testing",
    "lambda x: pd.show_versions()",
    "lambda x: x.plot()",
    "lambda x: x.hist()",
    "lambda x: x.style",
    "lambda x: sp.spatial.voronoi_plot_2d",
    "lambda x: np.core",
    "lambda x: pd.core",
    "lambda x: pd.compat",
    "lambda x: np.stats",
    "lambda x: sp.zscore(x)",
    "lambda x: x.zscore()",
    "lambda x: sp.stats.stats",  # deprecated alias module
    "lambda x: sp.stats.contingency.reduce",  # leaked functools.reduce
    "lambda x: math.sqrt.foo",
    # --- frame / generator / dunder access ---
    "lambda x: x.__class__",
    "lambda x: x.T.__class__",
    "lambda x: (a for a in x).gi_frame",
    "lambda x: x.f_back",
    "lambda x: x.f_globals",
    "lambda x: np.__dict__",
    # --- names ---
    "lambda x: open('f')",
    "lambda x: getattr(x, 'a')",
    "lambda x: __import__('os')",
    "lambda x: eval('1')",
    "lambda x: globals()",
    "lambda x: type(x)",
    "lambda x: _hidden",
    # --- syntax ---
    "lambda x: f'{x}'",
    "lambda x: (y := x)",
    "lambda: (yield)",
    # --- not a single lambda ---
    "x + 1",
    "np.sqrt",
    # --- guarded methods: names that are not allowed methods ---
    "lambda x: x.agg('to_csv')",
    "lambda x: x.agg('to_pickle')",
    "lambda x: x.apply('to_csv')",
    "lambda x: x.transform('to_json')",
    "lambda x: x.agg(['sum', 'to_pickle'])",
    "lambda x: x.agg({'a': 'to_csv'})",
    "lambda x: x.agg({'a': [np.mean, 'to_csv']})",
    "lambda x: x.agg(func='to_csv')",
    "lambda x: x.agg('apply')",  # a guarded method is not an allowed method name
    "lambda x: x.agg('__class__')",
    "lambda x: x.agg('load')",
    "lambda x: x.agg('eval')",
    "lambda x: x.groupby('b').agg('to_csv')",
    "lambda x: x.rolling(3).agg('to_csv')",
    "lambda x: x.resample('D').agg('to_csv')",
    # --- guarded methods: anything not visibly a function or an allowed name ---
    "lambda x: x.agg('to_' + 'csv')",  # name built at runtime
    "lambda x: x.apply(('su' + 'm'))",
    "lambda x: x.agg(str('sum'))",
    "lambda x: x.agg(x.name)",
    "lambda x: x.agg(func=None)",
    "lambda x: x.agg()",
    "lambda x: x.agg(total=('a', np.sum))",  # named aggregation: no function given
    "lambda x: x.agg(*['sum'])",
    "lambda x: x.agg(**{'func': 'sum'})",
    "lambda x, f: x.apply(f)",  # value unknown
    "lambda x: [x.apply(f) for f in [np.mean]]",  # comprehension variable
    "lambda x: x.apply(x.sum)",
    "lambda x: x.apply(np.sum(x))",  # a call, not a function
    "lambda x: x.apply(str.upper)",
    "lambda x: pd.DataFrame.apply(x, 'sum')",  # called through the class
    "lambda x: pd.Series.agg(x, np.mean)",
    "lambda x: x.apply",  # not called
    "lambda x: map(x.apply, ['sum'])",  # passed around as a value
    "lambda x: (lambda f: f('to_csv'))(x.agg)",
    "lambda x: list(map(x.agg, ['to_csv']))",
    "lambda x: [x.agg][0]('to_csv')",
    "lambda x: (x.apply if x else x.agg)('to_csv')",
    "lambda np: np.apply",
]


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize("expr", REJECTED)
def test_custom_operation_rejected(expr):
    with pytest.raises(ValueError):
        operations.validate_custom_operation(expr)
    with pytest.raises(ValueError):
        operations.build_custom_operation(expr)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize("expr", ["lambda x: x; 1", "lambda x:", "lambda : ", "x = 1"])
def test_custom_operation_invalid_syntax_raises_syntaxerror(expr):
    with pytest.raises(SyntaxError):
        operations.validate_custom_operation(expr)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize("value", [None, 1, b"lambda x: x", ["lambda x: x"]])
def test_custom_operation_non_string_input_raises_typeerror(value):
    with pytest.raises(TypeError):
        operations.validate_custom_operation(value)
    with pytest.raises(TypeError):
        operations.build_custom_operation(value)


# behaviour of built operations
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_build_evaluates_pandas_ops():
    s = pd.Series([1.0, 3.0, 6.0, 10.0])
    out = operations.build_custom_operation("lambda x: x.diff().shift(-1)")(s)
    assert out.iloc[:3].tolist() == [2.0, 3.0, 4.0]
    assert np.isnan(out.iloc[-1])


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_build_evaluates_boolean_masks_and_shifts():
    s = pd.Series([1, 5, 8, 12])
    mask = operations.build_custom_operation("lambda x: x[(x > 2) & (x < 10)]")
    assert mask(s).tolist() == [5, 8]
    # pandas Series do not implement << / >>; numpy arrays and ints do
    a = np.array([1, 5, 8, 12])
    assert operations.build_custom_operation("lambda x: x << 2")(a).tolist() == [
        4,
        20,
        32,
        48,
    ]
    assert operations.build_custom_operation("lambda x: x >> 1")(a).tolist() == [
        0,
        2,
        4,
        6,
    ]
    assert operations.build_custom_operation("lambda x: x << 3")(1) == 8


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_build_evaluates_numpy_math_and_submodules():
    f = operations.build_custom_operation("lambda a, b: np.where(a > b, a, b)")
    assert f(np.array([1, 5]), np.array([3, 2])).tolist() == [3, 5]
    assert operations.build_custom_operation("lambda x: math.sqrt(x)")(9) == 3
    norm = operations.build_custom_operation("lambda x: np.linalg.norm(x)")
    assert norm(np.array([3.0, 4.0])) == 5.0
    interp = operations.build_custom_operation(
        "lambda x: np.interp(x, [0, 1], [0, 10])"
    )
    assert interp(0.5) == 5.0
    poly = operations.build_custom_operation(
        "lambda x: np.polynomial.polynomial.polyval(x, [1, 2])"
    )
    assert poly(3) == 7.0


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_build_evaluates_scipy():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    out = operations.build_custom_operation("lambda x: sp.stats.zscore(x)")(x)
    np.testing.assert_allclose(out, (x - x.mean()) / x.std())
    pdf = operations.build_custom_operation("lambda x: sp.stats.norm.pdf(x)")(0.0)
    assert pdf == pytest.approx(0.3989422804)
    linregress = operations.build_custom_operation(
        "lambda x, y: sp.stats.linregress(x, y).slope"
    )
    assert linregress(x, 2 * x) == pytest.approx(2.0)
    minimize = operations.build_custom_operation(
        "lambda x: sp.optimize.minimize(lambda v: (v[0] - 1) ** 2, [0.0]).x[0]"
    )
    assert minimize(0) == pytest.approx(1.0, abs=1e-4)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_build_evaluates_guarded_methods():
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [1, 1, 2]})
    build = operations.build_custom_operation
    assert build("lambda df: df.apply(lambda r: r.sum(), axis=1)")(df).tolist() == [
        2.0,
        3.0,
        5.0,
    ]
    assert build("lambda df: df['a'].agg(np.mean)")(df) == 2.0
    assert build("lambda df: df['a'].agg('sum')")(df) == 6.0
    assert build("lambda df: df['a'].agg(['min', 'max'])")(df).tolist() == [1.0, 3.0]
    assert build("lambda df: df['a'].agg([np.min, np.max])")(df).tolist() == [1.0, 3.0]
    assert build("lambda df: df.groupby('b')['a'].agg(np.sum)")(df).tolist() == [
        3.0,
        3.0,
    ]
    assert build("lambda df: df.groupby('b')['a'].agg('sum')")(df).tolist() == [
        3.0,
        3.0,
    ]
    centered = build("lambda df: df['a'].transform(lambda v: v - v.mean())")
    assert centered(df).tolist() == [-1.0, 0.0, 1.0]


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_build_evaluates_nested_lambda_and_comprehension():
    build = operations.build_custom_operation
    assert build("lambda x: (lambda y: y + 1)(x)")(2) == 3
    assert build("lambda xs: sum(v * 2 for v in xs)")([1, 2, 3]) == 12
    assert build("lambda x: [a + b for a, b in zip(x, x)]")([1, 2]) == [2, 4]


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_only_the_libraries_an_expression_uses_are_loaded():
    f = operations.build_custom_operation("lambda x: math.sqrt(x)")
    assert "math" in f.__globals__
    assert "np" not in f.__globals__ and "sp" not in f.__globals__
    g = operations.build_custom_operation("lambda x: np.sqrt(x)")
    assert "np" in g.__globals__ and "math" not in g.__globals__


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_restricted_builtins_are_the_only_builtins():
    f = operations.build_custom_operation("lambda x: len(x)")
    assert f.__globals__["__builtins__"] is operations.SAFE_BUILTINS


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_inplace_and_out_are_deliberately_allowed():
    # Mutating the caller's data is a side effect, not an escape from the
    # restrictions, and is permitted by design (see the comment above ALLOWED_NODES).
    s = pd.Series([1.0, None, 3.0])
    operations.build_custom_operation("lambda x: x.fillna(0, inplace=True)")(s)
    assert s.tolist() == [1.0, 0.0, 3.0]
    a = np.array([-1.0, 0.5, 2.0])
    operations.build_custom_operation("lambda x: np.clip(x, 0, 1, out=x)")(a)
    assert a.tolist() == [0.0, 0.5, 1.0]


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_validate_returns_input_unchanged():
    s = "  lambda x: x  "
    assert operations.validate_custom_operation(s) == s


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_whitespace_that_strip_removes_but_eval_would_not_is_fine():
    # validation and compilation share one parse, so there is no
    # validate-one-string / evaluate-another gap
    assert operations.build_custom_operation("\u00a0lambda x: x")(3) == 3


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_count_args():
    assert operations.count_args("lambda a, b: a + b") == 2
    with pytest.raises(ValueError):
        operations.count_args("x + 1")


# size and depth
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize("n", [50, 400, 1000, 2500])
def test_long_sums_validate_build_and_evaluate(n):
    expr = tag_sum(n)
    assert operations.validate_custom_operation(expr) == expr
    assert operations.build_custom_operation(expr)(*range(1, n + 1)) == n * (n + 1) // 2


def _outcome(fn, expr):
    """'ok' or 'rejected'; any other exception (e.g. RecursionError) fails."""
    try:
        fn(expr)
    except (ValueError, SyntaxError):
        return "rejected"
    return "ok"


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "expr",
    [
        "lambda x: x" + ".T" * 5000,
        "lambda x: x" + ".diff()" * 3000,
        "lambda x: " + "-" * 5000 + "x",
        "lambda x: " + "~" * 5000 + "x",
        "lambda x: " + "(" * 400 + "x" + ")" * 400,
        "lambda x: " + "[" * 400 + "x" + "]" * 400,
        "lambda x: " + "x + (" * 150 + "x" + ")" * 150,
        "lambda x: x" + ".agg(np.mean)" * 1500,
        tag_sum(20000),
    ],
    ids=[
        "attr-chain",
        "call-chain",
        "unary-minus",
        "invert",
        "parens",
        "lists",
        "right-nested",
        "guarded-chain",
        "huge-sum",
    ],
)
def test_pathological_depth_never_raises_recursionerror(expr):
    assert _outcome(operations.validate_custom_operation, expr) in ("ok", "rejected")
    assert _outcome(operations.build_custom_operation, expr) in ("ok", "rejected")


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_length_limit(monkeypatch):
    monkeypatch.setattr(operations, "MAX_EXPRESSION_LENGTH", 20)
    with pytest.raises(ValueError, match="too long"):
        operations.validate_custom_operation("lambda x: x + x + x + x + x")
    operations.validate_custom_operation("lambda x: x + x")


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_node_limit(monkeypatch):
    monkeypatch.setattr(operations, "MAX_EXPRESSION_NODES", 6)
    with pytest.raises(ValueError, match="too large"):
        operations.validate_custom_operation("lambda x: x + x + x + x + x")
    operations.validate_custom_operation("lambda x: x")


# ALLOWED_NODES is the single source of truth
@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "removed, expr",
    [
        (ast.GeneratorExp, "lambda x: (a for a in x)"),
        (ast.ListComp, "lambda x: [a for a in x]"),
        (ast.SetComp, "lambda x: {a for a in x}"),
        (ast.DictComp, "lambda x: {a: a for a in x}"),
        (ast.Lambda, "lambda x: (lambda y: y)(x)"),
        (ast.Attribute, "lambda x: x.diff()"),
        (ast.Call, "lambda x: x.agg(np.mean)"),
        (ast.Name, "lambda x: x"),
        (ast.BitAnd, "lambda x: x & x"),
        (ast.LShift, "lambda x: x << 1"),
        (ast.RShift, "lambda x: x >> 1"),
    ],
    ids=lambda v: v.__name__ if isinstance(v, type) else None,
)
def test_removing_a_node_type_rejects_it_everywhere(monkeypatch, removed, expr):
    monkeypatch.setattr(
        operations,
        "ALLOWED_NODES",
        tuple(n for n in operations.ALLOWED_NODES if n is not removed),
    )
    with pytest.raises(ValueError, match="Disallowed syntax"):
        operations.validate_custom_operation(expr)


# ---------------------------------------------------------------------------
# The generated allow-lists
# ---------------------------------------------------------------------------


def walk_tree(nodes=None, path=()):
    """Yield (path, node) for every namespace in the generated allow-list."""
    nodes = operations.ALLOWED_MODULE_MEMBERS if nodes is None else nodes
    if not path:
        for name, node in nodes.items():
            yield from walk_tree(node, (name,))
        return
    yield path, nodes
    for child, child_node in nodes["modules"].items():
        yield from walk_tree(child_node, path + (child,))


def is_installed_copy():
    """Whether the package under test was installed (site-packages), not checked out."""
    parts = pathlib.Path(operations.__file__).resolve().parts
    return "site-packages" in parts or "dist-packages" in parts


def generator_candidates():
    """Where generate_allowlist.py may be: in the package (it ships with the tests),
    or, in a source checkout only, at the top of the repository. The repository root
    is not searched in an installed copy, because there it would be site-packages
    itself, and any other installed distribution could drop a file there for the
    tests to run."""
    here = pathlib.Path(__file__).resolve()
    roots = [here.parents[1]]
    if not is_installed_copy():
        roots += here.parents[2:3]
    return [
        root / folder / "generate_allowlist.py"
        for root in roots
        for folder in ("scripts", "tools")
    ]


def load_generator():
    """Import generate_allowlist.py.

    It ships with the tests so that an installed copy can be verified, which means a
    missing generator is always a failure: skipping would quietly turn off the checks
    that guard the allow-list.
    """
    candidates = generator_candidates()
    for path in candidates:
        if path.is_file():
            spec = importlib.util.spec_from_file_location("generate_allowlist", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    pytest.fail(
        "generate_allowlist.py not found, so the allow-list checks cannot run. "
        "It must ship with the tests (check the package data). "
        "Looked in: " + ", ".join(str(path) for path in candidates)
    )


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_shadowing_probe_is_meaningful():
    # the shadowing cases in REJECTED rely on `meshgrid` being reachable through
    # numpy but not as an attribute of ordinary objects
    assert "meshgrid" in operations.ALLOWED_MODULE_MEMBERS["numpy"]["names"]
    assert "meshgrid" not in operations.ALLOWED_ATTRIBUTES


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_constants_are_consistent():
    assert set(operations.MODULE_ALIASES.values()) == set(
        operations.ALLOWED_MODULE_MEMBERS
    )
    assert operations.ALLOWED_NAMES == frozenset(operations.MODULE_ALIASES)
    assert set(operations.SAFE_BUILTINS) == set(operations.SAFE_BUILTIN_NAMES)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_tree_is_well_formed():
    for path, node in walk_tree():
        assert set(node) == {"names", "modules"}, path
        assert isinstance(node["names"], frozenset), path
        assert isinstance(node["modules"], dict), path
        assert not (
            node["names"] & set(node["modules"])
        ), f"{path}: name is both a member and a submodule"


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_guarded_methods_are_not_ordinary_attributes():
    assert operations.GUARDED_METHODS == frozenset(
        {"agg", "aggregate", "apply", "transform"}
    )
    assert not (operations.GUARDED_METHODS & operations.ALLOWED_ATTRIBUTES)
    for path, node in walk_tree():
        assert not (operations.GUARDED_METHODS & node["names"]), path


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_no_underscore_names_are_allow_listed():
    # the underscore check on free names is belt-and-braces: an unbound name
    # is already rejected unless it is in one of these sets
    free = operations.ALLOWED_NAMES | operations.SAFE_BUILTIN_NAMES
    assert not [n for n in free if n.startswith("_")]
    assert not [n for n in operations.ALLOWED_ATTRIBUTES if n.startswith("_")]
    for path, node in walk_tree():
        assert not [n for n in node["names"] if n.startswith("_")], path


# An independent re-statement of what must never be allow-listed. (The generator
# has its own rules; this test fails if a rule there is loosened by mistake.)
NEVER_ANYWHERE = re.compile(
    r"read_\w+|to_(csv|excel|json|hdf|sql|parquet|feather|html|latex|markdown|xml|"
    r"clipboard|stata|orc|pickle|string|xarray)|load|loads|loadtxt|save|savez|savetxt|"
    r"dump|dumps|tofile|fromfile|fromregex|genfromtxt|memmap|open|eval|exec|compile|"
    r"query|pivot_table|crosstab|NamedAgg|bmat|ctypes|cffi|ids|as_strided|byte_bounds|"
    r"from_dlpack|LowLevelCallable|get_blas_funcs|get_lapack_funcs|cython_\w+|seed|"
    r"set_state|set_printoptions|seterr|seterrcall|setbufsize|errstate|printoptions|"
    r"set_option|reset_option|option_context|options|show_config|show_runtime|"
    r"show_versions|get_include|lookfor|who|test|tests|plot|boxplot|style|dendrogram|"
    r"agg|aggregate|apply|transform"
)
NEVER_ON_OBJECTS = re.compile(
    r"format|format_map|resize|setflags|info|source|hist|lock"
)
# Reviewed and allowed in a specific namespace despite matching a pattern above.
# These share a *name* with something dangerous elsewhere, but are plain numeric
# functions.
PERMITTED = {
    # builds a sparse block matrix; unlike numpy.bmat it takes no string
    ("scipy.sparse", "bmat"),
    # contingency table; unlike pandas.crosstab, it has no aggfunc
    ("scipy.stats.contingency", "crosstab"),
}


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_no_dangerous_names_are_allow_listed():
    offenders = []
    for path, node in walk_tree():
        for name in node["names"]:
            if (
                NEVER_ANYWHERE.fullmatch(name)
                and (".".join(path), name) not in PERMITTED
            ):
                offenders.append((".".join(path), name))
    for name in operations.ALLOWED_ATTRIBUTES:
        if NEVER_ANYWHERE.fullmatch(name) or NEVER_ON_OBJECTS.fullmatch(name):
            offenders.append(("<attribute>", name))
    assert not offenders, offenders


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_no_unreviewed_name_collisions_with_modules():
    """A module can be passed around as a value (``lambda m: m.load``), and then
    ALLOWED_ATTRIBUTES applies to it. So an allowed attribute name must not also
    reach a member of an enumerated library that was *not* allowed there, unless
    the collision was reviewed (REVIEWED_MODULE_COLLISIONS)."""
    problems = []
    for path, node in walk_tree():
        module = operations._resolve_namespace(path)
        reachable = node["names"] | set(node["modules"])
        unreviewed = (
            operations.ALLOWED_ATTRIBUTES
            - reachable
            - operations.REVIEWED_MODULE_COLLISIONS
        )
        for name in sorted(unreviewed):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")  # e.g. np.bytes warns on access
                    present = hasattr(module, name)
            except Exception:
                present = True
            if present:
                problems.append((".".join(path), name))
    assert not problems, problems


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_every_allow_listed_member_resolves():
    missing = []
    for path, node in walk_tree():
        module = operations._resolve_namespace(path)
        for name in sorted(node["names"] | set(node["modules"])):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if not hasattr(module, name):
                    missing.append(f"{'.'.join(path)}.{name}")
    assert not missing, (
        "allow-listed names that do not exist in the installed libraries "
        f"(re-run scripts/generate_allowlist.py): {missing}"
    )


def normalize_versions(versions):
    """Compare Python by major.minor, so that a patch release is not a difference."""
    return re.sub(r"Python (\d+\.\d+)\.\d+", r"Python \1", versions or "")


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_generator_refuses_to_rewrite_an_installed_copy(tmp_path, monkeypatch):
    gen = load_generator()
    installed = tmp_path / "lib" / "site-packages" / "pype_schema"
    installed.mkdir(parents=True)
    copy = installed / "operations.py"
    copy.write_text(pathlib.Path(operations.__file__).read_text())
    before = copy.read_text()
    monkeypatch.setattr(sys, "argv", ["generate_allowlist.py", "--target", str(copy)])
    with pytest.raises(SystemExit, match="refusing to rewrite"):
        gen.main()
    assert copy.read_text() == before


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_generated_block_has_not_been_edited_by_hand():
    """Tamper check. Rebuild the generated block from the values it defines and
    compare it, character for character, with the text in operations.py. Anything
    else in there (an extra name that the data does not account for, or any other
    statement hidden among the names) makes the texts differ. This does not depend
    on which library versions are installed."""
    gen = load_generator()
    source = pathlib.Path(operations.__file__).read_text()
    block = gen.extract_block(source)
    expected = gen.render_block(
        gen.tree_from_frozen(operations.ALLOWED_MODULE_MEMBERS),
        set(operations.ALLOWED_ATTRIBUTES),
        set(operations.REVIEWED_MODULE_COLLISIONS),
        gen.block_versions(block),
    )
    assert block == expected, (
        "the generated block in operations.py is not exactly what "
        "generate_allowlist.py writes. If you did not edit it by hand, re-run "
        "scripts/generate_allowlist.py; if you did, change the generator's rules "
        "instead and re-run it."
    )
    assert operations.GUARDED_METHODS == frozenset(gen.GUARDED_METHODS)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_frozen_allowlist_matches_installed_libraries():
    """Fails when numpy/pandas/scipy change under the frozen allow-lists, so new
    API is reviewed (re-run generate_allowlist.py and read the diff) instead of
    silently reachable or silently missing."""
    gen = load_generator()
    block = gen.extract_block(pathlib.Path(operations.__file__).read_text())
    recorded_versions = normalize_versions(gen.block_versions(block))
    current_versions = normalize_versions(gen.versions_string())
    fresh = gen.generate()

    frozen = {
        path: (set(node["names"]), set(node["modules"])) for path, node in walk_tree()
    }
    current = {
        ns: (set(n["names"]), set(n["modules"])) for ns, n in fresh["tree"].items()
    }
    problems = []
    for ns in sorted(set(frozen) | set(current)):
        f_names, f_mods = frozen.get(ns, (set(), set()))
        c_names, c_mods = current.get(ns, (set(), set()))
        added = (c_names | c_mods) - (f_names | f_mods)
        removed = (f_names | f_mods) - (c_names | c_mods)
        if added or removed:
            problems.append(
                f"{'.'.join(ns)}: +{sorted(added)[:8]} -{sorted(removed)[:8]}"
            )
    attr_added = sorted(fresh["attrs"] - operations.ALLOWED_ATTRIBUTES)
    attr_removed = sorted(operations.ALLOWED_ATTRIBUTES - fresh["attrs"])
    if attr_added or attr_removed:
        problems.append(f"attributes: +{attr_added[:8]} -{attr_removed[:8]}")
    if problems and is_installed_copy() and recorded_versions != current_versions:
        # someone else's environment: the allow-lists are frozen to the versions they
        # were generated with, so a difference here is expected and not a defect
        pytest.skip(
            f"installed libraries ({current_versions}) differ from the versions the "
            f"allow-lists were generated with ({recorded_versions}); not comparable"
        )
    assert not problems, (
        "the installed numpy/pandas/scipy differ from the versions the allow-lists "
        "were generated with. Run `python scripts/generate_allowlist.py`, review "
        "the diff, and commit it:\n" + "\n".join(problems)
    )
