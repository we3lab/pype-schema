import os
import pint
import pytest
from pype_schema.units import u
from pype_schema.parse_json import JSONParser

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False

# set default pint registry so that custom units like MGD are understood
pint.set_application_registry(u)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, connection_name, num_source, num_dest",
    [
        ("data/connection.json", "GasToCogen", 3, 1),
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
        ("data/connection.json", "GasToCogen", "Digester", "Cogenerator"),
    ],
)
def test_get_source_dest_ids(json_path, connection_name, source_id, dest_id):
    parser = JSONParser(json_path)

    result = parser.initialize_network()
    connection = result.get_connection(connection_name)

    assert connection.get_source_id() == source_id
    assert connection.get_dest_id() == dest_id


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, connection_name, expected",
    [
        (
            "data/connection.json",
            "GasToCogen",
            (600 * u.BTU / u.ft**3, 700 * u.BTU / u.ft**3),
        ),
    ],
)
def test_set_heating_values(json_path, connection_name, expected):
    parser = JSONParser(json_path)

    result = parser.initialize_network()
    connection = result.get_connection(connection_name)

    assert connection.heating_values == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, conn_id_0, conn_id_1, expected",
    [
        ("../data/sample.json", "GasToFacility", "DesalInlet", True),
        ("../data/sample.json", "DesalOutlet", "DesalInlet", True),
        ("../data/sample.json", "ElectricToRecycledWater", "ElectricToDesal", False),
        ("../data/sample.json", "CogenToFacility", "ElectricToDesal", False),
        ("../data/sample.json", "GasToFacility", "CogenToFacility", "TypeError"),
    ],
)
def test_conn_less_than(json_path, conn_id_0, conn_id_1, expected):
    network = JSONParser(json_path).initialize_network()
    conn0 = network.get_connection(conn_id_0, recurse=True)
    conn1 = network.get_connection(conn_id_1, recurse=True)

    try:
        result = conn0 < conn1
    except Exception as err:
        result = type(err).__name__

    assert result == expected
