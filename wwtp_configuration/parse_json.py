import json
from . import network
from . import connection
from . import node
from . import process
from . import utils


class JSONParser:
    """A parser to convert a JSON file into a `Network` object

    Parameters
    ----------
    path : str
        path to the JSON file to load

    Attributes
    ----------
    path : str
        path to the JSON file to load

    config : dict
        dictionary with the contents the JSON file

    network_obj : Network
        Python representation of the JSON file
    """

    def __init__(self, path):
        f = open(path)
        self.path = path
        self.config = json.load(f)
        self.network_obj = network.Network()
        f.close()

    def initialize_network(self):
        """Converts a dictionary into a `Network` object

        Returns
        -------
        Network
            a Python object with all the values from the JSON file stored hierarchically
        """
        for node_id in self.config["nodes"]:
            # check that node exists in dictionary (NameError)
            if node_id not in self.config:
                raise NameError("Node " + node_id + " not found in " + self.path)
            self.network_obj.add_node(self.create_node(node_id))
        for connection_id in self.config["connections"]:
            # check that connection exists in dictionary (NameError)
            if connection_id not in self.config:
                raise NameError(
                    "Connection " + connection_id + " not found in " + self.path
                )
            self.network_obj.add_connection(self.create_connection(connection_id))

        # TODO: check for unused fields and throw a warning for each
        return self.network_obj

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
        input_contents, output_contents = self.parse_contents(node_id)
        elevation = self.config[node_id].get("elevation")

        # create correct type of node class
        if self.config[node_id]["type"] == "Facility":
            min, max, avg = self.parse_flow_or_gen_capacity(
                self.config[node_id]["flowrate (MGD)"]
            )
            node_obj = node.Facility(
                node_id,
                utils.ContentsType[input_contents],
                utils.ContentsType[output_contents],
                elevation,
                min,
                max,
                avg,
            )

            for train in self.config[node_id]["trains"]:
                node_obj.add_train(self.create_train(train))
        elif self.config[node_id]["type"] == "Tank":
            volume = self.config[node_id].get("volume")
            node_obj = node.Tank(
                node_id,
                utils.ContentsType[input_contents],
                utils.ContentsType[output_contents],
                elevation,
                volume,
            )
        elif self.config[node_id]["type"] == "Pump":
            min, max, avg = self.parse_flow_or_gen_capacity(
                self.config[node_id]["flowrate (MGD)"]
            )
            pump_type = self.config[node_id].get("pump_type", utils.PumpType.Constant)
            horsepower = self.config[node_id].get("horsepower")
            num_units = self.config[node_id].get("horsepower")
            node_obj = node.Pump(
                node_id,
                utils.ContentsType[input_contents],
                utils.ContentsType[output_contents],
                elevation,
                horsepower,
                num_units,
                min,
                max,
                avg,
                pump_type,
            )
        else:
            raise TypeError("Unsupported Node type: " + self.config[node_id]["type"])

        tags = self.config[node_id].get("tags")
        if tags:
            for tag_id, tag_info in tags.items():
                tag = self.parse_tag(tag_id, tag_info)
                node_obj.add_tag(tag)

        return node_obj

    def create_train(self, train_id):
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
        train_obj = process.Train(train_id)
        for process_id in self.config[train_id]["processes"]:
            if (
                self.config[process_id]["type"] == "Facility"
                or self.config[process_id]["type"] == "Tank"
                or self.config[process_id]["type"] == "Pump"
            ):
                train_obj.add_process(self.create_node(process_id))
            else:
                train_obj.add_process(self.create_process(process_id))

        return train_obj

    def create_process(self, process_id):
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
        input_contents, output_contents = self.parse_contents(process_id)
        num_units = self.config[process_id].get("num_units")
        volume = self.config[process_id].get("volume")
        try:
            min, max, avg = self.parse_flow_or_gen_capacity(
                self.config[process_id]["flowrate (MGD)"]
            )
        except KeyError:
            min, max, avg = (None, None, None)

        # create correct type of process class
        if self.config[process_id]["type"] == "Aeration":
            process_obj = process.Aeration(
                process_id,
                input_contents,
                output_contents,
                min,
                max,
                avg,
                num_units,
                volume,
            )
        elif self.config[process_id]["type"] == "Clarification":
            process_obj = process.Clarification(
                process_id,
                input_contents,
                output_contents,
                min,
                max,
                avg,
                num_units,
                volume,
            )
        elif self.config[process_id]["type"] == "Cogeneration":
            min, max, avg = self.parse_flow_or_gen_capacity(
                self.config[process_id]["generation_capacity (kWh)"]
            )
            process_obj = process.Cogeneration(
                process_id, input_contents, min, max, avg, num_units
            )
        elif self.config[process_id]["type"] == "Digestion":
            digester_type = self.config[process_id].get("digester_type")
            process_obj = process.Digestion(
                process_id,
                input_contents,
                output_contents,
                min,
                max,
                avg,
                num_units,
                volume,
                utils.DigesterType[digester_type],
            )
        elif self.config[process_id]["type"] == "Filtration":
            process_obj = process.Filtration(
                process_id,
                input_contents,
                output_contents,
                min,
                max,
                avg,
                num_units,
                volume,
            )
        elif self.config[process_id]["type"] == "Flaring":
            process_obj = process.Flaring(process_id, input_contents, num_units)
        elif self.config[process_id]["type"] == "Thickening":
            process_obj = process.Thickening(
                process_id,
                input_contents,
                output_contents,
                min,
                max,
                avg,
                num_units,
                volume,
            )
        else:
            raise TypeError(
                "Unsupported Process type: " + self.config[process_id]["type"]
            )

        tags = self.config[process_id].get("tags")
        if tags:
            for tag_id, tag_info in tags.items():
                tag = self.parse_tag(tag_id, tag_info)
                process_obj.add_tag(tag)

        return process_obj

    def create_connection(self, connection_id):
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
        contents = self.config[connection_id].get("contents")
        source_id = self.config[connection_id].get("source")
        if source_id:
            source = self.network_obj.get_node(source_id)

        sink_id = self.config[connection_id].get("sink")
        if sink_id:
            sink = self.network_obj.get_node(sink_id)

        try:
            min_flow, max_flow, avg_flow = self.parse_flow_or_gen_capacity(
                self.config[connection_id]["flowrate (MGD)"]
            )
        except KeyError:
            min_flow, max_flow, avg_flow = (None, None, None)

        if self.config[connection_id]["type"] == "Pipe":
            diameter = self.config[connection_id].get("diameter")
            connection_obj = connection.Pipe(
                connection_id,
                utils.ContentsType[contents],
                source,
                sink,
                min_flow,
                max_flow,
                avg_flow,
                diameter,
            )
        else:
            raise TypeError(
                "Unsupported Connection type: " + self.config[connection_id]["type"]
            )

        return connection_obj

    def parse_contents(self, id):
        """Converts a dictionary into a tuple of input and output contents

        Parameters
        ----------
        id : str
            ID of the process or node to get the contents for

        Returns
        -------
        (str, str)
            (input_contents, output_contents)
        """
        input_contents = self.config[id].get(
            "input_contents", self.config[id].get("contents")
        )
        if input_contents is None:
            raise ValueError(
                "Either contents or input_contents must be defined for " + id
            )
        output_contents = self.config[id].get(
            "output_contents", self.config[id].get("contents")
        )
        if output_contents is None:
            raise ValueError(
                "Either contents or output_contents must be defined for " + id
            )

        return (input_contents, output_contents)

    @staticmethod
    def parse_tag(tag_id, tag_info):
        """Parse tag ID and dictionary of information into Tag object

        Parameters
        ----------
        tag_id : str
            name of the tag

        tag_info : dict
            dictionary of the form {
                'type': TagType,
                'units': str
                'contents': str
                'unit_id': int or str
                'totalized': bool
            }

        Returns
        -------
        Tag
            a Python object with the given ID and the values from `tag_info`
        """
        try:
            contents = utils.ContentsType[tag_info["contents"]]
        except KeyError:
            # TODO: check for contents of process/node and set contents equal to that
            contents = None
        tag_type = utils.TagType[tag_info["type"]]
        totalized = tag_info.get("totalized", False)
        unit_id = tag_info.get("unit_id", "total")
        tag = utils.Tag(
            tag_id,
            tag_info["units"],
            tag_type,
            unit_id,
            totalized=totalized,
            contents=contents,
        )

        return tag

    @staticmethod
    def parse_flow_or_gen_capacity(flow_or_gen):
        """Converts a dictionary into a tuple of flow rates

        Parameters
        ----------
        flowrate : dict
            dictionary of the form {'min': int, 'max': int, 'avg': int}

        Returns
        -------
        (int, int, int)
            min, max, and average flow rate as a tuple
        """
        return (flow_or_gen.get("min"), flow_or_gen.get("max"), flow_or_gen.get("avg"))
