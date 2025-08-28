import os
import json
import pytest
from pype_schema.epyt_utils import epyt2pypes

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "inp_file, out_file, add_nodes, use_name_as_id, expected_path",
    [
        (
            "data/EPANET_Net_3.inp",
            "dummy_output.json",
            False,
            False,
            "data/EPANET_Net_3.json",
        ),
        ("data/L-TOWN.inp", "dummy_output.json", False, False, "data/L-TOWN.json"),
        (
            "data/L-TOWN.inp",
            "dummy_output.json",
            True,
            False,
            "data/L-TOWN-with-nodes.json",
        ),
        (
            "data/L-TOWN.inp",
            "dummy_output.json",
            True,
            True,
            "data/L-TOWN-with-nodes.json",
        ),
        ("data/valve.inp", "dummy_output.json", False, False, "KeyError"),
        ("data/valve.inp", "dummy_output.json", True, False, "ValueError"),
        (
            "data/EPANET_Net_3.inp",
            "dummy_output.json",
            False,
            True,
            "data/EPANET_Net_3_name_as_id.json",
        ),
    ],
)
def test_epyt2pypes(inp_file, out_file, add_nodes, use_name_as_id, expected_path):
    try:
        result = epyt2pypes(
            inp_file, out_file, add_nodes=add_nodes, use_name_as_id=use_name_as_id
        )
        with open(expected_path, "r") as f:
            expected = json.load(f)
    except Exception as err:
        result = type(err).__name__
        expected = expected_path

    assert result == expected
