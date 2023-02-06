import os
import pint
import pandas as pd
from wwtp_configuration.tag import VirtualTag
from wwtp_configuration.parse_json import JSONParser

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False

# set default pint registry so that custom units like MGD are understood
pint.set_application_registry(u)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, csv_path, tag_name, expected_path",
    [
        # TODO: create test files
        (),
    ],
)
def test_calculate_values(json_path, csv_path, tag_name, expected_path):
    parser = JSONParser(json_path)
    result = parser.initialize_network()
    tag = result.get_tag(tag_name, recurse=True)

    # TODO: add numpy array and list test cases
    data = pd.read_csv(csv_path)
    expected = pd.read_csv(expected_path)

    assert tag.calculate_values(data) == expected
