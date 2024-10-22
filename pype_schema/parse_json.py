import json
import pint
import copy
import warnings
from collections import defaultdict
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

    def initialize_network(self, verbose=False):
        """Converts a dictionary into a `Network` object

        Parameters
        ----------
        verbose : bool
            If `True` will print informative statements while initializing the network

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
            if verbose:
                print(f"Initializing network, adding node {node_id}...")
            self.network_obj.add_node(self.create_node(node_id))
        for connection_id in self.config["connections"]:
            if verbose:
                print(f"Initializing network, adding connection {connection_id}...")
            # check that connection exists in dictionary (NameError)
            if connection_id not in self.config:
                raise NameError(f"Connection {connection_id} not found in {self.path}")
            self.network_obj.add_connection(
                self.create_connection(connection_id, self.network_obj)
            )
        # Add all virtual tags
        self.add_virtual_tags(verbose=verbose)
        # TODO: check for unused fields and throw a warning for each
        return self.network_obj

    def collect_virtual_tags(self, config, obj_id=None, virtual_tags=None):
        """Recursively collects all virtual tags in a network's dictionary
        representation (i.e. config)

        Parameters
        ----------
        config : dict
            Dictionary representation of the network

        obj_id : str
            Optional "id" of config whose virtual tags are being collected
            (if `None` will use "ParentNetwork")

        virtual_tags : dict
            dictionary to store virtual tags in

        Returns
        -------
        dict
            dictionary of all VirtualTag in network
        """
        if virtual_tags is None:
            virtual_tags = {}
        obj_id = "ParentNetwork" if obj_id is None else obj_id
        v_tags = config.get("virtual_tags")
        if v_tags:
            # Make sure obj_id is specified for all virtual tags as `parent_id`
            for v_tag in v_tags.values():
                v_tag["parent_id"] = obj_id
            virtual_tags.update(v_tags)
        for key, value in config.items():
            # Parse any subdictionaries in the JSON
            # (e.g. a network within a network or a node/connection within a network)
            if key not in ["tags", "virtual_tags"] and isinstance(value, dict):
                self.collect_virtual_tags(value, obj_id=key, virtual_tags=virtual_tags)
        return virtual_tags

    def add_virtual_tags(self, verbose=False):
        """Adds all virtual tags in an object
        NOTE: assumes the objects tags have already been added

        Parameters
        ----------
        obj : Node or Connection
            object to add virtual tags to

        verbose : bool
            If `True` will print informative statements while adding virtual tags.
            Default is `False`
        """
        config_v_tags = self.collect_virtual_tags(self.config)
        network_v_tags = {}
        if config_v_tags:
            # Create a queue of virtual tags to add
            v_tag_queue = [
                (v_tag_id, v_tag_info)
                for v_tag_id, v_tag_info in config_v_tags.copy().items()
            ]
            processed = []
            while v_tag_queue:
                v_tag_id, v_tag_info = v_tag_queue.pop(0)
                # Try parsing the virtual tag
                try:
                    if verbose:
                        print(f"Parsing virtual tag {v_tag_id}...")
                    obj_id = v_tag_info.get("parent_id")
                    obj = (
                        self.network_obj
                        if obj_id == "ParentNetwork"
                        else self.network_obj.get_node_or_connection(
                            obj_id, recurse=True
                        )
                    )
                    v_tag = self.parse_virtual_tag(
                        v_tag_id, v_tag_info, obj, parent_network=self.network_obj
                    )
                    if verbose:
                        print(
                            "Initializing network, adding virtual "
                            "tag {} to {}...".format(v_tag_id, obj.id)
                        )
                    obj.add_tag(v_tag)
                # If there is a Key error, it may be because a virtual tag
                # is pointing to another virtual tag that hasn't been added yet.
                except KeyError as ex:
                    for tag_pointer in v_tag_info["tags"]:
                        # Check if the tag being pointed to is in the already
                        # initialized tags or the network's set of virtual tags
                        if tag_pointer not in config_v_tags and tag_pointer not in [
                            tag.id
                            for tag in self.network_obj.get_all_tags(recurse=True)
                        ]:
                            raise KeyError(
                                f"Invalid Tag id {tag_pointer} in VirtualTag {v_tag_id}"
                            )
                    # Since the tag was not in the network
                    # if it was processed then there was an error during the processing
                    # so we want to raise an exception
                    if v_tag_id not in processed:
                        v_tag_queue.append((v_tag_id, v_tag_info))
                        processed.append(v_tag_id)
                    else:
                        raise ex
        for v_tag in network_v_tags.values():
            obj = self.network_obj.get_node_or_connection(v_tag.parent_id)
            obj.add_tag(v_tag)

    def merge_network(self, old_network, inplace=False):
        """Incorporates nodes/connections (i.e. the `new_network`) into a network
        (i.e. `old_newtwork`) modifying it in place and returning the modified network

        Parameters
        ----------
        old_network: str or pype_schema.Network
            JSON file path or Network objet to merge with `self`

        Raises
        ------
        TypeError:
            When user does not provide a valid path or Network object for `old_network`

        Returns
        -------
        pype_schema.node.Network:
            Modified network object
        """
        if isinstance(old_network, str) and old_network.endswith("json"):
            old_network = JSONParser(old_network).initialize_network()
        if not isinstance(old_network, node.Network):
            raise TypeError(
                "Please provide a valid json path or object for network to merge with"
            )
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
            if (
                hasattr(old_network, "connections")
                and connection_id in old_network.connections.keys()
            ):
                old_network.remove_connection(connection_id)
            old_network.add_connection(
                self.create_connection(connection_id, old_network)
            )
        if inplace:
            self.network_obj = old_network
        return old_network

    @staticmethod
    def prefix_children(target_node, prefix):
        """Renames the children nodes and connections of the `target_node` by
        prepending their ID with `prefix`.

        Parameters
        ----------
        target_node : node.Network
            Network object to rename the children of with a `prefix`

        prefix : str
            String to prepend to the existing node and connection objects

        Returns
        -------
        node.Network
            New network object with
        """
        new_network = copy.deepcopy(target_node)
        for node_obj in new_network.get_all_nodes(recurse=False):
            new_network.remove_node(node_obj.id)
            node_obj.id = prefix + "-" + node_obj.id
            node_obj = JSONParser.prefix_children(node_obj, prefix)
            new_network.add_node(node_obj)
        for conn_obj in new_network.get_all_connections(recurse=False):
            new_network.remove_connection(conn_obj.id)
            conn_obj.id = prefix + "-" + conn_obj.id
            new_network.add_connection(conn_obj)
        return new_network

    def extend_node(
        self,
        new_network,
        target_node_id,
        connections_path,
        inplace=False,
        verbose=False,
    ):
        """
        Incoporates subnetwork (i.e. the `new_network`) into a node
        in a existing network (i.e. the `old_network`)
        modifying it in place and returning the modified network

        Parameters
        ----------
        new_network : str or pype_schema.Network
            JSON file path or Network objet to merge with `self`

        target_node_id : str
            ID of the node to expend, must be in the old_network

        connections_path : str
            JSON file path to the connections connecting `new_network` to `old_network`.

        inplace : bool
            Whether to modify `self` in place or leave original object unmodified.
            False by default

        verbose : bool
            Whether to print informative messages for debugging. Default is False

        Raises
        ------
        TypeError
            When user does not provide a valid path or Network object
            for `old_network` or `new_network`

        KeyError
            When `target_node_id` is not in the `old_network` or
            any node in `connections_path` is not in the `new_network` or `old_network`

        Returns
        -------
        pype_schema.node.Network:
            Modified network object
        """
        if isinstance(new_network, str) and new_network.endswith("json"):
            new_network = JSONParser(new_network).initialize_network()
        if not isinstance(new_network, node.Network):
            raise TypeError(
                "Please provide a valid json path or object for network to extend with"
            )
        if verbose:
            print(f"[*] Merging {new_network.id} into {self.network_obj.id}")
        modified_network = copy.deepcopy(self.network_obj)
        # remove the node and connections that contains the node
        modified_network.remove_node(target_node_id, recurse=True)
        if verbose:
            print("Removed node:", target_node_id)
        for connection_obj in self.network_obj.get_all_connections(recurse=True):
            entry_point_id = (
                None
                if connection_obj.entry_point is None
                else connection_obj.entry_point.id
            )
            exit_point_id = (
                None
                if connection_obj.exit_point is None
                else connection_obj.exit_point.id
            )
            if (
                target_node_id == connection_obj.source.id
                or target_node_id == connection_obj.destination.id
                or target_node_id == entry_point_id
                or target_node_id == exit_point_id
            ):
                modified_network.remove_connection(connection_obj.id, recurse=True)
                if verbose:
                    print("Removed connection:", connection_obj.id)
        # get the parent of the target node so we are at the correct level of network
        parent_obj_id = self.network_obj.get_parent(
            self.network_obj.get_node(target_node_id, recurse=True)
        ).id
        if parent_obj_id == "ParentNetwork":
            parent_network = modified_network
        else:
            parent_network = modified_network.get_node(parent_obj_id, recurse=True)
        # get just the new target node if it is not the entirety of the new network
        try:
            new_target_node = new_network.get_node(target_node_id, recurse=True)
        except KeyError:
            new_target_node = new_network
        # modify names of the child nodes and connections to avoid namespace collisions
        new_target_node = self.prefix_children(new_target_node, target_node_id)
        for node_obj in new_target_node.nodes.values():
            parent_network.add_node(node_obj)
            if verbose:
                print("Added node:", node_obj.id)
        for connection_obj in new_target_node.connections.values():
            parent_network.add_connection(connection_obj)
            if verbose:
                print("Added connection:", connection_obj.id)
        with open(connections_path, "r") as f:
            config = json.load(f)
            # update the config dictionary
            for connection_id in config["connections"]:
                conn_dict = config[connection_id]
                parent_id = conn_dict.get("parent_id")
                # add to ParentNetwork if no parent_id
                if parent_id is None or parent_id == "ParentNetwork":
                    self.config["connections"].append(
                        f"{target_node_id}-{connection_id}"
                    )
                else:
                    self.config[parent_id]["connections"].append(
                        f"{target_node_id}-{connection_id}"
                    )
            new_network_node_ids = [
                node_obj.id for node_obj in new_network.get_all_nodes(recurse=True)
            ]
            # create the Connection object
            for k, v in list(config.items()):
                if k == "connections":
                    continue
                for field in ["source", "exit_point", "destination", "entry_point"]:
                    if (
                        v.get(field) in new_network_node_ids
                        and v[field] != target_node_id
                    ):
                        v[field] = f"{target_node_id}-{v[field]}"
                self.config[f"{target_node_id}-{k}"] = v
                if verbose:
                    print("Added connection:", f"{target_node_id}-{k}")
            for connection_id in config["connections"]:
                # check that connection exists in dictionary (KeyError)
                if connection_id not in config.keys():
                    raise KeyError(
                        f"Connection {connection_id} not found in {connections_path}"
                    )
                parent_id = config[connection_id].get("parent_id")
                if parent_id is None or parent_id == "ParentNetwork":
                    parent_obj = modified_network
                else:
                    parent_obj = modified_network.get_node(parent_id, recurse=True)
                parent_obj.add_connection(
                    self.create_connection(
                        f"{target_node_id}-{connection_id}", parent_obj, verbose=verbose
                    )
                )
                if verbose:
                    print("Added connection:", f"{target_node_id}-{connection_id}")
        if inplace:
            self.network_obj = modified_network
            if verbose:
                print(
                    f"Replaced the network {self.network_obj.id} by extending "
                    f"{target_node_id} with the new network in place"
                )
        return modified_network

    def create_node(self, node_id, verbose=False):
        """Converts a dictionary into a `Node` object

        Parameters
        ----------
        node_id : str
            the string id for the `Node`

        verbose : bool
            Whether to print informative messages for debugging. Default is False

        Returns
        -------
        Node
            a Python object with all the values from key `node_id`
        """
        if verbose:
            print("Creating node:", node_id)
        (input_contents, output_contents) = self.parse_contents(node_id)
        elevation = self.parse_unit_val_dict(self.config[node_id].get("elevation"))
        # strings like `elevation (meters)` and `volume (cubic meters)`
        # are included for backwards compatability
        if elevation is None:
            elevation = utils.parse_quantity(
                self.config[node_id].get("elevation (meters)"), "m"
            )
            warnings.warn(
                "Please switch to new dictionary syntax for elevation with units",
                FutureWarning,
            )
        num_units = self.config[node_id].get("num_units")
        volume = self.parse_unit_val_dict(self.config[node_id].get("volume"))
        if volume is None:
            volume = utils.parse_quantity(
                self.config[node_id].get("volume (cubic meters)"), "m3"
            )
            warnings.warn(
                "Please switch to new dictionary syntax for volume with units",
                FutureWarning,
            )

        flowrate = self.config[node_id].get("flowrate")
        if flowrate is None:
            flowrate = self.config[node_id].get("flow_rate")

        min_flow, max_flow, design_flow = self.parse_min_max_design(flowrate)
        dosing_rate = self.parse_dosing_rate(
            self.config[node_id].get("dosing_rate", defaultdict(float))
        )

        inflow = self.config[node_id].get("inflow")
        outflow = self.config[node_id].get("outflow")

        # create correct type of node class
        if self.config[node_id]["type"] in ["Network", "Facility", "ModularUnit"]:
            num_units = 1 if num_units is None else num_units
            if self.config[node_id]["type"] == "Network":
                node_obj = node.Network(
                    node_id,
                    input_contents,
                    output_contents,
                    tags={},
                    nodes={},
                    connections={},
                    num_units=num_units,
                )
            elif self.config[node_id]["type"] == "Facility":
                node_obj = node.Facility(
                    node_id,
                    input_contents,
                    output_contents,
                    elevation,
                    min_flow,
                    max_flow,
                    design_flow,
                    tags={},
                    nodes={},
                    connections={},
                )
            elif self.config[node_id]["type"] == "ModularUnit":
                node_obj = node.ModularUnit(
                    node_id,
                    input_contents,
                    output_contents,
                    num_units,
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
            energy_capacity = self.parse_unit_val_dict(
                self.config[node_id].get("energy_capacity")
            )
            discharge_rate = self.parse_unit_val_dict(
                self.config[node_id].get("discharge_rate")
            )
            charge_rate = self.parse_unit_val_dict(
                self.config[node_id].get("charge_rate")
            )
            if energy_capacity is None:
                energy_capacity = utils.parse_quantity(
                    self.config[node_id].get("capacity (kWh)"), "kwh"
                )
                warnings.warn(
                    "Please switch to new dictionary syntax "
                    + "for energy capacity with units",
                    FutureWarning,
                )
            if discharge_rate is None:
                discharge_rate = utils.parse_quantity(
                    self.config[node_id].get("discharge_rate (kW)"), "kw"
                )
                warnings.warn(
                    "Please switch to new dictionary syntax "
                    + "for discharge rate with units",
                    FutureWarning,
                )
            if charge_rate is None:
                charge_rate = utils.parse_quantity(
                    self.config[node_id].get("charge_rate (kW)"), "kw"
                )
                warnings.warn(
                    "Please switch to new dictionary syntax for charge rate with units",
                    FutureWarning,
                )
            # if either discharge or charge rate are null assume they are the same
            if discharge_rate is None and charge_rate is None:
                warnings.warn(
                    "Battery object {} has no charge or discharge rate defined".format(
                        node_id
                    )
                )
            elif charge_rate is None:
                charge_rate = discharge_rate
            elif discharge_rate is None:
                discharge_rate = charge_rate
            rte = self.config[node_id].get("rte")
            leakage = self.parse_unit_val_dict(self.config[node_id].get("leakage"))
            node_obj = node.Battery(
                node_id,
                energy_capacity,
                charge_rate,
                discharge_rate,
                rte,
                leakage,
                tags={},
            )
        elif self.config[node_id]["type"] == "Pump":
            pump_type = self.config[node_id].get("pump_type")
            if pump_type is None:
                pump_type = utils.PumpType.Constant
            else:
                pump_type = utils.PumpType[pump_type]

            power_rating = self.parse_unit_val_dict(
                self.config[node_id].get("power_rating")
            )
            if power_rating is None:
                power_rating = utils.parse_quantity(
                    self.config[node_id].get("horsepower"), "hp"
                )
                warnings.warn(
                    "Please switch to new dictionary syntax "
                    + "for power rating with units",
                    FutureWarning,
                )
            node_obj = node.Pump(
                node_id,
                input_contents,
                output_contents,
                elevation,
                min_flow,
                max_flow,
                design_flow,
                power_rating,
                num_units,
                pump_type=pump_type,
                tags={},
            )

            efficiency = self.config[node_id].get("efficiency")
            if efficiency is None:
                pump_curve = self.config[node_id].get("pump_curve")
            else:
                pump_curve = efficiency
            if pump_curve:

                def efficiency_curve(arg):
                    # TODO: fix this so that it interpolates between dictionary values
                    if type(pump_curve) is dict:
                        return pump_curve[arg]
                    else:
                        return float(pump_curve)

                node_obj.set_pump_curve(efficiency_curve)
        elif self.config[node_id]["type"] == "Reservoir":
            node_obj = node.Reservoir(
                node_id, input_contents, output_contents, elevation, volume, tags={}
            )
        elif self.config[node_id]["type"] == "Tank":
            node_obj = node.Tank(
                node_id,
                input_contents,
                output_contents,
                elevation,
                volume,
                num_units,
                tags={},
            )
        elif self.config[node_id]["type"] == "Aeration":
            node_obj = node.Aeration(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                design_flow,
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
                design_flow,
                num_units,
                volume,
                tags={},
            )
        elif self.config[node_id]["type"] in ["Cogeneration", "Boiler"]:
            gen_capacity = self.config[node_id].get("generation_capacity")
            if gen_capacity is None:
                self.config[node_id].get("gen_capacity")
            min, max, design = self.parse_min_max_design(gen_capacity)
            if self.config[node_id]["type"] == "Cogeneration":
                node_obj = node.Cogeneration(
                    node_id, input_contents, min, max, design, num_units, tags={}
                )
                electrical_efficiency = self.config[node_id].get(
                    "electrical efficiency"
                )
                if electrical_efficiency is None:
                    electrical_efficiency = self.config[node_id].get(
                        "electrical_efficiency"
                    )
                thermal_efficiency = self.config[node_id].get("thermal efficiency")
                if thermal_efficiency is None:
                    thermal_efficiency = self.config[node_id].get("thermal_efficiency")
            else:
                node_obj = node.Boiler(
                    node_id, input_contents, min, max, design, num_units, tags={}
                )
                electrical_efficiency = None
                thermal_efficiency = self.config[node_id].get("thermal efficiency")

            if electrical_efficiency:

                def efficiency_curve(arg):
                    # TODO: fix this so that it interpolates between dictionary values
                    if type(electrical_efficiency) is dict:
                        return electrical_efficiency[arg]
                    else:
                        return float(electrical_efficiency)

                node_obj.set_electrical_efficiency(efficiency_curve)

            if thermal_efficiency:

                def efficiency_curve(arg):
                    # TODO: fix this so that it interpolates between dictionary values
                    if type(thermal_efficiency) is dict:
                        return thermal_efficiency[arg]
                    else:
                        return float(thermal_efficiency)

                node_obj.set_thermal_efficiency(efficiency_curve)
        elif self.config[node_id]["type"] == "Digestion":
            digester_type = self.config[node_id].get("digester_type")
            node_obj = node.Digestion(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                design_flow,
                num_units,
                volume,
                utils.DigesterType[digester_type],
                tags={},
            )
        elif self.config[node_id]["type"] == "Filtration":
            settling_time = self.parse_unit_val_dict(
                self.config[node_id].get("settling_time", {"value": 0.0})
            )
            node_obj = node.Filtration(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                design_flow,
                num_units,
                volume,
                dosing_rate=dosing_rate,
                settling_time=settling_time,
                tags={},
            )
        elif self.config[node_id]["type"] == "ROMembrane":
            area = self.parse_unit_val_dict(self.config[node_id].get("area"))
            permeability = self.parse_unit_val_dict(
                self.config[node_id].get("permeability")
            )
            selectivity = self.parse_unit_val_dict(
                self.config[node_id].get("selectivity")
            )
            settling_time = self.parse_unit_val_dict(
                self.config[node_id].get("settling_time", {"value": 0.0})
            )
            node_obj = node.ROMembrane(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                design_flow,
                num_units,
                volume,
                area,
                permeability,
                selectivity,
                dosing_rate=dosing_rate,
                settling_time=settling_time,
                tags={},
            )
        elif self.config[node_id]["type"] == "Chlorination":
            residence_time = self.parse_unit_val_dict(
                self.config[node_id].get("residence_time")
            )
            node_obj = node.Chlorination(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                design_flow,
                num_units,
                volume,
                dosing_rate=dosing_rate,
                residence_time=residence_time,
                tags={},
            )
        elif self.config[node_id]["type"] == "Disinfection":
            residence_time = self.parse_unit_val_dict(
                self.config[node_id].get("residence_time")
            )
            node_obj = node.Disinfection(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                design_flow,
                num_units,
                volume,
                dosing_rate=dosing_rate,
                residence_time=residence_time,
                tags={},
            )
        elif self.config[node_id]["type"] == "UVSystem":
            area = self.parse_unit_val_dict(self.config[node_id].get("area"))
            intensity = self.parse_unit_val_dict(self.config[node_id].get("intensity"))
            residence_time = self.parse_unit_val_dict(
                self.config[node_id].get("residence_time")
            )
            node_obj = node.UVSystem(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                design_flow,
                num_units,
                volume,
                residence_time,
                intensity,
                area,
                tags={},
            )
        elif self.config[node_id]["type"] == "Flaring":
            node_obj = node.Flaring(
                node_id,
                num_units,
                min_flow,
                max_flow,
                design_flow,
                tags={},
            )
        elif self.config[node_id]["type"] == "Thickening":
            node_obj = node.Thickening(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                design_flow,
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
                design_flow,
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
                design_flow,
                num_units,
                tags={},
            )
        elif self.config[node_id]["type"] == "Reactor":
            pH = self.config[node_id].get("pH")
            residence_time = self.parse_unit_val_dict(
                self.config[node_id].get("residence_time")
            )
            node_obj = node.Reactor(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                design_flow,
                num_units,
                volume,
                residence_time,
                dosing_rate=dosing_rate,
                pH=pH,
                tags={},
            )
        elif self.config[node_id]["type"] == "StaticMixer":
            pH = self.config[node_id].get("pH")
            residence_time = self.parse_unit_val_dict(
                self.config[node_id].get("residence_time")
            )
            node_obj = node.StaticMixer(
                node_id,
                input_contents,
                output_contents,
                min_flow,
                max_flow,
                design_flow,
                num_units,
                volume,
                residence_time,
                dosing_rate=dosing_rate,
                pH=pH,
                tags={},
            )
        elif self.config[node_id]["type"] == "Joint":
            node_obj = node.Joint(
                node_id,
                input_contents,
                output_contents,
                inflow,
                outflow,
                tags={},
            )
        elif self.config[node_id]["type"] == "Reducer":
            node_obj = node.Reducer(
                node_id,
                input_contents,
                output_contents,
                inflow,
                outflow,
                tags={},
            )
        elif self.config[node_id]["type"] == "Splitter":
            node_obj = node.Splitter(
                node_id,
                input_contents,
                output_contents,
                inflow,
                outflow,
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
                contents_type = tag_info.get("contents")

                if (
                    contents_type is not None
                    and utils.ContentsType[contents_type] not in contents_list
                ):
                    contents_list.append(utils.ContentsType[tag_info["contents"]])

            for contents in contents_list:
                if contents is not None:
                    tags_by_contents = [
                        tag_obj
                        for _, tag_obj in node_obj.tags.items()
                        if tag_obj.contents == contents
                    ]
                    tag_source_unit_ids = [
                        tag.source_unit_id for tag in tags_by_contents
                    ]
                    if (
                        "total" not in tag_source_unit_ids
                        and len(tag_source_unit_ids) > 1
                    ):
                        tag_obj = tags_by_contents[0]
                        tag_id = "_".join(
                            [node_id, tag_obj.contents.name, tag_obj.tag_type.name]
                        )
                        operations = utils.get_tag_sum_lambda_func(tag_source_unit_ids)
                        v_tag = VirtualTag(
                            tag_id, tags_by_contents, operations=operations
                        )
                        node_obj.add_tag(v_tag)
        return node_obj

    def create_connection(self, connection_id, node_obj, verbose=False):
        """Converts a dictionary into a `Connection` object

        Parameters
        ----------
        connection_id : str
            the string id for the `Connection`

        node_id : str
            the string id for the `Node` which holds this connection.
            If None the default ID, 'ParentNetwork' is used

        verbose : bool
            Whether to print informative messages for debugging. Default is False

        Returns
        -------
        Connection
            a Python object with all the values from key `connection_id`
        """
        if verbose:
            print(
                "Creating connection {} in node {}".format(connection_id, node_obj.id)
            )
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

        flowrate = self.config[connection_id].get("flowrate")
        if flowrate is None:
            flowrate = self.config[connection_id].get("flow_rate")

        min_flow, max_flow, design_flow = self.parse_min_max_design(flowrate)
        min_pres, max_pres, design_pres = self.parse_min_max_design(
            self.config[connection_id].get("pressure")
        )
        lower, higher = self.parse_heating_values(
            self.config[connection_id].get("heating_values")
        )

        if self.config[connection_id]["type"] == "Pipe":
            friction = self.config[connection_id].get("friction_coeff")
            diameter = self.parse_unit_val_dict(
                self.config[connection_id].get("diameter")
            )
            if diameter is None:
                diameter = utils.parse_quantity(
                    self.config[connection_id].get("diameter (inches)"), "in"
                )
                warnings.warn(
                    "Please switch to new dictionary syntax for diamter with units",
                    FutureWarning,
                )
            connection_obj = connection.Pipe(
                connection_id,
                contents,
                source,
                destination,
                min_flow,
                max_flow,
                design_flow,
                diameter=diameter,
                friction=friction,
                lower_heating_value=lower,
                higher_heating_value=higher,
                min_pres=min_pres,
                max_pres=max_pres,
                design_pres=design_pres,
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
        elif self.config[connection_id]["type"] == "Delivery":
            connection_obj = connection.Delivery(
                connection_id,
                contents,
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
        exit_point_id = (
            ""
            if connection_obj.get_exit_point() is None
            else "_" + connection_obj.get_exit_point().id
        )
        entry_point_id = (
            ""
            if connection_obj.get_entry_point() is None
            else "_" + connection_obj.get_entry_point().id
        )
        if tags:
            for tag_id, tag_info in tags.items():
                tag = self.parse_tag(tag_id, tag_info, connection_obj)
                connection_obj.add_tag(tag)

            # create virtual "total" tag if it was missing
            contents_list = (
                connection_obj.contents
                if (type(connection_obj.contents) is list)
                else [connection_obj.contents]
            )

            for contents in contents_list:
                if contents is not None:
                    tags_by_contents = [
                        tag_obj
                        for _, tag_obj in connection_obj.tags.items()
                        if tag_obj.contents == contents
                    ]
                    tag_source_unit_ids = [
                        tag.source_unit_id for tag in tags_by_contents
                    ]
                    tag_dest_unit_ids = [tag.dest_unit_id for tag in tags_by_contents]
                    if (
                        "total" not in tag_source_unit_ids
                        and len(tag_source_unit_ids) > 1
                    ):
                        tag_obj = tags_by_contents[0]
                        operations = utils.get_tag_sum_lambda_func(tag_source_unit_ids)
                        # create a separate virtual total for each destination unit.
                        # If none exist then just use total
                        if tag_dest_unit_ids:
                            for id in tag_dest_unit_ids:
                                tag_list = [
                                    connection_obj.tags[tag_obj.id]
                                    for tag_obj in tags_by_contents
                                    if tag_obj.contents == contents
                                    and tag_obj.dest_unit_id == id
                                ]
                                dest_unit_id = "" if id == "total" else "_" + str(id)
                                tag_id = "{}{}_{}{}{}_{}_{}".format(
                                    connection_obj.get_source_id(),
                                    exit_point_id,
                                    connection_obj.get_dest_id(),
                                    entry_point_id,
                                    dest_unit_id,
                                    tag_obj.contents.name,
                                    tag.tag_type.name,
                                )
                                v_tag = VirtualTag(
                                    tag_id,
                                    tag_list,
                                    operations=operations,
                                    units=tag_obj.units,
                                )
                                connection_obj.add_tag(v_tag)

                        else:
                            tag_list = [
                                connection_obj.tags[tag_obj.id]
                                for tag_obj in tags_by_contents
                                if tag_obj.contents == contents
                            ]

                            tag_id = "{}{}_{}{}_{}_{}".format(
                                connection_obj.get_source_id(),
                                exit_point_id,
                                connection_obj.get_dest_id(),
                                entry_point_id,
                                tag_obj.contents.name,
                                tag.tag_type.name,
                            )
                            v_tag = VirtualTag(
                                tag_id,
                                tag_list,
                                operations=operations,
                                units=tag_obj.units,
                            )
                            v_tag = VirtualTag(
                                tag_id,
                                tag_list,
                                operations=operations,
                                units=tag_obj.units,
                            )
                            connection_obj.add_tag(v_tag)
                    if "total" not in tag_dest_unit_ids and len(tag_dest_unit_ids) > 1:
                        tag_obj = tags_by_contents[0]
                        operations = utils.get_tag_sum_lambda_func(tag_dest_unit_ids)
                        # create a separate virtual total for each source unit.
                        # If none exist then just use total
                        if tag_source_unit_ids:
                            for id in tag_source_unit_ids:
                                tag_list = [
                                    connection_obj.tags[tag_obj.id]
                                    for tag_obj in tags_by_contents
                                    if tag_obj.contents == contents
                                    and tag_obj.source_unit_id == id
                                ]
                                source_unit_id = "" if id == "total" else "_" + str(id)
                                tag_id = "{}{}{}_{}{}_{}_{}".format(
                                    connection_obj.get_source_id(),
                                    exit_point_id,
                                    source_unit_id,
                                    connection_obj.get_dest_id(),
                                    entry_point_id,
                                    tag_obj.contents.name,
                                    tag.tag_type.name,
                                )
                                v_tag = VirtualTag(
                                    tag_id,
                                    tag_list,
                                    operations=operations,
                                    units=tag_obj.units,
                                )
                                connection_obj.add_tag(v_tag)
                        else:
                            tag_list = [
                                connection_obj.tags[tag_obj.id]
                                for tag_obj in tags_by_contents
                                if tag_obj.contents == contents
                            ]

                            tag_id = "{}{}_{}{}_{}_{}".format(
                                connection_obj.get_source_id(),
                                exit_point_id,
                                connection_obj.get_dest_id(),
                                entry_point_id,
                                tag_obj.contents.name,
                                tag.tag_type.name,
                            )
                            v_tag = VirtualTag(
                                tag_id,
                                tag_list,
                                operations=operations,
                                units=tag_obj.units,
                            )
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
    def parse_virtual_tag(tag_id, tag_info, obj, parent_network=None):
        """Parse tag ID and dictionary information into VirtualTag object

        Parameters
        ----------
        tag_id : str
            name of the tag

        tag_info : dict
            dictionary of the form {
                ``tags``: `dict` of `Tag`

                ``operations``: `str`

                ``type``: `TagType`

                ``contents``: `str`

            }

        obj : Node or Connection
            parent object that contains all constituent tags,
            which is used to gather the tag list for combining data correctly

        parent_network : None, Network
            Optional network object the tag is a part of
            If `None` will assume `obj` is parent network and all tags are in `obj.tags`

        parent_network : None, Network
            Optional network object the tag is a part of
            If `None` will assume `obj` is the parent network
            and all tags are in `obj.tags`

        Returns
        -------
        VirtualTag
            a Python object with the given ID and the values from `tag_info`
        """
        tag_list = []
        parent_network = obj if parent_network is None else parent_network
        for subtag_id in tag_info["tags"]:
            subtag = parent_network.get_tag(subtag_id, recurse=True)
            if subtag is None:
                raise KeyError(
                    "Could not find Tag id {} in VirtualTag {}".format(
                        subtag_id, tag_id
                    )
                )
            tag_list.append(subtag)
        pint_unit = utils.parse_units(tag_info["units"])
        try:
            tag_type = TagType[tag_info["type"]]
        except KeyError:
            tag_type = None
        try:
            contents_type = utils.ContentsType[tag_info["contents"]]
        except KeyError:
            contents_type = None
        v_tag = VirtualTag(
            tag_id,
            tag_list,
            operations=tag_info.get("operations"),
            tag_type=tag_type,
            contents=contents_type,
            parent_id=tag_info.get("parent_id"),
            units=pint_unit,
        )
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
                ``type``: `TagType`

                ``units``: `str`

                ``contents``: `str`

                ``source_unit_id``: `int` or `str`

                ``dest_unit_id``: `int` or `str`

                ``totalized``: `bool`

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
                ``type``: `TagType`

                ``units``: `str`

                ``contents``: `str`

                ``source_unit_id``: `int` or `str`

                ``dest_unit_id``: `int` or `str`

                ``totalized``: `bool`

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
                if (
                    obj.input_contents == obj.output_contents
                    and len(obj.input_contents) == 1
                ):
                    contents = obj.input_contents[0]
                else:
                    raise ValueError("Ambiguous contents definition for tag " + tag_id)

        return contents

    @staticmethod
    def parse_dosing_rate(dosing_dict):
        """Converts a dictionary into a dictionary of a different format

        Parameters
        ----------
        heating_vals : dict
            dictionary of the form {

                ``DosingType``: {

                    ``rate``: `float`

                    ``units``: `str`
                }

            }

        Returns
        -------
        dict
            Keys are of DosingType or str and values of pint.Quantity or float
            Given as a float if no units are specified
        """
        new_dosing_dict = {}
        for k, v in dosing_dict.items():
            if k not in utils.DosingType.__members__:
                raise ValueError(f"{k} is not a valid dosing type")
            new_v = JSONParser.parse_unit_val_dict(v)
            new_dosing_dict[utils.DosingType[k]] = new_v

        return new_dosing_dict

    @staticmethod
    def dosing_to_dict(dosing_dict):
        """Converts the dosing rate or area dictionary from PyPES to JSON format.

        Parameters
        ----------
        dosing_dict : dict
            dictionary of the form {
                ``DosingTypeA`` : `float` or`pint.Quantity`

                ``DosingTypeB`` : `float` or `pint.Quantity`

            }

        Returns
        -------
        dict
            Dictionary in JSON-readable format. I.e., {
                ``DosingTypeA``: {
                    ``value``: `float`

                    ``units``: `str`

                }

                ``DosingTypeB``: {
                    ``value``: `float`

                    ``units``: `str`

                }

            }
        """
        new_dosing_dict = {}
        for k, v in dosing_dict.items():
            new_v = JSONParser.unit_val_to_dict(v)
            new_dosing_dict[k.name] = new_v

        return new_dosing_dict

    @staticmethod
    def parse_min_max_design(min_max_design):
        """Converts a dictionary into a tuple of flow rates

        Parameters
        ----------
        min_max_design : dict
            dictionary of the form {
                ``min``: `float`

                ``max``: `float`

                ``design``: `float`

                ``units``: `str`

            }

        Returns
        -------
        (pint.Quantity, pint.Quantity, pint.Quantity) or (float, float, float)
            (min, max, and average) with the given Pint units as a tuple.
            If no units given, then returns a tuple of floats.
        """
        if min_max_design is None:
            return (None, None, None)
        else:
            units = min_max_design.get("units")

            # field name was changed from 'avg' to 'design'
            # so this code is included for backwards compatability
            design_val = min_max_design.get("design")
            if design_val is None:
                design_val = min_max_design.get("avg")
            if units:
                return (
                    utils.parse_quantity(min_max_design.get("min"), units),
                    utils.parse_quantity(min_max_design.get("max"), units),
                    utils.parse_quantity(design_val, units),
                )
            else:
                return (
                    min_max_design.get("min"),
                    min_max_design.get("max"),
                    design_val,
                )

    @staticmethod
    def unit_val_to_dict(attribute):
        """Converts the given attribute to dictionary of the form {
                ``value``: ``float``

                ``units``: `str`

            }

        Parameters
        ----------
        attribute : pint.Quantity or float
            Attribute to represent as a dictionary

        Returns
        -------
        dict
            Dictionary with keys ``value`` and ``units``
        """
        if isinstance(attribute, pint.Quantity):
            data_dict = {"value": attribute.magnitude, "units": str(attribute.units)}
        else:
            data_dict = {"value": attribute, "units": None}
        return data_dict

    @staticmethod
    def parse_unit_val_dict(unit_dict):
        """Converts a dictionary into a Pint Quantity

        Parameters
        ----------
        unit_dict : dict
            dictionary of the form {
                ``value``: ``float``

                ``units``: `str`

            }

        Returns
        -------
        pint.Quantity or float
            Dictionary as a Pint Quantity (or float if no units are specified)
        """
        if unit_dict is not None:
            val = unit_dict.get("value")
            units = unit_dict.get("units")
            if units is None:
                return val
            else:
                return utils.parse_quantity(val, units)
        else:
            return None

    @staticmethod
    def parse_heating_values(heating_vals):
        """Converts a dictionary into a tuple of flow rates

        Parameters
        ----------
        heating_vals : dict
            dictionary of the form {
                ``lower``: `float`

                ``higher``: `float`

                ``units``: `str`

            }

        Returns
        -------
        (pint.Quantity, pint.Quantity) or (float, float)
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

    @staticmethod
    def tag_to_dict(tag_obj):
        """Converts a Tag or VirtualTag object to a dictionary that can be
        parsed into JSON format

        Parameters
        ----------
        tag_obj : Tag or VirtualTag
            object to be converted into a dictionary

        Raises
        ------
        TypeError
            If `tag_obj` is not of type Tag or VirtualTag

        Returns
        -------
        dict
            `tag_obj` in dictionary form
        """
        tag_dict = {}
        if isinstance(tag_obj, VirtualTag):
            tag_dict["units"] = "{!s}".format(tag_obj.units)
            tag_dict["tags"] = [tag.id for tag in tag_obj.tags]
            tag_dict["operations"] = tag_obj.operations
        elif isinstance(tag_obj, Tag):
            tag_dict["units"] = "{!s}".format(tag_obj.units)
            tag_dict["source_unit_id"] = tag_obj.source_unit_id
            tag_dict["dest_unit_id"] = tag_obj.dest_unit_id
            tag_dict["totalized"] = tag_obj.totalized
        else:
            raise TypeError("'tag_obj' must be of type Tag or VirtualTag")

        tag_dict["type"] = tag_obj.tag_type.name
        if tag_obj.tag_type not in CONTENTLESS_TYPES:
            tag_dict["contents"] = tag_obj.contents.name

        return tag_dict

    @staticmethod
    def min_max_design_to_dict(obj, attribute):
        """Converts the flow rate tuple of a `Node` or `Connection` into a
        dictionary object

        Parameters
        ----------
        obj : Node or Connection
            object to get `attribute` of and convert it to a dictionary

        attribute : str
            Either "flow_rate", "gen_capacity", or "pressure"

        Returns
        -------
        dict
            flow rate in the form {
                ``min``: `float` or `int`

                ``max``: `float` or `int`

                ``design``: `float` or `int`

                ``units``: `str`

            }
        """
        min_max_design_dict = {"min": None, "max": None, "design": None, "units": None}
        # try/except for backwards compatability with flow_rate and gen_capacity tuples
        try:
            values = getattr(obj, attribute)
        except AttributeError:
            if attribute == "flow_rate":
                suffix = "flow"
            elif attribute == "gen_capacity":
                suffix = "gen"
            else:
                suffix = attribute
            values = (
                getattr(obj, "min_" + suffix),
                getattr(obj, "max_" + suffix),
                getattr(obj, "design_" + suffix),
            )
        if values[0] is not None:
            min_max_design_dict["min"] = values[0].magnitude
            min_max_design_dict["units"] = "{!s}".format(values[0].units)

        if values[1] is not None:
            min_max_design_dict["max"] = values[1].magnitude
            min_max_design_dict["units"] = "{!s}".format(values[1].units)

        if values[2] is not None:
            min_max_design_dict["design"] = values[2].magnitude
            min_max_design_dict["units"] = "{!s}".format(values[2].units)

        return min_max_design_dict

    @staticmethod
    def conn_to_dict(conn_obj):
        """Converts a Connection object to a dictionary that can be
        parsed into JSON format

        Parameters
        ----------
        conn_obj : Connection
            object to be converted into a dictionary

        Returns
        -------
        dict
            `conn_obj` in dictionary form
        """
        conn_dict = {}
        print(conn_obj)
        conn_dict["type"] = type(conn_obj).__name__
        conn_dict["source"] = conn_obj.source.id
        conn_dict["destination"] = conn_obj.destination.id
        conn_dict["contents"] = conn_obj.contents.name
        conn_dict["bidirectional"] = conn_obj.bidirectional

        if conn_obj.exit_point is not None:
            conn_dict["exit_point"] = conn_obj.exit_point.id

        if conn_obj.entry_point is not None:
            conn_dict["entry_point"] = conn_obj.entry_point.id

        if isinstance(conn_obj, connection.Pipe):
            conn_dict["flowrate"] = JSONParser.min_max_design_to_dict(
                conn_obj, "flow_rate"
            )
            conn_dict["pressure"] = JSONParser.min_max_design_to_dict(
                conn_obj, "pressure"
            )

            heat_dict = {"lower": None, "higher": None, "units": "BTU/scf"}
            if conn_obj.heating_values[0] is not None:
                heat_dict["lower"] = conn_obj.heating_values[0].magnitude
                heat_dict["units"] = "{!s}".format(conn_obj.heating_values[0].units)

            if conn_obj.heating_values[1] is not None:
                heat_dict["higher"] = conn_obj.heating_values[1].magnitude
                heat_dict["units"] = "{!s}".format(conn_obj.heating_values[1].units)

            conn_dict["heating_values"] = heat_dict

            if conn_obj.diameter is not None:
                conn_dict["diameter"] = JSONParser.unit_val_to_dict(conn_obj.diameter)

            if conn_obj.friction_coeff is not None:
                conn_dict["friction_coeff"] = conn_obj.friction_coeff

        tag_dict = {}
        v_tag_dict = {}
        for tag_id, tag_obj in conn_obj.tags.items():
            if isinstance(tag_obj, Tag):
                tag_dict[tag_id] = JSONParser.tag_to_dict(tag_obj)
            elif isinstance(tag_obj, VirtualTag):
                v_tag_dict[tag_id] = JSONParser.tag_to_dict(tag_obj)

        conn_dict["tags"] = tag_dict
        conn_dict["virtual_tags"] = v_tag_dict

        return conn_dict

    @staticmethod
    def node_to_dict(node_obj):
        """Converts a Node object to a dictionary that can be
        parsed into JSON format

        Parameters
        ----------
        node_obj : Node
            object to be converted into a dictionary

        Raises
        ------
        TypeError
            if `node_obj` is not a subclass of `Node`

        Returns
        -------
        dict
            `node_obj` in dictionary form
        """
        node_dict = {}

        node_dict["type"] = type(node_obj).__name__
        if not isinstance(node_obj, node.Flaring):
            node_dict["input_contents"] = [
                contents.name for contents in node_obj.input_contents
            ]
            node_dict["output_contents"] = [
                contents.name for contents in node_obj.output_contents
            ]
        else:
            node_dict["contents"] = [
                contents.name for contents in node_obj.input_contents
            ]

        tag_dict = {}
        v_tag_dict = {}
        for tag_id, tag_obj in node_obj.tags.items():
            if isinstance(tag_obj, Tag):
                tag_dict[tag_id] = JSONParser.tag_to_dict(tag_obj)
            elif isinstance(tag_obj, VirtualTag):
                v_tag_dict[tag_id] = JSONParser.tag_to_dict(tag_obj)

        node_dict["tags"] = tag_dict
        node_dict["virtual_tags"] = v_tag_dict

        if isinstance(node_obj, node.Reservoir):
            if node_obj.elevation is not None:
                node_dict["elevation"] = JSONParser.unit_val_to_dict(node_obj.elevation)

            if node_obj.volume is not None:
                node_dict["volume (cubic meters)"] = node_obj.volume.magnitude
        elif isinstance(node_obj, node.Tank):
            if node_obj.elevation is not None:
                node_dict["elevation (meters)"] = node_obj.elevation.magnitude

            if node_obj.volume is not None:
                node_dict["volume (cubic meters)"] = node_obj.volume.magnitude
            if node_obj.num_units is not None:
                node_dict["num_units"] = node_obj.num_units
        elif isinstance(node_obj, node.Pump):
            if node_obj.elevation is not None:
                node_dict["elevation"] = JSONParser.unit_val_to_dict(node_obj.elevation)

            if node_obj.power_rating is not None:
                node_dict["power_rating"] = JSONParser.unit_val_to_dict(
                    node_obj.power_rating
                )

            if node_obj.pump_type is not None:
                node_dict["pump_type"] = node_obj.pump_type.name

            node_dict["flowrate"] = JSONParser.min_max_design_to_dict(
                node_obj, "flow_rate"
            )
            node_dict["num_units"] = node_obj.num_units
        elif isinstance(node_obj, node.Digestion):
            if node_obj.volume is not None:
                node_dict["volume"] = JSONParser.unit_val_to_dict(node_obj.volume)

            if node_obj.digester_type is not None:
                node_dict["digester_type"] = node_obj.digester_type.name

            node_dict["flowrate"] = JSONParser.min_max_design_to_dict(
                node_obj, "flow_rate"
            )
            node_dict["num_units"] = node_obj.num_units
        elif isinstance(node_obj, (node.Cogeneration, node.Boiler)):
            node_dict["generation_capacity"] = JSONParser.min_max_design_to_dict(
                node_obj, "gen_capacity"
            )
            node_dict["num_units"] = node_obj.num_units
        elif isinstance(node_obj, node.Disinfection):
            if node_obj.volume is not None:
                node_dict["volume"] = JSONParser.unit_val_to_dict(node_obj.volume)

            node_dict["flowrate"] = JSONParser.min_max_design_to_dict(
                node_obj, "flow_rate"
            )
            node_dict["num_units"] = node_obj.num_units
            node_dict["residence_time"] = JSONParser.unit_val_to_dict(
                node_obj.residence_time
            )
            if isinstance(node_obj, node.UVSystem):
                node_dict["area"] = JSONParser.unit_val_to_dict(
                    node_obj.dosing_area[utils.DosingType["UVLight"]]
                )
                node_dict["intensity"] = JSONParser.unit_val_to_dict(
                    node_obj.dosing_rate[utils.DosingType["UVLight"]]
                )
            else:
                node_dict["dosing_rate"] = JSONParser.dosing_to_dict(
                    node_obj.dosing_rate
                )
        elif isinstance(node_obj, node.Filtration):
            if node_obj.volume is not None:
                node_dict["volume"] = JSONParser.unit_val_to_dict(node_obj.volume)

            node_dict["flowrate"] = JSONParser.min_max_design_to_dict(
                node_obj, "flow_rate"
            )
            node_dict["num_units"] = node_obj.num_units
            node_dict["settling_time"] = JSONParser.unit_val_to_dict(
                node_obj.settling_time
            )
            node_dict["dosing_rate"] = JSONParser.dosing_to_dict(node_obj.dosing_rate)

            if isinstance(node_obj, node.ROMembrane):
                node_dict["area"] = JSONParser.unit_val_to_dict(node_obj.area)
                node_dict["selectivity"] = JSONParser.unit_val_to_dict(
                    node_obj.selectivity
                )
                node_dict["permeability"] = JSONParser.unit_val_to_dict(
                    node_obj.permeability
                )
        elif isinstance(node_obj, (node.Reactor, node.StaticMixer)):
            if node_obj.volume is not None:
                node_dict["volume"] = JSONParser.unit_val_to_dict(node_obj.volume)

            node_dict["flowrate"] = JSONParser.min_max_design_to_dict(
                node_obj, "flow_rate"
            )
            node_dict["num_units"] = node_obj.num_units
            node_dict["residence_time"] = JSONParser.unit_val_to_dict(
                node_obj.residence_time
            )
            node_dict["dosing_rate"] = JSONParser.dosing_to_dict(node_obj.dosing_rate)
            node_dict["pH"] = node_obj.pH
        elif isinstance(node_obj, (node.Thickening, node.Aeration, node.Clarification)):
            if node_obj.volume is not None:
                node_dict["volume"] = JSONParser.unit_val_to_dict(node_obj.volume)

            node_dict["flowrate"] = JSONParser.min_max_design_to_dict(
                node_obj, "flow_rate"
            )
            node_dict["num_units"] = node_obj.num_units
        elif isinstance(node_obj, (node.Screening, node.Conditioning, node.Flaring)):
            node_dict["flowrate"] = JSONParser.min_max_design_to_dict(
                node_obj, "flow_rate"
            )
            node_dict["num_units"] = node_obj.num_units
        elif isinstance(node_obj, node.Battery):
            node_dict["energy_capacity"] = JSONParser.unit_val_to_dict(
                node_obj.energy_capacity
            )
            node_dict["discharge_rate"] = JSONParser.unit_val_to_dict(
                node_obj.discharge_rate
            )
            node_dict["charge_rate"] = JSONParser.unit_val_to_dict(node_obj.charge_rate)
            node_dict["leakage"] = JSONParser.unit_val_to_dict(node_obj.leakage)
            node_dict["rte"] = node_obj.rte
        elif isinstance(node_obj, node.Network):
            node_dict["type"] = type(node_obj).__name__
            node_dict["input_contents"] = [
                contents.name for contents in node_obj.input_contents
            ]
            node_dict["output_contents"] = [
                contents.name for contents in node_obj.output_contents
            ]
            node_dict["nodes"] = []
            node_dict["connections"] = []
            for subnode in node_obj.get_all_nodes(recurse=False):
                node_dict["nodes"].append(subnode.id)
            for conn in node_obj.get_all_connections(recurse=False):
                node_dict["connections"].append(conn.id)
            if isinstance(node_obj, node.Facility):
                if node_obj.elevation is not None:
                    node_dict["elevation"] = JSONParser.unit_val_to_dict(
                        node_obj.elevation
                    )

                node_dict["flowrate"] = JSONParser.min_max_design_to_dict(
                    node_obj, "flow_rate"
                )
        elif isinstance(node_obj, node.Joint):
            node_dict["type"] = type(node_obj).__name__
            node_dict["input_contents"] = [
                contents.name for contents in node_obj.input_contents
            ]
            node_dict["output_contents"] = [
                contents.name for contents in node_obj.output_contents
            ]
            node_dict["inflow"] = [conn.id for conn in node_obj.inflow]
            node_dict["outflow"] = [conn.id for conn in node_obj.outflow]
        elif isinstance(node_obj, node.Reducer):
            node_dict["type"] = type(node_obj).__name__
            node_dict["input_contents"] = [
                contents.name for contents in node_obj.input_contents
            ]
            node_dict["output_contents"] = [
                contents.name for contents in node_obj.output_contents
            ]
            node_dict["inflow"] = [conn.id for conn in node_obj.inflow]
            node_dict["outflow"] = [conn.id for conn in node_obj.outflow]
        elif isinstance(node_obj, node.Splitter):
            node_dict["type"] = type(node_obj).__name__
            node_dict["input_contents"] = [
                contents.name for contents in node_obj.input_contents
            ]
            node_dict["output_contents"] = [
                contents.name for contents in node_obj.output_contents
            ]
            node_dict["inflow"] = [conn.id for conn in node_obj.inflow]
            node_dict["outflow"] = [conn.id for conn in node_obj.outflow]
        else:
            raise TypeError("Unsupported Node type: " + type(node_obj).__name__)
        return node_dict

    @staticmethod
    def to_json(network, file_path=None, indent=4, verbose=False):
        """Converts a Network object to a JSON file

        Parameters
        ----------
        network : node.Network
            Network object to export to JSON

        file_path : str
            path to write the configuration in JSON format

        indent : int
            number of spaces to indent the JSON file

        verbose : bool
            Whether to print informative messages for debugging. Default is False

        Raises
        ------
        TypeError
            If `network` is not of type `Network`

        Returns
        -------
        dict
            json in dictionary format
        """
        if not isinstance(network, node.Network):
            raise TypeError("Only Network objects can be converted to JSON format")

        result = {"nodes": [], "connections": [], "virtual_tags": {}}

        for tag_id, tag_obj in network.tags.items():
            if isinstance(tag_obj, VirtualTag):
                if verbose:
                    print(
                        f"Outputting json file, converting {tag_id} to a dictionary..."
                    )
                v_tag_dict = JSONParser.tag_to_dict(tag_obj)
                result["virtual_tags"][tag_id] = v_tag_dict

        for conn_obj in network.get_all_connections(recurse=False):
            result["connections"].append(conn_obj.id)

        for conn_obj in network.get_all_connections(recurse=True):
            if verbose:
                print(
                    f"Outputting json file, converting {conn_obj.id} to a dictionary..."
                )
            conn_dict = JSONParser.conn_to_dict(conn_obj)
            result[conn_obj.id] = conn_dict

        for node_obj in network.get_all_nodes(recurse=False):
            result["nodes"].append(node_obj.id)

        for node_obj in network.get_all_nodes(recurse=True):
            if verbose:
                print(
                    f"Outputting json file, converting {node_obj.id} to a dictionary..."
                )
            node_dict = JSONParser.node_to_dict(node_obj)
            result[node_obj.id] = node_dict

        if file_path is not None:
            with open(file_path, "w") as file:
                json.dump(result, file, indent=indent)

        return result
