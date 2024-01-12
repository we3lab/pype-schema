import os
import pint
import pytest
import json
import pickle
from pype_schema.units import u
from pype_schema.parse_json import JSONParser

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False

# set default pint registry so that custom units like MGD are understood
pint.set_application_registry(u)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, expected_path",
    [
        ("../data/sample.json", "data/sample.pkl"),
        ("data/key_error.json", "KeyError"),
        ("data/sample_nested_vtag.json", "data/sample_nested_vtag.pkl"),
    ],
)
def test_create_network(json_path, expected_path):
    parser = JSONParser(json_path)
    try:
        result = parser.initialize_network()
        with open(expected_path, "rb") as pickle_file:
            expected = pickle.load(pickle_file)
    except Exception as err:
        result = type(err).__name__
        expected = expected_path
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, original_network_path, node_id, inplace, expected_path",
    [
        (
            "data/sewer_expansion.json",
            "../data/sample.json",
            None,
            False,
            "data/merged.json",
        ),
        (
            "data/wwtp_expansion.json",
            "../data/sample.json",
            "WWTP",
            False,
            "data/merged_wwtp.json",
        ),
        (
            "data/wwtp_expansion.json",
            "../data/sample.json",
            "WWTP",
            True,
            "data/merged_wwtp.json",
        ),
    ],
)
def test_merge_network(json_path, original_network_path, node_id, inplace, expected_path):
    parser = JSONParser(json_path)
    expected = JSONParser(expected_path).initialize_network()
    if node_id:
        original = JSONParser(original_network_path).initialize_network().get_node(node_id)
        expected = expected.get_node(node_id)
    else:
        original = original_network_path

    result = parser.merge_network(original, inplace=inplace)
    assert result == expected
    assert inplace == (expected == parser.network_obj)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize("json_path", [("../data/sample.json")])
def test_to_json(
    json_path,
):
    expected = JSONParser(json_path).initialize_network()
    JSONParser.to_json(expected, "data/test_to_json.json")
    result = JSONParser("data/test_to_json.json").initialize_network()
    assert result == expected
