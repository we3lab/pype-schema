import json


class JSONParser:
    """A parser to convert a JSON file into a `Network` object

    Parameters
    ----------
    path : str
        path to the JSON file to load

    Attributes
    ----------
    config : dict
        dictionary with the contents the JSON file
    """

    def __init__(self, path):
        f = open(path)
        self.config = json.load(f)
        f.close()

    def create_network(self):
        """Converts a dictionary into a `Network` object

        Returns
        -------
        Network
            a Python object with all the values from the JSON file stored hierarchically
        """
        # for node in nodes:
        # check that node exists in dictionary (NameError)
        # throw TypeError if unsupported type
        # create_node(node)
        # for connection in connections:
        # check that connection exists in dictionary (NameError)
        # throw TypeError if unsupported type
        # create_connection(connection)
        # check for unused fields and throw a warning for each

    def create_node(self, node_id):
        """Converts a dictionary into a `Node` object

        Parameters
        ----------
        node_id : str
            the string id for the `Node`

        Returns
        -------
        Node
            a Python object with all the values from key `node_id`
        """
        # parse JSON values
        # fill in default values for missing fields

    def create_train(train):
        """Converts a dictionary into a `Train` object

        Parameters
        ----------
        train_id : str
            the string id for the `Train`

        Returns
        -------
        Train
            a Python object with all the values from key `train_id`
        """
        # for process in processes:
        # create_process()

    def create_process(process):
        """Converts a dictionary into a `Process` object

        Parameters
        ----------
        process_id : str
            the string id for the `Process`

        Returns
        -------
        Process
            a Python object with all the values from key `process_id`
        """
        # parse JSON values
        # fill in default values for missing fields

    def create_connection(self, connection):
        """Converts a dictionary into a `Connection` object

        Parameters
        ----------
        connection_id : str
            the string id for the `Connection`

        Returns
        -------
        Connection
            a Python object with all the values from key `connection_id`
        """
        # parse JSON values
        # fill in default values for missing fields
