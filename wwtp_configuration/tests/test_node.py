import os
import pint
import pickle
import pytest
from collections import Counter
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
            "data/top_level_tags.pkl",
        ),
        (
            "data/node.json",
            True,
            "data/all_connections.pkl",
            "data/all_nodes.pkl",
            "data/all_tags.pkl",
        ),
    ],
)
def test_get_all(json_path, recurse, connection_path, node_path, tag_path):
    parser = JSONParser(json_path)
    result = parser.initialize_network()

    with open(connection_path, "rb") as pickle_file:
        connections = pickle.load(pickle_file)

    assert result.get_all_connections(recurse=recurse) == connections

    with open(node_path, "rb") as pickle_file:
        nodes = pickle.load(pickle_file)

    assert result.get_all_nodes(recurse=recurse) == nodes

    with open(tag_path, "rb") as pickle_file:
        tags = pickle.load(pickle_file)

    # Counter is used so that order is ignored
    assert Counter(result.get_all_tags(recurse=recurse)) == Counter(tags)


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
    "json_path, recurse, expected",
    [
        ("data/node.json", False, []),
        ("data/connection.json", False, "data/get_cogen.pkl"),
        ("data/node.json", True, "data/get_cogen.pkl"),
    ],
)
def test_get_cogen_list(json_path, recurse, expected):
    parser = JSONParser(json_path)

    result = parser.initialize_network()

    if isinstance(expected, str) and os.path.isfile(expected):
        with open(expected, "rb") as pickle_file:
            expected = pickle.load(pickle_file)

    assert result.get_cogen_list(recurse) == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, tag_path, expected",
    [
        # Case 1: node does not exist
        ("data/node.json", "InvalidNode", []),
        # Case 2: no connections but node exists
        ("data/node.json", "PowerGrid", []),
        # Case 3: only normal connections
        ("data/connection.json", "Cogenerator", "data/connection_to_cogen.pkl"),
        # Case 4: normal connections and entry_point
        ("data/node.json", "Digester", "data/connection_to_digester.pkl"),
    ],
)
def test_get_all_connections_to(json_path, node_id, expected):
    parser = JSONParser(json_path)
    config = parser.initialize_network()

    with open(tag_path, "rb") as pickle_file:
        tag = pickle.load(pickle_file)

    with open(expected, "rb") as pickle_file:
        expected = pickle.load(pickle_file)

    result = config.get_all_connections_to(tag)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, tag_path, expected",
    [
        ("data/connection.json", "Digester", []),
        ("data/node.json", "data/combined_gas_tag.pkl", "data/connection_from_gas_flow.pkl"),
        ("data/node.json", "data/electricity_purchase_tag.pkl", "data/connection_from_elec_flow.pkl"),
    ],
)
def test_get_all_connections_from(json_path, node_id, expected):
    parser = JSONParser(json_path)
    config = parser.initialize_network()

    with open(tag_path, "rb") as pickle_file:
        tag = pickle.load(pickle_file)

    with open(expected, "rb") as pickle_file:
        expected = pickle.load(pickle_file)

    result = config.get_all_connections_from(tag)
    assert result == expected

# test_get_parent_from_tag
