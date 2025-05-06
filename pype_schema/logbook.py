import os
import json
import pandas as pd
from enum import Enum, auto
from dateutil.parser import parse


class LogCode(Enum):
    """Enum to represent codes associated with logbook entries"""

    Info = auto()
    Warning = auto()
    Error = auto()
    Critical = auto()


class LogEntry:
    """A single `text` log entry in the digital `Logbook` with associated `timestamp`
    and `code` (e.g., info or error)

    Parameters
    ----------
    timestamp : datetime.datetime
        The timestamp for the entry

    text : str
        The text portion of the entry

    code : LogCode
        The code associated with the entry. Default is Info

    Attributes
    ----------
    timestamp : datetime.datetime
        The timestamp for the entry

    text : str
        The text portion of the entry

    code : LogCode
        The code associated with the entry. Default is Info
    """

    def __init__(self, timestamp, text, code=LogCode.Info):
        self.timestamp = timestamp
        self.text = text
        if code is None:
            self.code = LogCode.Info
        else:
            self.code = code

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False
        return (
            self.timestamp == other.timestamp
            and self.text == other.text
            and self.code == other.code
        )

    def __repr__(self):
        return (
            f"<pype_schema.logbook.LogEntry timestamp:{self.timestamp} "
            f"text:{self.text} code:{self.code}>\n"
        )

    def __hash__(self):
        return hash((self.timestamp, self.text, self.code))

    def pprint(self):
        """Pretty print this entry"""
        name = "None" if self.code is None else self.code.name
        print("{\n" + self.timestamp.strftime("%b %d, %Y %H:%M:%S") + ",\n")
        print(name + ",\n" + self.text + ",\n}")


