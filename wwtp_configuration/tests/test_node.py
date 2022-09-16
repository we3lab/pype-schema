import os
import pint
import pickle
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
    "json_path, tag_name, expected_path",
    [
        ("data/node.json", "PumpRuntime", "data/top_level_node_tag.pkl"),
        ("data/node.json", "ElectricityPurchases", "data/top_level_connection_tag.pkl"),
        ("data/node.json", "Digester1Level", "data/lower_level_node_tag.pkl"),
        (
            "data/node.json",
            "CombinedDigesterGasFlow",
            "data/lower_level_connection_tag.pkl",
        ),
        ("data/node.json", "NonexistentTag", None),
    ],
)
def test_get_tag(json_path, tag_name, expected_path):
    parser = JSONParser(json_path)

    result = parser.initialize_network()
    tag = result.get_tag(tag_name)

    expected = None
    if expected_path:
        with open(expected_path, "rb") as pickle_file:
            expected = pickle.load(pickle_file)

    assert tag == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, recurse, connection_path, node_path, tag_path",
    [
        (
            "data/node.json",
            False,
            "data/top_level_connections.pkl",
            "data/top_level_nodes.pkl",
            "data/top_level_tags.pkl"
        ),
        ("data/node.json", True, "data/all_connections.pkl", "data/all_nodes.pkl", "data/all_tags.pkl"),
    ],
)
def test_get_all(json_path, recurse, connection_path, node_path, tag_path):
    parser = JSONParser(json_path)

    result = parser.initialize_network()

    with open(connection_path, "rb") as pickle_file:
        connections = pickle.load(pickle_file)

    with open(node_path, "rb") as pickle_file:
        nodes = pickle.load(pickle_file)

    with open(tag_path, "rb") as pickle_file:
        tags = pickle.load(pickle_file)

    assert result.get_all_connections(recurse=recurse) == connections
    assert result.get_all_nodes(recurse=recurse) == nodes
    assert result.get_all_tags(recurse=recurse) == tags


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, cogen_id, efficiency_arg, expected",
    [
        ("data/connection.json", "Cogenerator", None, 0.32),
        ("data/connection.json", "Cogenerator", 2000, 0.32),
    ],
)
def test_set_energy_efficiency(json_path, cogen_id, efficiency_arg, expected):
    parser = JSONParser(json_path)

    result = parser.initialize_network()
    cogen = result.get_node(cogen_id)

    assert cogen.energy_efficiency(efficiency_arg) == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, recurse, expected_path",
    [
        ("data/node.json", False, []),
        ("data/connection.json", False, "get_cogen.pkl"),
        ("data/node.json", True, "get_cogen.pkl"),
    ],
)
def test_get_cogen_list(json_path, recurse, expected_path):
    parser = JSONParser(json_path)

    result = parser.initialize_network()

    with open(expected_path, "rb") as pickle_file:
        expected = pickle.load(pickle_file)

    assert result.get_cogen(recurse) == expected
