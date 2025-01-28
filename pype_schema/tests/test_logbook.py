import os
import sys
import json
import pint
import pytest
import pandas as pd
from io import StringIO
from datetime import datetime
from pype_schema.units import u
from pype_schema.logbook import Logbook, LogEntry, LogCode

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False

# set default pint registry so that custom units like MGD are understood
pint.set_application_registry(u)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "log_path, expected",
    [
        (
            "data/sample_log.json", 
            Logbook(
                {
                    0: LogEntry(
                        datetime.strptime("2019-11-23 22:00:00", "%Y-%m-%d %H:%M:%S"),
                        "Change of shift. System operating as normal.",
                        LogCode.Info,
                    ),
                    1: LogEntry(
                        datetime.strptime("2019-11-23 11:30:00", "%Y-%m-%d %H:%M:%S"),
                        "Sludge samples taken from primary and secondary clarifiers.",
                        LogCode.Info,
                    ),
                    2: LogEntry(
                        datetime.strptime("2019-11-22 09:00:00", "%Y-%m-%d %H:%M:%S"),
                        "Digester #1 taken offline due to pump failure.",
                        LogCode.Error,
                    ),
                    3: LogEntry(
                        datetime.strptime("2019-11-30 10:00:00", "%Y-%m-%d %H:%M:%S"),
                        "Potential clog in grit chamber sump.",
                        LogCode.Warning
                    ),
                    4: LogEntry(
                        datetime.strptime("2019-11-30 17:00:00", "%Y-%m-%d %H:%M:%S"),
                        "Influent station failure forced facility shutdown.",
                        LogCode.Critical
                    ),
                }
            )
        ),
    ],
)
def test_load_entries(log_path, expected):
    logbook = Logbook()
    logbook.load_entries(log_path)
    assert logbook == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "log_path, timestamp, text, code, expected",
    [
        (
            "data/sample_log.json", 
            datetime.strptime("2019-11-24 22:00:00", "%Y-%m-%d %H:%M:%S"),
            "Change of shift. System operating as normal.",
            LogCode.Info,
            Logbook(
                {
                    0: LogEntry(
                        datetime.strptime("2019-11-23 22:00:00", "%Y-%m-%d %H:%M:%S"),
                        "Change of shift. System operating as normal.",
                        LogCode.Info,
                    ),
                    1: LogEntry(
                        datetime.strptime("2019-11-23 11:30:00", "%Y-%m-%d %H:%M:%S"),
                        "Sludge samples taken from primary and secondary clarifiers.",
                        LogCode.Info,
                    ),
                    2: LogEntry(
                        datetime.strptime("2019-11-22 09:00:00", "%Y-%m-%d %H:%M:%S"),
                        "Digester #1 taken offline due to pump failure.",
                        LogCode.Error,
                    ),
                    3: LogEntry(
                        datetime.strptime("2019-11-30 10:00:00", "%Y-%m-%d %H:%M:%S"),
                        "Potential clog in grit chamber sump.",
                        LogCode.Warning
                    ),
                    4: LogEntry(
                        datetime.strptime("2019-11-30 17:00:00", "%Y-%m-%d %H:%M:%S"),
                        "Influent station failure forced facility shutdown.",
                        LogCode.Critical
                    ),
                    5: LogEntry(
                        datetime.strptime("2019-11-24 22:00:00", "%Y-%m-%d %H:%M:%S"),
                        "Change of shift. System operating as normal.",
                        LogCode.Info,
                    )
                }
            )
        ),
    ],
)
def test_add_entry(log_path, timestamp, text, code, expected):
    logbook = Logbook()
    logbook.load_entries(log_path)
    logbook.add_entry(timestamp, text, code)
    assert logbook == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "log_path, removal_id, expected",
    [
        (
            "data/sample_log.json", 
            0,
            Logbook(
                {
                    1: LogEntry(
                        datetime.strptime("2019-11-23 11:30:00", "%Y-%m-%d %H:%M:%S"),
                        "Sludge samples taken from primary and secondary clarifiers.",
                        LogCode.Info,
                    ),
                    2: LogEntry(
                        datetime.strptime("2019-11-22 09:00:00", "%Y-%m-%d %H:%M:%S"),
                        "Digester #1 taken offline due to pump failure.",
                        LogCode.Error,
                    ),
                    3: LogEntry(
                        datetime.strptime("2019-11-30 10:00:00", "%Y-%m-%d %H:%M:%S"),
                        "Potential clog in grit chamber sump.",
                        LogCode.Warning
                    ),
                    4: LogEntry(
                        datetime.strptime("2019-11-30 17:00:00", "%Y-%m-%d %H:%M:%S"),
                        "Influent station failure forced facility shutdown.",
                        LogCode.Critical
                    ),
                }
            )
        ),
        (
            "data/sample_log.json", 
            3,
            Logbook(
                {
                    0: LogEntry(
                        datetime.strptime("2019-11-23 22:00:00", "%Y-%m-%d %H:%M:%S"),
                        "Change of shift. System operating as normal.",
                        LogCode.Info,
                    ),
                    1: LogEntry(
                        datetime.strptime("2019-11-23 11:30:00", "%Y-%m-%d %H:%M:%S"),
                        "Sludge samples taken from primary and secondary clarifiers.",
                        LogCode.Info,
                    ),
                    2: LogEntry(
                        datetime.strptime("2019-11-22 09:00:00", "%Y-%m-%d %H:%M:%S"),
                        "Digester #1 taken offline due to pump failure.",
                        LogCode.Error,
                    ),
                    4: LogEntry(
                        datetime.strptime("2019-11-30 17:00:00", "%Y-%m-%d %H:%M:%S"),
                        "Influent station failure forced facility shutdown.",
                        LogCode.Critical
                    ),
                }
            )
        ),
    ],
)
def test_remove_entry(log_path, removal_id, expected):
    logbook = Logbook()
    logbook.load_entries(log_path)
    logbook.remove_entry(removal_id)
    assert logbook == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "csv_log_path, outpath, json_log_path", 
    [("data/sample_log.csv", "", "data/output_log.json")],
)
def test_to_json(csv_log_path, outpath, json_log_path):
    logbook = Logbook()
    logbook.load_entries(csv_log_path)
    result = logbook.to_json(outpath)
    with open(json_log_path, "r") as file:
        expected = json.load(file)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_log_path, outpath, csv_log_path", 
    [("data/sample_log.json", "", "data/output_log.csv")],
)
def test_to_csv(json_log_path, outpath, csv_log_path):
    logbook = Logbook()
    logbook.load_entries(json_log_path)
    result = logbook.to_csv(outpath)
    expected = pd.read_csv(csv_log_path)
    pd.testing.assert_frame_equal(result, expected)


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "log_path, start_dt, end_dt, keyword, code, expected",
    [
        (
            "data/sample_log.json", 
            datetime(2000, 1, 1), 
            None, 
            None, 
            None, 
            {
                0: LogEntry(
                    datetime.strptime("2019-11-23 22:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Change of shift. System operating as normal.",
                    LogCode.Info,
                ),
                1: LogEntry(
                    datetime.strptime("2019-11-23 11:30:00", "%Y-%m-%d %H:%M:%S"),
                    "Sludge samples taken from primary and secondary clarifiers.",
                    LogCode.Info,
                ),
                2: LogEntry(
                    datetime.strptime("2019-11-22 09:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Digester #1 taken offline due to pump failure.",
                    LogCode.Error,
                ),
                3: LogEntry(
                    datetime.strptime("2019-11-30 10:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Potential clog in grit chamber sump.",
                    LogCode.Warning
                ),
                4: LogEntry(
                    datetime.strptime("2019-11-30 17:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Influent station failure forced facility shutdown.",
                    LogCode.Critical
                ),
            }
        ),
        (
            "data/sample_log.json", 
            datetime(2000, 1, 1), 
            None, 
            None, 
            LogCode.Info, 
            {
                0: LogEntry(
                    datetime.strptime("2019-11-23 22:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Change of shift. System operating as normal.",
                    LogCode.Info,
                ),
                1: LogEntry(
                    datetime.strptime("2019-11-23 11:30:00", "%Y-%m-%d %H:%M:%S"),
                    "Sludge samples taken from primary and secondary clarifiers.",
                    LogCode.Info,
                ),
            }
        ),
        (
            "data/sample_log.json", 
            datetime(2019, 11, 23, 0, 0, 0), 
            datetime(2019, 11, 24, 0, 0, 0), 
            None,
            None, 
            {
                0: LogEntry(
                    datetime.strptime("2019-11-23 22:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Change of shift. System operating as normal.",
                    LogCode.Info,
                ),
                1: LogEntry(
                    datetime.strptime("2019-11-23 11:30:00", "%Y-%m-%d %H:%M:%S"),
                    "Sludge samples taken from primary and secondary clarifiers.",
                    LogCode.Info,
                ),
            }
        ),
        (
            "data/sample_log.json", 
            datetime(2019, 11, 23, 0, 0, 0), 
            datetime(2019, 11, 24, 0, 0, 0), 
            "samples",
            None, 
            {
                1: LogEntry(
                    datetime.strptime("2019-11-23 11:30:00", "%Y-%m-%d %H:%M:%S"),
                    "Sludge samples taken from primary and secondary clarifiers.",
                    LogCode.Info,
                ),
            }
        ),
        (
            "data/sample_log.json", 
            datetime(2019, 11, 23, 0, 0, 0), 
            datetime(2019, 11, 24, 0, 0, 0), 
            ".",
            LogCode.Info, 
            {
                0: LogEntry(
                    datetime.strptime("2019-11-23 22:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Change of shift. System operating as normal.",
                    LogCode.Info,
                ),
                1: LogEntry(
                    datetime.strptime("2019-11-23 11:30:00", "%Y-%m-%d %H:%M:%S"),
                    "Sludge samples taken from primary and secondary clarifiers.",
                    LogCode.Info,
                ),
            }
        ),
        (
            "data/sample_log.json", 
            datetime(2000, 1, 1), 
            None,
            "shift", 
            LogCode.Info, 
            {
                0: LogEntry(
                    datetime.strptime("2019-11-23 22:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Change of shift. System operating as normal.",
                    LogCode.Info,
                ),
            }
        ),
        (
            "data/sample_log.json", 
            datetime(2000, 1, 1), 
            datetime(2019, 11, 23, 0, 0), 
            None, 
            None, 
            {
                2: LogEntry(
                    datetime.strptime("2019-11-22 09:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Digester #1 taken offline due to pump failure.",
                    LogCode.Error,
                ),
            }
        ),
    ],
)
def test_query(log_path, start_dt, end_dt, keyword, code, expected):
    logbook = Logbook()
    logbook.load_entries(log_path)
    result = logbook.query(start_dt, end_dt, keyword, code)
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "log_path, start_dt, end_dt, keyword, code, expected",
    [
        (
            "data/sample_log.json", 
            datetime(2000, 1, 1), 
            None, 
            None, 
            None, 
            "{\nNov 23, 2019 22:00:00,\n\nInfo,\nChange of shift. System operating as normal.,\n}"
            "\n{\nNov 23, 2019 11:30:00,\n\nInfo,\nSludge samples taken from primary and secondary clarifiers.,\n}"
            "\n{\nNov 22, 2019 09:00:00,\n\nError,\nDigester #1 taken offline due to pump failure.,\n}"
            "\n{\nNov 30, 2019 10:00:00,\n\nWarning,\nPotential clog in grit chamber sump.,\n}"
            "\n{\nNov 30, 2019 17:00:00,\n\nCritical,\nInfluent station failure forced facility shutdown.,\n}\n"
        ),
    ],
)
def test_print_query(log_path, start_dt, end_dt, keyword, code, expected):
    logbook = Logbook()
    logbook.load_entries(log_path)
    # from https://stackoverflow.com/questions/5136611/capture-stdout-from-a-script
    backup = sys.stdout
    sys.stdout = StringIO()
    logbook.print_query(start_dt, end_dt, keyword, code)
    result = sys.stdout.getvalue()
    sys.stdout.close()
    sys.stdout = backup
    assert result == expected


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "log_path, start_dt, end_dt, keyword, code, outpath, expected",
    [
        (
            "data/sample_log.json", 
            datetime(2000, 1, 1), 
            None, 
            None, 
            None,
            "data/output_log.csv",
            {
                0: LogEntry(
                    datetime.strptime("2019-11-23 22:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Change of shift. System operating as normal.",
                    LogCode.Info,
                ),
                1: LogEntry(
                    datetime.strptime("2019-11-23 11:30:00", "%Y-%m-%d %H:%M:%S"),
                    "Sludge samples taken from primary and secondary clarifiers.",
                    LogCode.Info,
                ),
                2: LogEntry(
                    datetime.strptime("2019-11-22 09:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Digester #1 taken offline due to pump failure.",
                    LogCode.Error,
                ),
                3: LogEntry(
                    datetime.strptime("2019-11-30 10:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Potential clog in grit chamber sump.",
                    LogCode.Warning
                ),
                4: LogEntry(
                    datetime.strptime("2019-11-30 17:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Influent station failure forced facility shutdown.",
                    LogCode.Critical
                ),
            }
        ),
        (
            "data/sample_log.json", 
            datetime(2000, 1, 1), 
            None, 
            None, 
            None,
            "data/output_log.json",
            {
                0: LogEntry(
                    datetime.strptime("2019-11-23 22:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Change of shift. System operating as normal.",
                    LogCode.Info,
                ),
                1: LogEntry(
                    datetime.strptime("2019-11-23 11:30:00", "%Y-%m-%d %H:%M:%S"),
                    "Sludge samples taken from primary and secondary clarifiers.",
                    LogCode.Info,
                ),
                2: LogEntry(
                    datetime.strptime("2019-11-22 09:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Digester #1 taken offline due to pump failure.",
                    LogCode.Error,
                ),
                3: LogEntry(
                    datetime.strptime("2019-11-30 10:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Potential clog in grit chamber sump.",
                    LogCode.Warning
                ),
                4: LogEntry(
                    datetime.strptime("2019-11-30 17:00:00", "%Y-%m-%d %H:%M:%S"),
                    "Influent station failure forced facility shutdown.",
                    LogCode.Critical
                ),
            }
        ),
    ],
)
def test_save_query(log_path, start_dt, end_dt, keyword, code, outpath, expected):
    logbook = Logbook()
    logbook.load_entries(log_path)
    result = logbook.save_query(start_dt, end_dt, keyword, code, outpath=outpath)
    assert result == expected