class Logbook:
    """A digital logbook with built-in querying.

    Parameters
    ----------
    entries : dict
        Dictionary of the form { `int` : LogEntry }. Default is an empty dictionary

    Attributes
    ----------
    entries : dict
        Dictionary of the form { `int` : LogEntry }
    """

    def __init__(self, entries=None):
        if entries is None:
            self.entries = {}
        else:
            self.entries = entries

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False
        return self.entries == other.entries

    def __repr__(self):
        return f"<pype_schema.logbook.Logbook entries:{self.entries}>\n"

    def __hash__(self):
        return hash(str(self.entries))

    def next_entry_id(self):
        """Gets the next entry ID by checking the current maximum ID

        Returns
        -------
        int
            ID for the next logbook entry
        """
        if len(self.entries) == 0:
            entry_id = 0
        else:
            entry_id = max(self.entries.keys()) + 1

        return entry_id

    def add_entry(self, timestamp, text, code=LogCode.Info):
        """Modifies `self.entries` to add the desired `text` with associated `timestamp`
        and `code` (e.g., info or error). Entries are saved with an automatically
        incremented counter as their ID.

        Parameters
        ----------
        timestamp : datetime.datetime
            The timestamp for the entry to be added

        text : str
            Plaintext logbook entry

        code : LogCode
            Code associated with the entry. Default is Info
        """
        entry = LogEntry(timestamp, text, code=code)
        self.entries[self.next_entry_id()] = entry

    def remove_entry(self, entry_id):
        """Modifies `self.entries`

        Parameters
        ----------
        timestamp : datetime.datetime
            The timestamp for the entry to be removed
        """
        del self.entries[entry_id]

    def load_entries(self, filepath):
        """Adds all the logbook entries from the given `filepath`.
        Supports both JSON and CSV file formats.

        Parameters
        ----------
        filpath : str
            The path to the file to load logbook entries from

        Raises
        ------
        ValueError
            When file extension is not `json` or `csv`
        """
        filename, file_extension = os.path.splitext(filepath)
        if file_extension == ".csv":
            df = pd.read_csv(filepath, parse_dates=["timestamp"])
            new_timestamps = df["timestamp"].to_list()
            new_entries = df["text"].to_list()
            try:
                new_codes = df["code"].map(lambda x: LogCode[x])
            except KeyError:
                new_codes = [None] * len(new_entries)
            for timestamp, text, code in zip(new_timestamps, new_entries, new_codes):
                entry = LogEntry(timestamp, text, code=code)
                self.entries[self.next_entry_id()] = entry
        elif file_extension == ".json":
            with open(filepath, "r") as file:
                data = json.load(file)
            entry_list = data["entries"]
            for entry in entry_list:
                timestamp = parse(entry["timestamp"], fuzzy=True)
                if entry.get("code") is None:
                    code = None
                else:
                    code = LogCode[entry["code"]]

                entry = LogEntry(timestamp, entry["text"], code=code)
                self.entries[self.next_entry_id()] = entry
        else:
            raise ValueError(
                "Invalid file extension {}. Only CSV and JSON are supported".format(
                    file_extension
                )
            )

    def to_json(self, outpath="", indent=4):
        """Save the current Logbook as a JSON file

        Parameters
        ----------
        outpath : str
            Path where logbook will be saved.
            Default is "", meaning that no file will be written

        indent : int
            number of spaces to indent the JSON file. Default is 4

        Returns
        -------
        dict
            json in dictionary format
        """
        entry_list = []
        for entry in self.entries.values():
            entry_list.append(
                {
                    "timestamp": entry.timestamp.strftime("%b %d, %Y %H:%M:%S"),
                    "text": entry.text,
                    "code": entry.code.name,
                }
            )

        result = {"entries": entry_list}
        if outpath:
            with open(outpath, "w") as file:
                json.dump(result, file, indent=indent)

        return result

    def to_csv(self, outpath=""):
        """Save the current Logbook as a CSV file

        Parameters
        ----------
        outpath : str
            Path where logbook will be saved.
            Default is "", meaning no file will be saved

        Return
        ------
        pandas.DataFrame
            csv in DataFrame format
        """
        entry_dict = {"timestamp": [], "text": [], "code": []}
        for entry in self.entries.values():
            entry_dict["timestamp"].append(
                entry.timestamp.strftime("%b %d, %Y %H:%M:%S")
            )
            entry_dict["text"].append(entry.text)
            entry_dict["code"].append(entry.code.name)

        entry_df = pd.DataFrame(entry_dict)
        if outpath:
            entry_df.to_csv(outpath, index=False)
        return entry_df

    def query(self, start_dt, end_dt=None, keyword=None, code=None):
        """Queries logbook entries based on timestamp, keywords, and code.

        Parameters
        ----------
        start_dt : datetime.datetime
            First datetime to include in the timestamps of log entries to return.

        end_dt : datetime.datetime
            Final datetime to include in the timestamps of log entries to return.
            None by default, meaning that all entries after `start_dt` will be returned

        keyword : str
            Keyword to find in the log entry. None by default

        code : LogCode
            The code associated with desired logbook entries.
            None by default, meaning all codes will be included

        Returns
        -------
        dict
            Dictionary of logbook entries between `start_dt` and `end_dt`
            that contain `keyword` and have a matching `code`
        """
        valid_entries = {}
        for entry_id, entry in self.entries.items():
            if (
                (entry.timestamp >= start_dt)
                and (end_dt is None or entry.timestamp <= end_dt)
                and (keyword is None or keyword in entry.text)
                and (code is None or code == entry.code)
            ):
                valid_entries[entry_id] = entry

        return valid_entries

    def print_query(self, start_dt, end_dt=None, keyword=None, code=None):
        """Queries logbook entries based on timestamp, keywords, and code.
        Pretty prints the queried entries, and then also returns them

        Parameters
        ----------
        start_dt : datetime.datetime
            First datetime to include in the timestamps of log entries to return.

        end_dt : datetime.datetime
            Final datetime to include in the timestamps of log entries to return.
            None by default, meaning that all entries after `start_dt` will be returned

        keyword : str
            Keyword to find in the log entry. None by default

        code : LogCode
            The code associated with desired logbook entries.
            None by default, meaning all codes will be included

        Returns
        -------
        dict
            Dictionary of logbook entries between `start_dt` and `end_dt`
            that contain `keyword` and have a matching `code`
        """
        entries = self.query(start_dt, end_dt, keyword, code)
        for entry in entries.values():
            entry.pprint()

        return entries

    def save_query(self, start_dt, end_dt=None, keyword=None, code=None, outpath=""):
        """Queries logbook entries based on timestamp, keywords, and code.
        Saves the queried entries, and then also returns them

        Parameters
        ----------
        start_dt : datetime.datetime
            First datetime to include in the timestamps of log entries to return.

        end_dt : datetime.datetime
            Final datetime to include in the timestamps of log entries to return.
            None by default, meaning that all entries after `start_dt` will be returned

        keyword : str
            Keyword to find in the log entry. None by default

        code : LogCode
            The code associated with desired logbook entries.
            None by default, meaning all codes will be included

        outpath : str
            Path where logbook will be saved. Supported filetypes are JSON and CSV.
            Default path is "", meaning that no file will be written

        Returns
        -------
        dict
            Dictionary of logbook entries between `start_dt` and `end_dt`
            that contain `keyword` and have a matching `code`
        """
        # check file path and can throw exception before querying for efficiency
        if outpath:
            base, ext = os.path.splitext(outpath)
            if ext not in [".json", ".csv"]:
                raise ValueError("Only `.json` and `.csv` are supported extensions")

        entries = self.query(start_dt, end_dt, keyword, code)
        queried_logbook = Logbook(entries)
        if outpath:
            if ext == ".json":
                queried_logbook.to_json(outpath=outpath)
            else:  # if not JSON must be CSV given check above
                queried_logbook.to_csv(outpath=outpath)

        return entries
