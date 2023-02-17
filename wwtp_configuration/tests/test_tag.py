import os
import pint
import pytest
import pandas as pd
from wwtp_configuration.units import u
from wwtp_configuration.utils import parse_units
from wwtp_configuration.parse_json import JSONParser

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False

# set default pint registry so that custom units like MGD are understood
pint.set_application_registry(u)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, csv_path, tag_name, expected_path, expected_units",
    [
        (
            "../data/sample.json",
            "data/sample_data.csv",
            "GrossGasProduction",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "../data/sample.json",
            "data/sample_data.csv",
            "ElectricityProductionByGasVolume",
            "data/electrical_efficiency.csv",
            "kilowatt * hour * minute / (feet ** 3)",
        ),
    ],
)
def test_calculate_values(json_path, csv_path, tag_name, expected_path, expected_units):
    parser = JSONParser(json_path)
    result = parser.initialize_network()
    tag = result.get_tag(tag_name, recurse=True)

    # TODO: add numpy array and list test cases
    data = pd.read_csv(csv_path)
    expected = pd.read_csv(expected_path)

    pd.testing.assert_series_equal(tag.calculate_values(data), expected[tag_name])

    assert parse_units(expected_units) == tag.units
