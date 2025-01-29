import os
import json
import pytest
from pype_schema.epyt_utils import epyt2pypes

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "inp_file, out_file, expected_path",
    [("data/EPANET Net 3.inp", "dummy_output.json", "data/EPANET Net 3.json")],
)
def test_epyt2pypes(inp_file, out_file, expected_path):
    result = epyt2pypes(inp_file, out_file)
    with open(expected_path, "r") as f:
        expected = json.load(f)
    assert result == expected
