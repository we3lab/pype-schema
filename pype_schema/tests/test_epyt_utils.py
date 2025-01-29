import os
import json
import pytest
from pype_schema.epyt_utils import epyt2pypes

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "inp_file, out_file, add_nodes, expected_path",
    [
        ("data/EPANET_Net_3.inp", "dummy_output.json", False, "data/EPANET_Net_3.json"),
        ("data/L-TOWN.inp", "data/L-TOWN.json", False, "KeyError"),
        ("data/L-TOWN.inp", "data/L-TOWN.json", True, "ValueError"),
    ],
)
def test_epyt2pypes(inp_file, out_file, add_nodes, expected_path):
    try:
        result = epyt2pypes(inp_file, out_file, add_nodes=add_nodes)
        with open(expected_path, "r") as f:
            expected = json.load(f)
    except Exception as err:
        result = type(err).__name__
        expected = expected_path

    assert result == expected
