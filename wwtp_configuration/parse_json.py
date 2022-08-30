import json
from . import connection
from . import node
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
        self.network_obj = node.Network(
            "ParentNetwork", None, None, tags={}, nodes={}, connections={}
        )
        f.close()

    def initialize_network(self):
        """Converts a dictionary into a `Network` object

        Returns
        -------
        Network
            a Python object with all the values from the JSON file
            stored hierarchically
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
            self.network_obj.add_connection(
                self.create_connection(connection_id, self.network_obj)
            )

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
        (input_contents, output_contents) = self.parse_contents(node_id)
        elevation = utils.parse_quantity(
            self.config[node_id].get("elevation (meters)"), "m"
        )
        num_units = self.config[node_id].get("num_units")
        volume = utils.parse_quantity(
            self.config[node_id].get("volume (cubic meters)"), "m3"
        )

        min, max, avg = self.parse_flow_or_gen_capacity(
            self.config[node_id].get("flowrate (MGD)")
        )
        min_flow = utils.parse_quantity(min, "MGD")
        max_flow = utils.parse_quantity(max, "MGD")
        avg_flow = utils.parse_quantity(avg, "MGD")

        # create correct type of node class
        if self.config[node_id]["type"] == "Network":
            node_obj = node.Network(
                node_id,
                input_contents,
                output_contents,
                tags={},
                nodes={},
                connections={},
            )

            for new_node in self.config[node_id]["nodes"]:
                node_obj.add_node(self.create_node(new_node))
            for new_connection in self.config[node_id]["connections"]:
                node_obj.add_connection(
                    self.create_connection(new_connection, node_obj)
                )
        elif self.config[node_id]["type"] == "Battery":
            capacity = utils.parse_quantity(
                self.config[node_id].get("capacity (kWh)"), "kwh"
            )
            discharge_rate = utils.parse_quantity(
                self.config[node_id].get("discharge_rate (kW)"), "kw"
            )
            node_obj = node.Battery(node_id, capacity, discharge_rate, tags={})
        elif self.config[node_id]["type"] == "Facility":
            node_obj = node.Facility(
                node_id,
                input_contents,
                output_contents,
                elevation,
                min_flow,
                max_flow,
                avg_flow,
                tags={},
                nodes={},
                connections={},
            )

            for new_node in self.config[node_id]["nodes"]:
                node_obj.add_node(self.create_node(new_node))
            for new_connection in self.config[node_id]["connections"]:
                node_obj.add_connection(
                    self.create_connection(new_connection, node_obj)
                )
        elif self.config[node_id]["type"] == "Pump":
            pump_type = self.config[node_id].get("pump_type", utils.PumpType.Constant)
            horsepower = utils.parse_quantity(
                self.config[node_id].get("horsepower"), "hp"
            )
            node_obj = node.Pump(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                avg_flow,
                elevation,
                horsepower,
                num_units,
                pump_type=pump_type,
                tags={},
            )
        elif self.config[node_id]["type"] == "Reservoir":
            node_obj = node.Reservoir(
                node_id, input_contents, output_contents, elevation, volume, tags={}
            )
        elif self.config[node_id]["type"] == "Tank":
            node_obj = node.Tank(
                node_id, input_contents, output_contents, elevation, volume, tags={}
            )
        elif self.config[node_id]["type"] == "Aeration":
            node_obj = node.Aeration(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                avg_flow,
                num_units,
                volume,
                tags={},
            )
        elif self.config[node_id]["type"] == "Clarification":
            node_obj = node.Clarification(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                avg_flow,
                num_units,
                volume,
                tags={},
            )
        elif self.config[node_id]["type"] == "Cogeneration":
            min, max, avg = self.parse_flow_or_gen_capacity(
                self.config[node_id].get("generation_capacity (kW)")
            )
            min = utils.parse_quantity(min, "kW")
            max = utils.parse_quantity(max, "kW")
            avg = utils.parse_quantity(avg, "kW")
            node_obj = node.Cogeneration(
                node_id, input_contents, min, max, avg, num_units, tags={}
            )
        elif self.config[node_id]["type"] == "Digestion":
            digester_type = self.config[node_id].get("digester_type")
            node_obj = node.Digestion(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                avg_flow,
                num_units,
                volume,
                utils.DigesterType[digester_type],
                tags={},
            )
        elif self.config[node_id]["type"] == "Filtration":
            node_obj = node.Filtration(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                avg_flow,
                num_units,
                volume,
                tags={},
            )
        elif self.config[node_id]["type"] == "Chlorination":
            node_obj = node.Chlorination(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                avg_flow,
                num_units,
                volume,
                tags={},
            )
        elif self.config[node_id]["type"] == "Flaring":
            node_obj = node.Flaring(node_id, num_units)
        elif self.config[node_id]["type"] == "Thickening":
            node_obj = node.Thickening(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                avg_flow,
                num_units,
                volume,
                tags={},
            )
        elif self.config[node_id]["type"] == "Screening":
            node_obj = node.Screening(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                avg_flow,
                num_units,
                tags={},
            )
        elif self.config[node_id]["type"] == "Conditioning":
            node_obj = node.Conditioning(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                avg_flow,
                num_units,
                tags={},
            )
        else:
            raise TypeError("Unsupported Node type: " + self.config[node_id]["type"])

        tags = self.config[node_id].get("tags")
        if tags:
            for tag_id, tag_info in tags.items():
                tag = self.parse_tag(tag_id, tag_info, node_obj)
                node_obj.add_tag(tag)

        return node_obj

    def create_connection(self, connection_id, node_obj):
        """Converts a dictionary into a `Connection` object

        Parameters
        ----------
        connection_id : str
            the string id for the `Connection`

        node_id : str
            the string id for the `Node` which holds this connection.
            If None the default ID, 'ParentNetwork' is used

        Returns
        -------
        Connection
            a Python object with all the values from key `connection_id`
        """
        contents = self.config[connection_id].get("contents")
        if isinstance(contents, list):
            contents = list(map(lambda con: utils.ContentsType[con], contents))
        else:
            contents = utils.ContentsType[contents]

        bidirectional = self.config[connection_id].get("bidirectional", False)
        source_id = self.config[connection_id].get("source")
        if source_id:
            source = node_obj.get_node(source_id)

        exit_point = self.config[connection_id].get("exit_point")
        if exit_point:
            exit_point = source.get_node(exit_point)

        dest_id = self.config[connection_id].get("destination")
        if dest_id:
            destination = node_obj.get_node(dest_id)

        entry_point = self.config[connection_id].get("entry_point")
        if entry_point:
            entry_point = destination.get_node(entry_point)

        min_flow, max_flow, avg_flow = self.parse_flow_or_gen_capacity(
            self.config[connection_id].get("flowrate (MGD)")
        )
        min_flow = utils.parse_quantity(min_flow, "MGD")
        max_flow = utils.parse_quantity(max_flow, "MGD")
        avg_flow = utils.parse_quantity(avg_flow, "MGD")

        if self.config[connection_id]["type"] == "Pipe":
            diameter = utils.parse_quantity(
                self.config[connection_id].get("diameter (inches)"), "in"
            )
            connection_obj = connection.Pipe(
                connection_id,
                contents,
                source,
                destination,
                min_flow,
                max_flow,
                avg_flow,
                diameter,
                tags={},
                bidirectional=bidirectional,
                exit_point=exit_point,
                entry_point=entry_point,
            )
        elif self.config[connection_id]["type"] == "Wire":
            connection_obj = connection.Wire(
                connection_id,
                source,
                destination,
                tags={},
                bidirectional=bidirectional,
                exit_point=exit_point,
                entry_point=entry_point,
            )
        else:
            raise TypeError(
                "Unsupported Connection type: " + self.config[connection_id]["type"]
            )

        tags = self.config[connection_id].get("tags")
        if tags:
            for tag_id, tag_info in tags.items():
                tag = self.parse_tag(tag_id, tag_info, connection_obj)
                connection_obj.add_tag(tag)

        return connection_obj

    def parse_contents(self, id):
        """Converts a dictionary into a tuple of input and output contents

        Parameters
        ----------
        id : str
            ID of the node to get the contents for

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

        if isinstance(input_contents, list):
            input_contents = list(
                map(lambda contents: utils.ContentsType[contents], input_contents)
            )
        else:
            input_contents = utils.ContentsType[input_contents]

        if isinstance(output_contents, list):
            output_contents = list(
                map(lambda contents: utils.ContentsType[contents], output_contents)
            )
        else:
            output_contents = utils.ContentsType[output_contents]

        return (input_contents, output_contents)

    @staticmethod
    def parse_tag(tag_id, tag_info, obj):
        """Parse tag ID and dictionary of information into Tag object

        Parameters
        ----------
        tag_id : str
            name of the tag

        tag_info : dict
            dictionary of the form {
                'type': TagType,
                'units': str,
                'contents': str,
                'source_unit_id': int or str,
                'dest_unit_id': int or str,
                'totalized': bool
            }

        obj : Node or Connection
            object that this tag is associated with,
            which is used to gather relevant metadata

        Returns
        -------
        Tag
            a Python object with the given ID and the values from `tag_info`
        """
        contents = JSONParser.get_tag_contents(tag_id, tag_info, obj)
        tag_type = utils.TagType[tag_info["type"]]
        totalized = tag_info.get("totalized", False)
        pint_unit = utils.parse_units(tag_info["units"])
        source_unit_id = tag_info.get("source_unit_id", "total")
        dest_unit_id = tag_info.get("dest_unit_id", "total")
        tag = utils.Tag(
            tag_id,
            pint_unit,
            tag_type,
            source_unit_id,
            dest_unit_id,
            totalized=totalized,
            contents=contents,
        )

        return tag

    @staticmethod
    def get_tag_contents(tag_id, tag_info, obj):
        """Parse tag ID and dictionary of information into Tag object

        Parameters
        ----------
        tag_id : str
            name of the tag

        tag_info : dict
            dictionary of the form {
                'type': TagType,
                'units': str,
                'contents': str,
                'source_unit_id': int or str,
                'dest_unit_id': int or str,
                'totalized': bool
            }

        obj : Node or Connection
            object that this tag is associated with,
            which is used to gather relevant metadata

        Returns
        -------
        ContentsType
            the contents of this tag

        Raises
        ------
        ValueError
            If contents are ambiguously defined in JSON.
            E.g., contents not defined in tag and parent object has a list of contents
        """
        try:
            contents = utils.ContentsType[tag_info["contents"]]
        except KeyError:
            contents = None

        if contents is None:
            # will work if obj is of type Connection, otherwise exception occurs
            try:
                contents = obj.contents
            except AttributeError:
                if obj.input_contents == obj.output_contents and not isinstance(
                    obj.input_contents, list
                ):
                    contents = obj.input_contents
                else:
                    raise ValueError("Ambiguous contents definition for tag " + tag_id)

        return contents

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
        if flow_or_gen is None:
            return (None, None, None)
        else:
            return (
                flow_or_gen.get("min"),
                flow_or_gen.get("max"),
                flow_or_gen.get("avg"),
            )
