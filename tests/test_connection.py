import os
import pint
import pytest
from wwtp_configuration.units import u
from wwtp_configuration.parse_json import JSONParser

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False

# set default pint registry so that custom units like MGD are understood
pint.set_application_registry(u)

@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, connection_name, num_source, num_dest",
    [
        ("../data/test_connection.json", "GasToCogen", 3, 1),
    ],
)
def test_get_num_source_dest_units(json_path, connection_name, num_source, num_dest):
    parser = JSONParser(json_path)

    result = parser.initialize_network()
    connection = result.get_connection(connection_name)

    assert connection.get_num_source_units() == num_source
    assert connection.get_num_dest_units() == num_dest


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, connection_name, source_id, dest_id",
    [
        ("../data/test_connection.json", "GasToCogen", "Digester", "Cogenerator"),
    ],
)
def test_get_source_dest_ids(json_path, connection_name, source_id, dest_id):
    parser = JSONParser(json_path)

    result = parser.initialize_network()
    connection = result.get_connection(connection_name)

    assert connection.get_source_id() == source_id
    assert connection.get_dest_id() == dest_id
