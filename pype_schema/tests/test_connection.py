import os
import pint
import pytest
from pype_schema.units import u
from pype_schema.tag import Tag
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
        ("../data/wrrf_sample.json", "GasToCogen", "DesalInlet", True),
        ("../data/wrrf_sample.json", "DesalOutlet", "DesalInlet", True),
        (
            "../data/wrrf_sample.json",
            "ElectricToRecycledWater",
            "ElectricToDesal",
            False,
        ),
        ("../data/wrrf_sample.json", "CogenElecToFacility", "ElectricToDesal", False),
        ("../data/wrrf_sample.json", "GasToCogen", "CogenElecToFacility", "TypeError"),
        ("../data/wrrf_sample.json", "GasToBoiler", "GasToCogen", True),
        (
            "../data/desal_sample.json",
            "SolidsDisposal",
            "PressureExchangerDisposal",
            "TypeError",
        ),
        (
            "../data/desal_sample.json",
            "WaterBill",
            "ElectricityBill",
            True,
        ),
        (
            "../data/desal_sample.json",
            "Radio",
            "ElectricityBill",
            True,
        ),
        (
            "../data/desal_sample.json",
            "ElectricityBill",
            "PressureExchangerDisposal",
            "TypeError",
        ),
        (
            "../data/desal_sample.json",
            "MixerToPretreat",
            "PretreatToMediaFilter",
            False,
        ),
        (
            "../data/desal_sample.json",
            "SolidsDisposal",
            "AntiscalantDelivery",
            True,
        ),
        (
            "../data/wrrf_sample.json",
            "RecycledWaterOutlet",
            "WWTPToRecycledWater",
            False,
        ),
        (
            "../data/wrrf_sample.json",
            "ElectricToWWTP",
            "CogenElecToFacility",
            False,
        ),
        (
            "../data/wrrf_sample.json",
            "OceanOutfall",
            "WWTPToRecycledWater",
            False,
        ),
        (
            "../data/wrrf_sample.json",
            "OceanOutfall",
            "WWTPToRecycledWater",
            False,
        ),
        (
            "../data/wrrf_sample.json",
            "OceanOutfall",
            "UFToDisinfection",
            False,
        ),
        (
            "data/connection_less_than.json",
            "ElectricToWWTP",
            "ElectricToRecycledWater",
            False,
        ),
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


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, conn_id, flow_rate",
    [
        (
            "data/connection.json",
            "GasToCogen",
            (
                pint.Quantity(1, "MGD"),
                pint.Quantity(4, "MGD"),
                pint.Quantity(3, "MGD"),
            ),
        )
    ],
)
def test_depr_flow_rate(json_path, conn_id, flow_rate):
    network = JSONParser(json_path).initialize_network()
    conn = network.get_connection(conn_id, recurse=True)

    # check empty to start
    with pytest.raises(AttributeError):
        conn.flow_rate
    assert conn.min_flow is None
    assert conn.max_flow is None
    assert conn.design_flow is None

    # set flow_rate and assert warning
    with pytest.warns(DeprecationWarning):
        conn.set_flow_rate(*flow_rate)

    # check expected results
    assert conn.min_flow == flow_rate[0]
    assert conn.max_flow == flow_rate[1]
    assert conn.design_flow == flow_rate[2]

    # delete gen_capacity one-by-one, checking AttributeError
    conn.del_min_flow()
    assert conn.flow_rate == (None, flow_rate[1], flow_rate[2])
    conn.del_max_flow()
    assert conn.flow_rate == (None, None, flow_rate[2])
    conn.del_design_flow()
    assert conn.flow_rate == (None, None, None)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, conn_id, tag_id",
    [
        ("data/connection.json", "GasToCogen", "FakeTag"),
    ],
)
def test_add_get_remove_tag(json_path, conn_id, tag_id):
    tag = Tag(tag_id, None, None, None, None, None)
    network = JSONParser(json_path).initialize_network()
    conn = network.get_connection(conn_id, recurse=True)
    conn.add_tag(tag)
    assert conn.get_tag(tag_id) == tag
    conn.remove_tag(tag_id)
    try:
        conn.get_tag(tag_id)
    except Exception as err:
        assert type(err).__name__ == "KeyError"


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, connection_name, source_id, dest_id, recurse",
    [
        ("data/connection.json", "GasToCogen", "Digester", "Cogenerator", False),
        ("../data/wrrf_sample.json", "SewerIntake", "SewerNetwork", "WWTP", False),
        ("../data/wrrf_sample.json", "SewerIntake", "SewerNetwork", "BarScreen", True),
        (
            "../data/wrrf_sample.json",
            "WWTPToRecycledWater",
            "WWTP",
            "RecycledWaterFacility",
            False,
        ),
        (
            "../data/wrrf_sample.json",
            "WWTPToRecycledWater",
            "SecondaryClarifier",
            "Ultrafiltration",
            True,
        ),
    ],
)
def test_source_dest_nodes(json_path, connection_name, source_id, dest_id, recurse):
    parser = JSONParser(json_path)

    result = parser.initialize_network()
    connection = result.get_connection(connection_name)

    assert connection.get_source_node(recurse=recurse).id == source_id
    assert connection.get_dest_node(recurse=recurse).id == dest_id
