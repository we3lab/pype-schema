import os
import pint
import pickle
import pytest
from collections import Counter
from pype_schema.units import u
from pype_schema.utils import ContentsType
from pype_schema.tag import Tag, TagType
from pype_schema.parse_json import JSONParser
from pype_schema.node import Cogeneration, Pump
from pype_schema.connection import Pipe, Wire

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
            "Digester1GasFlow",
            "data/lower_level_connection_tag.pkl",
        ),
        ("data/node.json", "NonexistentTag", None),
    ],
)
def test_get_tag(json_path, tag_name, expected_path):
    parser = JSONParser(json_path)
    result = parser.initialize_network()
    tag = result.get_tag(tag_name, recurse=True)

    expected = None
    if expected_path:
        with open(expected_path, "rb") as pickle_file:
            expected = pickle.load(pickle_file)

    assert tag == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, obj_id, recurse, expected",
    [
        ("data/node.json", "Cogenerator", False, None),
        (
            "data/node.json",
            "Cogenerator",
            True,
            Cogeneration(
                "Cogenerator",
                [ContentsType.Biogas, ContentsType.NaturalGas],
                400 * u.kW,
                750 * u.kW,
                600 * u.kW,
                1,
            ),
        ),
        ("data/node.json", "SewerIntake", False, "data/sewer_intake.pkl"),
        ("data/node.json", "InvalidID", True, None),
    ],
)
def test_get_node_or_connection(json_path, obj_id, recurse, expected):
    result = (
        JSONParser(json_path)
        .initialize_network()
        .get_node_or_connection(obj_id, recurse=recurse)
    )
    if isinstance(expected, str) and os.path.isfile(expected):
        with open(expected, "rb") as pickle_file:
            expected = pickle.load(pickle_file)

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, virtual, recurse, connection_path, node_path, tag_path",
    [
        (
            "data/node.json",
            False,
            False,
            "data/top_level_connections.pkl",
            "data/top_level_nodes.pkl",
            "data/top_level_tags.pkl",
        ),
        (
            "data/node.json",
            False,
            True,
            "data/all_connections.pkl",
            "data/all_nodes.pkl",
            "data/all_tags.pkl",
        ),
        (
            "data/node.json",
            True,
            True,
            "data/all_connections.pkl",
            "data/all_nodes.pkl",
            "data/all_tags_virtual.pkl",
        ),
    ],
)
def test_get_all(json_path, virtual, recurse, connection_path, node_path, tag_path):
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
    assert Counter(result.get_all_tags(virtual=virtual, recurse=recurse)) == Counter(
        tags
    )


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
    "json_path, desired_type, recurse, expected",
    [
        ("data/node.json", None, False, "TypeError"),
        ("data/node.json", Cogeneration, False, []),
        ("data/node.json", Pipe, False, "data/get_pipe_no_recurse.pkl"),
        ("data/connection.json", Cogeneration, False, "data/get_cogen.pkl"),
        ("data/node.json", Cogeneration, True, "data/get_cogen.pkl"),
        ("data/node.json", Pipe, True, "data/get_pipe_recurse.pkl"),
    ],
)
def test_get_list_of_type(json_path, desired_type, recurse, expected):
    try:
        parser = JSONParser(json_path)
        result = parser.initialize_network().get_list_of_type(desired_type, recurse)

        if isinstance(expected, str) and os.path.isfile(expected):
            with open(expected, "rb") as pickle_file:
                expected = pickle.load(pickle_file)
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, node_id, expected",
    [
        # Case 1: node does not exist
        ("data/node.json", "InvalidNode", []),
        # Case 2: no incoming connections but node exists
        ("data/node.json", "RawSewagePump", []),
        # Case 3: only normal connections
        ("data/node.json", "Cogenerator", "data/connection_to_cogen.pkl"),
        # Case  4: normal connections and entry_point
        ("data/node.json", "Digester", "data/connection_to_digester.pkl"),
    ],
)
def test_get_all_connections_to(json_path, node_id, expected):
    parser = JSONParser(json_path)
    config = parser.initialize_network()
    result = config.get_all_connections_to(config.get_node(node_id, recurse=True))
    if isinstance(expected, str) and os.path.isfile(expected):
        with open(expected, "rb") as pickle_file:
            expected = pickle.load(pickle_file)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, node_id, expected",
    [
        # # Case 1: node does not exist
        ("data/node.json", "InvalidNode", []),
        # # Case 2: no outgoing connections but node exists
        ("data/node.json", "Cogenerator", []),
        # Case 3: only normal connections
        ("data/node.json", "RawSewagePump", "data/connection_from_sewer.pkl"),
        # Case 4: normal connections and exit_point
        ("data/node.json", "Digester", "data/connection_from_digester.pkl"),
    ],
)
def test_get_all_connections_from(json_path, node_id, expected):
    parser = JSONParser(json_path)
    config = parser.initialize_network()
    result = config.get_all_connections_from(config.get_node(node_id, recurse=True))

    if isinstance(expected, str) and os.path.isfile(expected):
        with open(expected, "rb") as pickle_file:
            expected = pickle.load(pickle_file)

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, tag_path, expected",
    [
        # Case 1: tag does not exist
        ("data/node.json", "NonexistentTag", None),
        # Case 2: tag exists at a top level connection
        (
            "data/node.json",
            "data/top_level_connection_tag.pkl",
            "data/electricty_to_wwtp.pkl",
        ),
        # Case 3: tag exists at a lower level connection
        (
            "data/node.json",
            "data/lower_level_connection_tag.pkl",
            "data/gas_to_cogen.pkl",
        ),
        # Case 4: tag exists at a top level node
        ("data/node.json", "data/top_level_node_tag.pkl", "data/sewage_pump.pkl"),
        # Case 5: tag exists at a lower level node
        ("data/node.json", "data/lower_level_node_tag.pkl", "data/digester.pkl"),
    ],
)
def test_get_parent_from_tag(json_path, tag_path, expected):
    if isinstance(tag_path, str) and os.path.isfile(tag_path):
        with open(tag_path, "rb") as pickle_file:
            tag = pickle.load(pickle_file)
    else:
        tag = Tag(tag_path, None, None, None, None, None)

    parser = JSONParser(json_path)
    config = parser.initialize_network()
    result = config.get_parent_from_tag(tag)
    if isinstance(expected, str) and os.path.isfile(expected):
        with open(expected, "rb") as pickle_file:
            expected = pickle.load(pickle_file)

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, source_id, dest_id, source_unit_id, dest_unit_id, exit_point_id, "
    "entry_point_id, source_node_type, dest_node_type, exit_point_type, "
    "entry_point_type, contents_type, tag_type, obj_type, recurse, expected_ids",
    [
        # Case 0: all objects without recursion
        (
            "data/node.json",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            False,
            [
                "WWTP",
                "SewerIntake",
                "PowerGrid",
                "RawSewagePump",
                "ElectricityToWWTP",
                "GasToGrid",
                "PumpRuntime",
                "ElectricityPurchases",
            ],
        ),
        # Case 1: all objects with recursion
        (
            "data/node.json",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            True,
            [
                "WWTP",
                "SewerIntake",
                "PowerGrid",
                "RawSewagePump",
                "ElectricityToWWTP",
                "GasToGrid",
                "PumpRuntime",
                "Digester1Level",
                "Digester2Level",
                "Digester_SludgeBlend_Level",
                "ElectricityPurchases",
                "GasToCogen",
                "Digester",
                "Cogenerator",
                "Digester1GasFlow",
                "Digester2GasFlow",
                "Digester3GasFlow",
                "Digester_Cogenerator_Biogas_Flow",
            ],
        ),
        # Case 2: no objects match search criteria
        (
            "data/node.json",
            "NonexistentNode",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            True,
            [],
        ),
        # Case 3: return a node, connection, and tag by source
        (
            "data/node.json",
            "RawSewagePump",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            False,
            ["RawSewagePump", "PumpRuntime", "SewerIntake"],
        ),
        # Case 4: return just the connection from Case 2
        (
            "data/node.json",
            "RawSewagePump",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            Pipe,
            False,
            ["SewerIntake"],
        ),
        # Case 5: return just the tag from Case 2
        (
            "data/node.json",
            "RawSewagePump",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            Tag,
            False,
            ["PumpRuntime"],
        ),
        # Case 6: return just the Node from Case 2
        (
            "data/node.json",
            "RawSewagePump",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            Pump,
            False,
            ["RawSewagePump"],
        ),
        # Case 7: return a connection and tag by source node type (with recursion)
        (
            "data/node.json",
            None,
            None,
            None,
            None,
            None,
            None,
            Pump,
            None,
            None,
            None,
            None,
            None,
            None,
            True,
            ["RawSewagePump", "PumpRuntime", "SewerIntake"],
        ),
        # Case 8: return a connection and tags by destination node type (with recursion)
        (
            "data/node.json",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            Cogeneration,
            None,
            None,
            None,
            None,
            None,
            True,
            [
                "GasToCogen",
                "Digester_Cogenerator_Biogas_Flow",
                "Digester1GasFlow",
                "Digester2GasFlow",
                "Digester3GasFlow",
            ],
        ),
        # Case 9: return mutliple tags by numeric source unit ID
        (
            "data/node.json",
            None,
            None,
            2,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            True,
            ["Digester2Level", "Digester2GasFlow"],
        ),
        # Case 10: return a single tag by "total" destination unit ID
        (
            "../data/sample.json",
            "SewerNetwork",
            None,
            None,
            "total",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            False,
            ["InfluentFlow"],
        ),
        # Case 11: return multiple connections by destination without recursion
        (
            "data/node.json",
            None,
            "WWTP",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            False,
            ["ElectricityToWWTP", "SewerIntake", "ElectricityPurchases"],
        ),
        # Case 12: return multiple connections by destination with recursion
        (
            "data/node.json",
            None,
            "WWTP",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            True,
            ["ElectricityToWWTP", "SewerIntake", "ElectricityPurchases"],
        ),
        # Case 13: return objects by exit point
        (
            "data/node.json",
            "Digester",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            Pipe,
            True,
            ["GasToGrid", "GasToCogen"],
        ),
        # Case 14: return objects by dest_id as entry_point_id with recurse set to True
        (
            "data/node.json",
            None,
            "Digester",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            True,
            ["SewerIntake"],
        ),
        # Case 15: bidirectional connection as source but searching for destination
        (
            "../data/sample.json",
            None,
            "TeslaBattery",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            True,
            ["BatteryToFacility"],
        ),
        # Case 16: bidirectional connection as destination but searching for source
        (
            "../data/sample.json",
            "VirtualDemand",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            Wire,
            True,
            ["BatteryToFacility"],
        ),
        # Case 17: all flow tags
        (
            "data/node.json",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            TagType.Flow,
            None,
            True,
            [
                "Digester1GasFlow",
                "Digester2GasFlow",
                "Digester3GasFlow",
                "Digester_Cogenerator_Biogas_Flow",
                "ElectricityPurchases",
            ],
        ),
        # Case 18: node of type Cogenerator
        (
            "data/node.json",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            Cogeneration,
            True,
            ["Cogenerator"],
        ),
        # Case 19: node, tags, and connections associated with id "Digester"
        (
            "data/node.json",
            "Digester",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            True,
            [
                "Digester",
                "GasToCogen",
                "Digester1GasFlow",
                "Digester2GasFlow",
                "Digester3GasFlow",
                "Digester_Cogenerator_Biogas_Flow",
                "Digester_SludgeBlend_Level",
                "Digester1Level",
                "Digester2Level",
                "GasToGrid",
            ],
        ),
        # Case 20: return objects by exit point
        (
            "data/node.json",
            None,
            None,
            None,
            None,
            "Digester",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            False,
            ["GasToGrid"],
        ),
        # Case 21: return objects by entry point
        (
            "data/node.json",
            None,
            None,
            None,
            None,
            None,
            "Digester",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            False,
            ["SewerIntake"],
        ),
        # Case 22: return objects by contents
        (
            "data/node.json",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            ContentsType.Biogas,
            None,
            None,
            False,
            ["GasToGrid"],
        ),
        (
            "data/node.json",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            ContentsType.Biogas,
            None,
            None,
            True,
            [
                "GasToGrid",
                "GasToCogen",
                "Digester1GasFlow",
                "Digester2GasFlow",
                "Digester3GasFlow",
                "Digester_Cogenerator_Biogas_Flow",
            ],
        ),
    ],
)
def test_select_objs(
    json_path,
    source_id,
    dest_id,
    source_unit_id,
    dest_unit_id,
    exit_point_id,
    entry_point_id,
    source_node_type,
    dest_node_type,
    exit_point_type,
    entry_point_type,
    contents_type,
    tag_type,
    obj_type,
    recurse,
    expected_ids,
):
    parser = JSONParser(json_path)
    config = parser.initialize_network()

    result = config.select_objs(
        source_id=source_id,
        dest_id=dest_id,
        source_unit_id=source_unit_id,
        dest_unit_id=dest_unit_id,
        exit_point_id=exit_point_id,
        entry_point_id=entry_point_id,
        source_node_type=source_node_type,
        dest_node_type=dest_node_type,
        exit_point_type=exit_point_type,
        entry_point_type=entry_point_type,
        contents_type=contents_type,
        tag_type=tag_type,
        obj_type=obj_type,
        recurse=recurse,
    )

    expected = []
    for id in expected_ids:
        obj = config.get_tag(id, recurse=True)
        if obj is None:
            obj = config.get_connection(id, recurse=True)
            if obj is None:
                obj = config.get_node(id, recurse=True)

        if obj is not None:
            expected.append(obj)

    # ignore order and test __lt__()
    try:
        assert sorted(result) == sorted(expected)
    except TypeError:
        res = [
            obj for obj in result + expected if obj not in result or obj not in expected
        ]
        assert not res  # confirm that list is empty
