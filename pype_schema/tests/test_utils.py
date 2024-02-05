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
        (
            ["1"],
            "lambda tag1: tag1"
        ),
        (
            ["1","2","3"],
            "lambda tag1,tag2,tag3: tag1+tag2+tag3"
        ),  
        (
            ["total","total","total"],
            "lambda tag1,tag2,tag3: tag1+tag2+tag3"
        )                 
    ],
)
def test_get_tag_sum_lambda_func(unit_ids, expected):
    result = ut.get_tag_sum_lambda_func(unit_ids)
    assert result == expected
