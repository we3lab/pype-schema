import os
import pint
import pytest
import numpy as np
import pandas as pd
from pype_schema.units import u
from pype_schema.tag import Tag, TagType, check_type_compatibility
from pype_schema.utils import parse_units, ContentsType
from pype_schema.parse_json import JSONParser

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False

# set default pint registry so that custom units like MGD are understood
pint.set_application_registry(u)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, expected",
    [
        ("data/invalid_tag.json", "KeyError"),
        ("data/invalid_bin_op.json", "ValueError"),
        ("data/no_op.json", "ValueError"),
        ("data/wrong_op_len.json", "ValueError"),
        ("data/tag_type_incompat.json", "ValueError"),
        ("data/tag_contents_incompat.json", "ValueError"),
    ],
)
def test_init_errors(json_path, expected):
    try:
        result = JSONParser(json_path).initialize_network()
    except Exception as err:
        result = type(err).__name__
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, csv_path, tag_name, data_type, expected_path, expected_units",
    [
        (
            "../data/wrrf_sample.json",
            "data/sample_data.csv",
            "GrossGasProduction",
            "DataFrame",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "../data/wrrf_sample.json",
            "data/sample_data.csv",
            "ElectricityProductionByGasVolume",
            "DataFrame",
            "data/electrical_efficiency.csv",
            "kilowatt * hour * minute / (feet ** 3)",
        ),
        (
            "../data/wrrf_sample.json",
            "data/sample_data.csv",
            "GrossGasProduction",
            "Dict",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "../data/wrrf_sample.json",
            "data/sample_data.csv",
            "ElectricityProductionByGasVolume",
            "Dict",
            "data/electrical_efficiency.csv",
            "kilowatt * hour * minute / (feet ** 3)",
        ),
        (
            "../data/wrrf_sample.json",
            "data/sample_data.csv",
            "GrossGasProduction",
            "Array",
            "ValueError",
            "SCFM",
        ),
        (
            "../data/wrrf_sample.json",
            "data/sample_array.csv",
            "GrossGasProduction",
            "Array",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "../data/wrrf_sample.json",
            "data/sample_array.csv",
            "GrossGasProductionList",
            "List",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "../data/wrrf_sample.json",
            "data/sample_array.csv",
            "GrossGasProduction",
            "Invalid",
            "TypeError",
            "SCFM",
        ),
        (
            "../data/wrrf_sample.json",
            "data/sample_data.csv",
            "NoGasPurchases",
            "DataFrame",
            "data/no_gas_bool.csv",
            None,
        ),
        (
            "../data/wrrf_sample.json",
            "data/sample_data.csv",
            "NoGasPurchases",
            "Dict",
            "data/no_gas_bool.csv",
            None,
        ),
        (
            "../data/wrrf_sample.json",
            "data/gas_purchases.csv",
            "NoGasPurchases",
            "Array",
            "data/no_gas_bool.csv",
            None,
        ),
        (
            "../data/wrrf_sample.json",
            "data/gas_purchases.csv",
            "NoGasPurchasesList",
            "List",
            "data/no_gas_bool.csv",
            None,
        ),
        (
            "../data/wrrf_sample.json",
            "data/sample_data.csv",
            "ElectricityGeneration_RShift2",
            "DataFrame",
            "data/gen_rshift2.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_RShift2_List",
            "List",
            "data/gen_rshift2.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_LShift1",
            "Dict",
            "data/gen_lshift1.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_LShift1_List",
            "List",
            "data/gen_lshift1.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_LShift1",
            "Invalid",
            "TypeError",
            "kWh",
        ),
        (
            "../data/wrrf_sample.json",
            "data/elec_gen.csv",
            "ElectricityGenDelta",
            "Dict",
            "data/gen_delta.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample.json",
            "data/sample_data.csv",
            "ElectricityProductionByGasVolume",
            "DataFrame",
            "data/electrical_efficiency.csv",
            "kilowatt * hour / SCFM",
        ),
        (
            "data/connection_less_than.json",
            "data/sample_data.csv",
            "ElectricityGenerationComputed",
            "DataFrame",
            "data/elec_gen_comp.csv",
            "kilowatt * hour",
        ),
        (
            "data/connection_less_than.json",
            "data/sample_data.csv",
            "ElectricityGenerationConstant",
            "DataFrame",
            "data/elec_gen_con.csv",
            "kilowatt * hour",
        ),
    ],
)
def test_calculate_values(
    json_path, csv_path, tag_name, data_type, expected_path, expected_units
):
    parser = JSONParser(json_path)
    result = parser.initialize_network()
    tag = result.get_tag(tag_name, recurse=True)

    data = pd.read_csv(csv_path)
    if isinstance(expected_path, str) and os.path.isfile(expected_path):
        expected = pd.read_csv(expected_path)
    else:
        expected = expected_path

    try:
        if data_type == "DataFrame":
            pd.testing.assert_series_equal(
                tag.calculate_values(data), expected[tag_name]
            )
        elif data_type == "Array":
            data = data.to_numpy()
            assert np.allclose(
                tag.calculate_values(data),
                expected.to_numpy().flatten(),
                equal_nan=True,
            )
        elif data_type == "List":
            data = data.values.T.tolist()
            tag.calculate_values(data)
            assert np.allclose(
                np.array(tag.calculate_values(data), dtype=np.float64),
                expected.values.flatten(),
                equal_nan=True,
            )
        elif data_type == "Dict":
            data = data.to_dict(orient="series")
            pd.testing.assert_series_equal(
                tag.calculate_values(data), expected[tag_name]
            )
        elif data_type == "Invalid":
            data = pd.Series([])
            tag.calculate_values(data)
    except Exception as err:
        result = type(err).__name__
        assert result == expected

    if expected_units is not None:
        assert parse_units(expected_units) == tag.units
    else:
        assert tag.units is None


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "id, contents, tag_type, source_unit_id, dest_unit_id, units, parent_id, "
    "totalized, expected",
    [
        # Case 0: ensure that equality returns False
        (
            ("SameID", "SameID"),
            (ContentsType.Biogas, ContentsType.Biogas),
            (TagType.Flow, TagType.Flow),
            ("total", "total"),
            ("total", "total"),
            (u.meter, u.meter),
            ("Same", "Same"),
            (True, True),
            False,
        ),
        # Case 1: different contents with False result
        (
            ("SameID", "SameID"),
            (ContentsType.Biogas, ContentsType.Electricity),
            (TagType.Flow, TagType.Flow),
            ("total", "total"),
            ("total", "total"),
            (u.meter, u.meter),
            ("Same", "Same"),
            (True, True),
            True,
        ),
        # Case 2: different contents with True result
        (
            ("SameID", "SameID"),
            (ContentsType.Groundwater, ContentsType.Electricity),
            (TagType.Flow, TagType.Flow),
            ("total", "total"),
            ("total", "total"),
            (u.meter, u.meter),
            ("Same", "Same"),
            (True, True),
            False,
        ),
        # Case 3: different source unit IDs with a total
        (
            ("SameID", "SameID"),
            (ContentsType.Biogas, ContentsType.Biogas),
            (TagType.Flow, TagType.Flow),
            (1, "total"),
            ("total", "total"),
            (u.meter, u.meter),
            ("Same", "Same"),
            (True, True),
            True,
        ),
        # Case 4: different source unit IDs (both numeric)
        (
            ("SameID", "SameID"),
            (ContentsType.Biogas, ContentsType.Biogas),
            (TagType.Flow, TagType.Flow),
            (1, 2),
            ("total", "total"),
            (u.meter, u.meter),
            ("Same", "Same"),
            (True, True),
            True,
        ),
        # Case 5: different source unit IDs (both numeric)
        (
            ("SameID", "SameID"),
            (ContentsType.Biogas, ContentsType.Biogas),
            (TagType.Flow, TagType.Flow),
            (1, 2),
            ("total", "total"),
            (u.meter, u.meter),
            ("Same", "Same"),
            (True, True),
            True,
        ),
        # Case 6: different source unit IDs with a total
        (
            ("SameID", "SameID"),
            (ContentsType.Biogas, ContentsType.Biogas),
            (TagType.Flow, TagType.Flow),
            (2, 2),
            ("total", 3),
            (u.meter, u.meter),
            ("Same", "Same"),
            (True, True),
            False,
        ),
        # Case 7: different source unit IDs (both numeric)
        (
            ("SameID", "SameID"),
            (ContentsType.Biogas, ContentsType.Biogas),
            (TagType.Flow, TagType.Flow),
            (2, 2),
            (4, 2),
            (u.meter, u.meter),
            ("Same", "Same"),
            (True, True),
            False,
        ),
        # Case 8: different units
        (
            ("SameID", "SameID"),
            (ContentsType.Biogas, ContentsType.Biogas),
            (TagType.Flow, TagType.Flow),
            (2, 2),
            (3, 3),
            (u.foot, u.meter),
            ("Same", "Same"),
            (True, True),
            True,
        ),
        # Case 8: different totalized
        (
            ("SameID", "SameID"),
            (ContentsType.Biogas, ContentsType.Biogas),
            (TagType.Flow, TagType.Flow),
            (2, 2),
            (3, 3),
            (u.foot, u.meter),
            ("Same", "Same"),
            (True, False),
            False,
        ),
    ],
)
def test_tag_less_than(
    id,
    contents,
    tag_type,
    source_unit_id,
    dest_unit_id,
    units,
    parent_id,
    totalized,
    expected,
):
    tags = []
    for i in range(2):
        tags.append(
            Tag(
                id[i],
                units[i],
                tag_type[i],
                source_unit_id[i],
                dest_unit_id[i],
                parent_id[i],
                totalized[i],
                contents[i],
            )
        )

    assert expected == (tags[0] < tags[1])


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, tag_0_id, tag_1_id, expected",
    [
        (
            "../data/wrrf_sample.json",
            "GrossGasProduction",
            "ElectricityProductionByGasVolume",
            True,
        ),
        (
            "../data/wrrf_sample.json",
            "GrossGasProduction",
            "CombinedDigesterGasFlow",
            False,
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "GrossGasProduction",
            "ElectricityProductionByGasVolume",
            True,
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "GrossGasProduction",
            "CombinedDigesterGasFlow",
            False,
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "NoGasPurchases",
            "ElectricityGeneration_RShift2",
            False,
        ),
    ],
)
def test_v_tag_less_than(json_path, tag_0_id, tag_1_id, expected):
    network = JSONParser(json_path).initialize_network()
    tag_0 = network.get_tag(tag_0_id, recurse=True)
    tag_1 = network.get_tag(tag_1_id, recurse=True)
    assert expected == (tag_0 < tag_1)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, tag_0_id, tag_1_id, expected",
    [
        (
            "../data/wrrf_sample.json",
            "GrossGasProduction",
            "GrossGasProductionList",
            True,
        ),
        (
            "../data/wrrf_sample.json",
            "GrossGasProduction",
            "CombinedDigesterGasFlow",
            True,
        ),
        (
            "../data/wrrf_sample.json",
            "GrossGasProduction",
            "ElectricityProductionByGasVolume",
            False,
        ),
    ],
)
def test_check_type_compatability(json_path, tag_0_id, tag_1_id, expected):
    network = JSONParser(json_path).initialize_network()
    tag_0 = network.get_tag(tag_0_id, recurse=True)
    tag_1 = network.get_tag(tag_1_id, recurse=True)
    assert expected == check_type_compatibility(tag_0.tag_type, tag_1.tag_type)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, tag_id, node_id, expected",
    [
        (
            "../data/wrrf_sample.json",
            "GrossGasProduction",
            "Cogenerator",
            "TypeError",
        ),
    ],
)
def test_check_type_incompatability(json_path, tag_id, node_id, expected):
    network = JSONParser(json_path).initialize_network()
    tag = network.get_tag(tag_id, recurse=True)
    node = network.get_node(node_id, recurse=True)
    try:
        result = check_type_compatibility(tag.tag_type, node)
    except Exception as err:
        result = type(err).__name__

    assert expected == result
