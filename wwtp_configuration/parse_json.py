import json
import copy
from .tag import TagType, Tag, VirtualTag, CONTENTLESS_TYPES
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
        v_tags = self.config.get("virtual_tags")
        if v_tags:
            for v_tag_id, v_tag_info in v_tags.items():
                v_tag = self.parse_virtual_tag(v_tag_id, v_tag_info, self.network_obj)
                self.network_obj.add_tag(v_tag)

        # TODO: check for unused fields and throw a warning for each
        return self.network_obj

    def merge_network(self, old_network, inplace=False):
        """ Incorporates nodes/connections (i.e. the `new_network`) into a network (i.e. `old_newtwork`)
        modifying it in place and returning the modified network

        Parameters
        ----------
        old_network: str or wwtp_configuration.Network
            JSON file path or Network objet to merge with `self`

        Raises
        ------
        TypeError:
            When user does not provide a valid path or Network object for `old_network`

        Returns
        -------
        wwtp_configuration.node.Network:
            Modified network object
        """
        if isinstance(old_network, str) and old_network.endswith("json"):
            old_network = JSONParser(old_network).initialize_network()
        if not isinstance(old_network, node.Network):
            raise TypeError("Please provide a valid json path or object for network to merge with")
        for node_id in self.config["nodes"]:
            if node_id not in self.config:
                raise NameError("Node " + node_id + " not found in " + self.path)
            # delete existing node before creating the new one if necessary
            elif hasattr(old_network, "nodes") and node_id in old_network.nodes.keys():
                old_network.remove_node(node_id)
            old_network.add_node(self.create_node(node_id))
        for connection_id in self.config["connections"]:
            if connection_id not in self.config:
                raise NameError(
                    "Connection " + connection_id + " not found in " + self.path
                )
            # delete existing connection before creating the new one if necessary
            if hasattr(old_network, "connections") and connection_id in old_network.connections.keys():
                old_network.remove_connection(connection_id)
            old_network.add_connection(self.create_connection(connection_id, old_network))
        if inplace:
            self.network_obj = old_network
        return old_network

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

        min_flow, max_flow, avg_flow = self.parse_min_max_avg(self.config[node_id].get("flowrate"))

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

            efficiency = self.config[node_id].get("efficiency")
            if efficiency:

                def efficiency_curve(arg):
                    # TODO: fix this so that it interpolates between dictionary values
                    if type(efficiency) is dict:
                        return efficiency[arg]
                    else:
                        return float(efficiency)

                node_obj.set_energy_efficiency(efficiency_curve)
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
            min, max, avg = self.parse_min_max_avg(self.config[node_id].get("generation_capacity"))
            node_obj = node.Cogeneration(
                node_id, input_contents, min, max, avg, num_units, tags={}
            )
            efficiency = self.config[node_id].get("efficiency")
            if efficiency:

                def efficiency_curve(arg):
                    # TODO: fix this so that it interpolates between dictionary values
                    if type(efficiency) is dict:
                        return efficiency[arg]
                    else:
                        return float(efficiency)

                node_obj.set_energy_efficiency(efficiency_curve)
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
            node_obj = node.Flaring(
                node_id,
                num_units,
                min_flow,
                max_flow,
                avg_flow,
                tags={},
            )
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
            contents_list = []
            for tag_id, tag_info in tags.items():
                # ensure that the destination ID for Node-associated Tags is null
                tag_info["dest_unit_id"] = None
                tag = self.parse_tag(tag_id, tag_info, node_obj)
                node_obj.add_tag(tag)

                if utils.ContentsType[tag_info["contents"]] not in contents_list:
                    contents_list.append(utils.ContentsType[tag_info["contents"]])

            for contents in contents_list:
                if contents is not None:
                    tags_by_contents = [
                        tag_info for _, tag_info in tags.items()
                        if utils.ContentsType[tag_info["contents"]] == contents
                    ]
                    tag_source_unit_ids = [
                        tag["source_unit_id"] for tag in tags_by_contents
                        if "source_unit_id" in tag.keys()
                    ]
                    if "total" not in tag_source_unit_ids and len(tag_source_unit_ids) > 1:
                        tag_info = tags_by_contents[0]
                        tag_list = [
                            node_obj.get_tag(tag_id, recurse=True)
                            for tag_id, _ in tags.items()
                            if utils.ContentsType[tag_info["contents"]] == contents
                        ]
                        tag_id = "".join([node_id, "Total", tag_info["contents"], tag_info["type"]])
                        v_tag = VirtualTag(tag_id, tag_list, "+")
                        node_obj.add_tag(v_tag)

        v_tags = self.config[node_id].get("virtual_tags")
        if v_tags:
            for v_tag_id, v_tag_info in v_tags.items():
                v_tag = self.parse_virtual_tag(v_tag_id, v_tag_info, node_obj)
                node_obj.add_tag(v_tag)

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

        min_flow, max_flow, avg_flow = self.parse_min_max_avg(self.config[connection_id].get("flowrate"))
        min_pres, max_pres, avg_pres = self.parse_min_max_avg(self.config[connection_id].get("pressure"))
        lower, higher = self.parse_heating_values(self.config[connection_id].get("heating_values"))

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
                diameter=diameter,
                lower_heating_value=lower,
                higher_heating_value=higher,
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

            # TODO: change this to employ new VirtualTag objects
            # create virtual "total" tag if it was missing
            contents_list = connection_obj.contents if (type(connection_obj.contents) is list) else [connection_obj.contents]
            for contents in contents_list:
                if contents is not None:
                    tags_by_contents = [tag_info for _, tag_info in tags.items() if utils.ContentsType[tag_info["contents"]] == contents]
                    tag_source_unit_ids = [tag["source_unit_id"] for tag in tags_by_contents if "source_unit_id" in tag.keys()]
                    tag_dest_unit_ids = [tag["dest_unit_id"] for tag in tags_by_contents if "dest_unit_id" in tag.keys()]
                    if "total" not in tag_source_unit_ids and len(tag_source_unit_ids) > 1:
                        tag_info = tags_by_contents[0]
                        # create a separate virtual total for each destination unit. If none exist then just use total
                        if tag_dest_unit_ids:
                            for id in tag_dest_unit_ids:
                                tag_list = [
                                    connection_obj.tags[tag_id]
                                    for tag_id, _ in tags.items()
                                    if utils.ContentsType[tag_info["contents"]] == contents
                                    and tag_info["dest_unit_id"] == id
                                ]
                                id = "Total" if id == "total" else str(id)
                                tag_id = "".join([
                                    connection_obj.get_source_id(),
                                    "Total",
                                    connection_obj.get_dest_id(),
                                    id,
                                    tag_info["contents"],
                                    tag_info["type"]]
                                )
                                v_tag = VirtualTag(tag_id, tag_list, "+")
                                connection_obj.add_tag(v_tag)
                        else:
                            tag_list = [
                                connection_obj.tags[tag_id]
                                for tag_id, _ in tags.items()
                                if utils.ContentsType[tag_info["contents"]] == contents
                            ]
                            tag_id = "".join([
                                connection_obj.get_source_id(),
                                "Total",
                                connection_obj.get_dest_id(),
                                "Total",
                                tag_info["contents"],
                                tag_info["type"]
                            ])
                            v_tag = VirtualTag(tag_id, tag_list, "+")
                            connection_obj.add_tag(v_tag)
                    if "total" not in tag_dest_unit_ids and len(tag_dest_unit_ids) > 1:
                        tag_info = tags_by_contents[0]
                        # create a separate virtual total for each source unit. If none exist then just use total
                        if tag_source_unit_ids:
                            for id in tag_source_unit_ids:
                                tag_list = [
                                    connection_obj.tags[tag_id]
                                    for tag_id, _ in tags.items()
                                    if utils.ContentsType[tag_info["contents"]] == contents
                                    and tag_info["source_unit_id"] == id
                                ]
                                id = "Total" if id == "total" else str(id)
                                tag_id = "".join([
                                    connection_obj.get_source_id(),
                                    id,
                                    connection_obj.get_dest_id(),
                                    "Total",
                                    tag_info["contents"],
                                    tag_info["type"]
                                ])
                                v_tag = VirtualTag(tag_id, tag_list, "+")
                                connection_obj.add_tag(v_tag)
                        else:
                            tag_list = [
                                connection_obj.tags[tag_id]
                                for tag_id, _ in tags.items()
                                if utils.ContentsType[tag_info["contents"]] == contents
                            ]
                            tag_id = "".join([
                                connection_obj.get_source_id(),
                                "Total",
                                connection_obj.get_dest_id(),
                                "Total", tag_info["contents"],
                                tag_info["type"]
                            ])
                            v_tag = VirtualTag(tag_id, tag_list, "+")
                            connection_obj.add_tag(v_tag)

        v_tags = self.config[connection_id].get("virtual_tags")
        if v_tags:
            for v_tag_id, v_tag_info in v_tags.items():
                v_tag = self.parse_virtual_tag(v_tag_id, v_tag_info, node_obj)
                connection_obj.add_tag(v_tag)

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
    def parse_virtual_tag(tag_id, tag_info, obj):
        """Parse tag ID and dictionary information into VirtualTag object

        Parameters
        ----------
        tag_id : str
            name of the tag

        tag_info : dict
            dictionary of the form {
                'tags': dict of Tag,
                'operations': list of str,
                'type': TagType,
                'contents': str
            }

        obj : Node or Connection
            parent object that contains all constituent tags,
            which is used to gather the tag list for combining data correctly

        Returns
        -------
        VirtualTag
            a Python object with the given ID and the values from `tag_info`
        """
        tag_list = []
        for subtag_id in tag_info["tags"]:
            subtag = obj.get_tag(subtag_id, recurse=True)
            if subtag is None:
                raise ValueError("Invalid Tag id {} in VirtualTag {}".format(subtag_id, tag_id))
            tag_list.append(subtag)

        try:
            tag_type = TagType[tag_info["type"]]
        except KeyError:
            tag_type = None
        try:
            contents_type = utils.ContentsType[tag_info["contents"]]
        except KeyError:
            contents_type = None
        v_tag = VirtualTag(tag_id, tag_list, tag_info["operations"], tag_type, contents_type)
        return v_tag


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
        tag_type = TagType[tag_info["type"]]
        totalized = tag_info.get("totalized", False)
        pint_unit = utils.parse_units(tag_info["units"]) if tag_info["units"] else None
        source_unit_id = tag_info.get("source_unit_id", "total")
        dest_unit_id = tag_info.get("dest_unit_id", "total")
        tag = Tag(
            tag_id,
            pint_unit,
            tag_type,
            source_unit_id,
            dest_unit_id,
            obj.id,
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

        tag_type = TagType[tag_info["type"]]
        if contents is None and tag_type not in CONTENTLESS_TYPES:
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
    def parse_min_max_avg(min_max_avg):
        """Converts a dictionary into a tuple of flow rates

        Parameters
        ----------
        min_max_avg : dict
            dictionary of the form {'min': int, 'max': int, 'avg': int}

        Returns
        -------
        (Quantity, Quantity, Quantity) or (float, float, float)
            (min, max, and average) with the given Pint units as a tuple.
            If no units given, then returns a tuple of floats.
        """
        if min_max_avg is None:
            return (None, None, None)
        else:
            units = min_max_avg.get("units")
            if units:
                return (
                    utils.parse_quantity(min_max_avg.get("min"), units),
                    utils.parse_quantity(min_max_avg.get("max"), units),
                    utils.parse_quantity(min_max_avg.get("avg"), units),
                )
            else:
                return (
                    min_max_avg.get("min"),
                    min_max_avg.get("max"),
                    min_max_avg.get("avg"),
                )

    @staticmethod
    def parse_heating_values(heating_vals):
        """Converts a dictionary into a tuple of flow rates

        Parameters
        ----------
        heating_vals : dict
            dictionary of the form {'lower': float, 'higher': float}

        Returns
        -------
        (Quantity, Quantity) or (float, float)
            (lower, higher) heating values as a tuple, with units applied.
            Given as a float if no units are specified
        """
        if heating_vals is None:
            return (None, None)
        else:
            units = heating_vals.get("units")
            if units:
                return (
                    utils.parse_quantity(heating_vals.get("lower"), units),
                    utils.parse_quantity(heating_vals.get("higher"), units),
                )
            else:
                return (heating_vals.get("lower"), heating_vals.get("higher"))
