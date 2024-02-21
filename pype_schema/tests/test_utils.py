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
