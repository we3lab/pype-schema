import os
import pint
import pytest
import numpy as np
from pype_schema.units import u
from pype_schema import operations

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
            {
                "delta_t": 2,
                "split": False
            },
            np.array([0.5,0.5,0.5,0.5, np.nan]),
        ),
        (
            np.arange(5),
            {
                "delta_t": 1,
                "split": False
            },
            np.array([1,1,1,1, np.nan]),
        ),   
        (
            np.concatenate([np.arange(3), np.arange(1,-1,-1)]),
            {
                "delta_t": 5,
                "split": True
            },
            (
                np.array([0,0,0.2,0.2, np.nan]),
                np.array([0.2,0.2,0,0, np.nan]),
            ),
        ), 
        (
            np.array([1]),
            {
                "delta_t": 1,
                "split": False
            },
            np.array([np.nan]),
        ),  
        (
            np.array([1]),
            {
                "delta_t": 1,
                "split": True
            },
            (
                np.array([np.nan]),
                np.array([np.nan])
            ),
        ),                                     
    ]
)
def test_get_change(variable, kwargs, expected):
    result = operations.get_change(variable, **kwargs)
    assert np.array_equal(result, expected, equal_nan=True)
