import os
import json
import pandas as pd

class Logbook:
    """
    Attributes
    ----------
    entries : dict
        Dictionary of the form { `datetime` : `str` }
        
    """
    def __init__():
        self.entries = {}

    def add_entry(self, timestamp, entry):
        """Modifies `self.entries` to add the desired `entry` text under `timestamp` key
        
        Parameters
        ----------
        timestamp : datetime.datetime
            The timestamp for the entry to be removed

        entry : str
            Plaintext logbook entry
        """
        self.entries[timestamp] = entry

    def remove_entry(self, timestamp):
        """Modifies `self.entries`
        
        Parameters
        ----------
        timestamp : datetime.datetime
            The timestamp for the entry to be removed
        """
        del self.entries[timestamp]

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
            df = pd.read_csv(filepath)
            new_timestamps = df["timestamps"].to_list()
            new_entries = df["entries"].to_list()
        elif file_extension == ".json":
            with open('data.json', 'r') as file:
                data = json.load(file)
            new_timestamps = list(data.keys())
            new_entries = list(data.values())
        else:
            raise ValueError("Invalid file extension {}. Only CSV and JSON are supported".format(file_extension))

        for timestamp, entry in zip(new_timestamps, new_entries):
            self.entries[timestamp] = entry

    def query(
        self, 
        start_dt, 
        end_dt=None,
        keyword=None
    ):
        """

        Parameters
        ----------
        start_dt : datetime.datetime

        end_dt : datetime.datetime
            Final datetime to include in the timestamps of log entries to return.
            None by default, meaning that all entries after `start_dt` will be returned

        keyword : str
            Keyword to find in the log entry. None by default

        Returns
        -------
        dict
            Dictionary of logbook entries between start_dt and `end_dt`
        """
        valid_entries = {}
        for timestamp in self.entries.keys():
            if timestamp < start_dt:
                continue
            if end_dt is not None:
                if timestamp > end_dt:
                    continue
            if keyword is not None:
                if keyword not in self.entries[timestamp]:
                    continue
            valid_entries[timestamp] = self.entries[timestamp]
        
        return valid_entries
