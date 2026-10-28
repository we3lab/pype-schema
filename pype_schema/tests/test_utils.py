import os
import pint
import pytest
from pype_schema.units import u
from pype_schema import utils as ut

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False

# set default pint registry so that custom units like MGD are understood
pint.set_application_registry(u)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "unit_ids, expected",
    [
        (["1"], "lambda tag1: tag1"),
        (["1", "2", "3"], "lambda tag1,tag2,tag3: tag1+tag2+tag3"),
        (["total", "total", "total"], "lambda tag1,tag2,tag3: tag1+tag2+tag3"),
    ],
)
def test_get_tag_sum_lambda_func(unit_ids, expected):
    result = ut.get_tag_sum_lambda_func(unit_ids)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "units, expected",
    [
        ("meters", u.m),
        ("inches", u.inch),
        ("gpd", u.gal / u.day),
        ("cubicfoot", u.ft**3),
        ("m3pd", u.m**3 / u.day),
        ("gallonspermin", u.gal / u.min),
        ("PSI", u.force_pound / (u.inch**2)),
        ("kwh/m3", u.kW * u.hr / (u.m**3)),
        ("error", "UndefinedUnitError"),
    ],
)
def test_parse_units(units, expected):
    try:
        result = ut.parse_units(units)
        assert u.convert(1, expected, result) == pytest.approx(1)
    except Exception as err:
        result = type(err).__name__
        assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "value, units, expected",
    [
        ("1", "day", 1 * u.day),
        ("1.5", "day", 1.5 * u.day),
        (2, "day", 2 * u.day),
        (2.5, None, 2.5),
        ("3", None, 3),
        (None, "day", None),
        (None, None, None),
    ],
)
def test_parse_quantity(value, units, expected):
    result = ut.parse_quantity(value, units)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
def test_parse_quantity_preserves_numeric_type():
    # integer-valued strings stay ints (so reprs render "1 day", not "1.0 day")
    assert isinstance(ut.parse_quantity("1", "day").magnitude, int)
    # non-integer strings become floats
    assert isinstance(ut.parse_quantity("1.5", "day").magnitude, float)


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
        result = ut.validate_custom_operation(func_str)
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
        func = ut.build_custom_operation(func_str)
    except Exception as err:
        assert type(err).__name__ == expected
    else:
        assert func(*args) == expected
