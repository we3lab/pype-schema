import os
import pint
import pytest
import numpy as np
import pandas as pd
from pype_schema.units import u
from pype_schema import operations
from pype_schema.utils import parse_units
from pype_schema.parse_json import JSONParser

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False

# set default pint registry so that custom units like MGD are understood
pint.set_application_registry(u)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "variable, kwargs, expected",
    [
        (
            np.arange(5),
            {"delta_t": 2, "split": False},
            np.array([0.5, 0.5, 0.5, 0.5, np.nan]),
        ),
        (
            np.arange(5),
            {"delta_t": 1, "split": False},
            np.array([1, 1, 1, 1, np.nan]),
        ),
        (
            np.concatenate([np.arange(3), np.arange(1, -1, -1)]),
            {"delta_t": 5, "split": True},
            (
                np.array([0, 0, 0.2, 0.2, np.nan]),
                np.array([0.2, 0.2, 0, 0, np.nan]),
            ),
        ),
        (
            np.array([1]),
            {"delta_t": 1, "split": False},
            np.array([np.nan]),
        ),
        (
            np.array([1]),
            {"delta_t": 1, "split": True},
            (np.array([np.nan]), np.array([np.nan])),
        ),
    ],
)
def test_get_change(variable, kwargs, expected):
    result = operations.get_change(variable, **kwargs)
    assert np.array_equal(result, expected, equal_nan=True)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, expected",
    [
        ("data/no_bin_op_algebraic.json", "ValueError"),
        ("data/invalid_bin_op_algebraic.json", "ValueError"),
        ("data/invalid_bin_op_list_algebraic.json", "ValueError"),
        ("data/wrong_bin_len_algebraic.json", "ValueError"),
        ("data/invalid_un_op_algebraic.json", "ValueError"),
        ("data/invalid_un_op_list_algebraic.json", "ValueError"),
        ("data/invalid_un_op_nested_list_algebraic.json", "ValueError"),
        ("data/wrong_un_len_algebraic.json", "ValueError"),
    ],
)
def test_init_errors(json_path, expected):
    try:
        JSONParser(json_path).initialize_network()
    except Exception as err:
        result = type(err).__name__

    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, csv_path, tag_name, data_type, expected_path, expected_units",
    [
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "GrossGasProduction",
            "DataFrame",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "ElectricityProductionByGasVolume",
            "DataFrame",
            "data/electrical_efficiency.csv",
            "kilowatt * hour * minute / (feet ** 3)",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "GrossGasProduction",
            "Dict",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "ElectricityProductionByGasVolume",
            "Dict",
            "data/electrical_efficiency.csv",
            "kilowatt * hour * minute / (feet ** 3)",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/array_division.csv",
            "ElectricityProductionByGasVolume",
            "Array",
            "data/electrical_efficiency.csv",
            "kilowatt * hour * minute / (feet ** 3)",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/array_division.csv",
            "ElectricityProductionByGasVolume",
            "List",
            "data/electrical_efficiency.csv",
            "kilowatt * hour * minute / (feet ** 3)",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "GrossGasProduction",
            "Array",
            "ValueError",
            "SCFM",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_array.csv",
            "GrossGasProduction",
            "Array",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_array.csv",
            "GrossGasProduction",
            "List",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_array.csv",
            "GrossGasProduction",
            "Invalid",
            "TypeError",
            "SCFM",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "NoGasPurchases",
            "DataFrame",
            "data/no_gas_bool.csv",
            None,
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "NoGasPurchases",
            "Dict",
            "data/no_gas_bool.csv",
            None,
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/gas_purchases.csv",
            "NoGasPurchases",
            "Array",
            "data/no_gas_bool.csv",
            None,
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/gas_purchases.csv",
            "NoGasPurchases",
            "List",
            "data/no_gas_bool.csv",
            None,
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "ElectricityGeneration_RShift2",
            "DataFrame",
            "data/gen_rshift2.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_RShift2",
            "Array",
            "data/gen_rshift2.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_RShift2",
            "List",
            "data/gen_rshift2.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_LShift1",
            "Dict",
            "data/gen_lshift1.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_LShift1",
            "List",
            "data/gen_lshift1.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_LShift1",
            "Array",
            "data/gen_lshift1.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_LShift1",
            "Invalid",
            "TypeError",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGenDelta",
            "Dict",
            "data/gen_delta.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/sample_data.csv",
            "ElectricityGenNegated",
            "DataFrame",
            "data/gen_negate.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGenNegated",
            "Array",
            "data/gen_negate.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGenNegated",
            "List",
            "data/gen_negate.csv",
            "kWh",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGenNegated",
            "Dict",
            "data/gen_negate.csv",
            "kWh",
        ),
        (
            "data/unit_incompat_algebraic.json",
            "data/sample_array.csv",
            "GrossGasProduction",
            "Array",
            "ValueError",
            None,
        ),
        (
            "data/unit_convert_algebraic.json",
            "data/sample_array.csv",
            "GrossGasProduction",
            "Array",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "data/totalized_warning_algebraic.json",
            "data/sample_array.csv",
            "GrossGasProduction",
            "Array",
            "data/gross_gas.csv",
            "SCFM",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_Plus1.5",
            "Array",
            "data/elec_gen_plus1point5.csv",
            "kilowatt * hour",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_Plus1.5",
            "List",
            "data/elec_gen_plus1point5.csv",
            "kilowatt * hour",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_Plus1.5",
            "Dict",
            "data/elec_gen_plus1point5.csv",
            "kilowatt * hour",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_Plus1.5",
            "DataFrame",
            "data/elec_gen_plus1point5.csv",
            "kilowatt * hour",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_Divide2",
            "Array",
            "data/elec_gen_divide2.csv",
            "kilowatt * hour",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_Divide2",
            "List",
            "data/elec_gen_divide2.csv",
            "kilowatt * hour",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_Divide2",
            "Dict",
            "data/elec_gen_divide2.csv",
            "kilowatt * hour",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_Divide2",
            "DataFrame",
            "data/elec_gen_divide2.csv",
            "kilowatt * hour",
        ),
        (
            "../data/wrrf_sample_algebraic.json",
            "data/elec_gen.csv",
            "ElectricityGeneration_LShift1",
            "InvalidUnary",
            "TypeError",
            "kWh",
        ),
    ],
)
def test_calculate_values(
    json_path, csv_path, tag_name, data_type, expected_path, expected_units
):
    parser = JSONParser(json_path)
    if isinstance(expected_path, str) and os.path.isfile(expected_path):
        expected = pd.read_csv(expected_path)
    else:
        expected = expected_path
    try:
        result = parser.initialize_network()
        tag = result.get_tag(tag_name, recurse=True)

        data = pd.read_csv(csv_path)
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
            assert np.allclose(
                np.array(tag.calculate_values(data)),
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
        elif data_type == "InvalidUnary":
            data = "invalid_data_type"  # pass a string
            tag.calculate_values(data)
    except Exception as err:
        result = type(err).__name__
        assert result == expected

    if not (isinstance(expected, str) and expected == "ValueError"):
        if expected_units is not None:
            assert parse_units(expected_units) == tag.units
        else:
            assert tag.units is None


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "constant0, constant1, expected",
    [
        (operations.Constant(-1), operations.Constant(0), True),
        (operations.Constant(0), operations.Constant(-1), False),
        (operations.Constant(100.1), operations.Constant(100.1), False),
        (operations.Constant(1.0), operations.Constant(1), False),
        (operations.Constant(1), operations.Constant(1.0), True),
        (operations.Constant(1, parent_id="ABC"), operations.Constant(1), False),
        (operations.Constant(1), operations.Constant(1, parent_id="XYZ"), True),
        (
            operations.Constant(1, parent_id="ABC"),
            operations.Constant(1, parent_id="XYZ"),
            True,
        ),
        (
            operations.Constant(1, parent_id="ABC"),
            operations.Constant(1, parent_id="ABC"),
            False,
        ),
    ],
)
def test_constant_less_than(constant0, constant1, expected):
    assert (constant0 < constant1) == expected
