import os
import pint
import pytest
import pickle
from wwtp_configuration.units import u
from wwtp_configuration.parse_json import JSONParser

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False

# set default pint registry so that custom units like MGD are understood
pint.set_application_registry(u)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, expected_path",
    [
        ("../data/sample.json", "../data/sample.pkl"),
        ("../data/test_key_error.json", "KeyError"),
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
