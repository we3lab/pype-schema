from abc import ABC
from . import utils


class Node(ABC):
    """Abstract class for all nodes

    Attributes
    ----------
    id : str
        Node ID

    input_contents : ContentsType
        Contents entering the node.

    output_contents : ContentsType
        Contents leaving the node.

    tags : dict of Tag
        Data tags associated with this node
    """

    id: str = NotImplemented
    input_contents: utils.ContentsType = NotImplemented
    output_contents: utils.ContentsType = NotImplemented
    tags: dict = NotImplemented

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Node id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} "
            f"tags:{self.tags}>\n"
        )

    def set_flow_rate(self, min, max, avg):
        """Set the minimum, maximum, and average flow rate of the node

        Parameters
        ----------
        min : int
            Minimum flow rate through the node

        max : int
            Maximum flow rate through the node

        avg : int
            Average flow rate through the node
        """
        self.flow_rate = (min, max, avg)

    def add_tag(self, tag):
        """Adds a tag to the node

        Parameters
        ----------
        tag : Tag
            Tag object to add to the node
        """
        self.tags[tag.id] = tag

    def remove_tag(self, tag_name):
        """Removes a tag from the node

        Parameters
        ----------
        tag_name : str
            name of tag to remove
        """
        del self.tags[tag_name]

    def get_tag(self, tag_name, recurse=False):
        """Gets the Tag object associated with `tag_name`

        Parameters
        ----------
        tag_name : str

        recurse : bool
            Whether or not to get tags recursively.
            Default is False, meaning that only tags involving direct children
            (and this Node itself) will be returned.

        Returns
        ------
        Tag
            wwtp_configuration Tag object associated with the variable name.
            Returns None if the `tag_name` is not found
        """
        tag = None
        if tag_name in self.tags.keys():
            tag = self.tags[tag_name]
        else:
            if hasattr(self, "connections"):
                for connection in self.connections.values():
                    if tag_name in connection.tags.keys():
                        tag = connection.tags[tag_name]
            if hasattr(self, "nodes") and tag is None:
                for node in self.nodes.values():
                    if recurse:
                        tag = node.get_tag(tag_name, recurse=True)
                    else:
                        tag = node.tags[tag_name]

                    if tag:
                        break

        return tag

    def get_all_tags(self, recurse=False):
        """Gets all Tag objects associated with this Node

        Parameters
        ----------
        recurse : bool
            Whether or not to get tags recursively.
            Default is False, meaning that only tags involving direct children
            (and this Node itself) will be returned.

        Returns
        ------
        list of Tag
            Tag objects inside this Node.
            If `recurse` is True, all children, grandchildren, etc. are returned.
            If False, only direct children are returned.
        """
        tags = list(self.tags.values())

        if hasattr(self, "connections"):
            for connection in self.connections.values():
                tags = tags + list(connection.tags.values())

        if hasattr(self, "nodes"):
            for node in self.nodes.values():
                tags = tags + list(node.tags.values())
                if recurse:
                    tags = tags + node.get_all_tags(recurse=recurse)

        # remove duplicates from grabbing top level and next level
        tags = list(set(tags))
        return tags

    def get_node(self, node_name, recurse=False):
        """Get a node from the network

        Parameters
        ----------
        node_name : str
            name of node to retrieve

        recurse : bool
            Whether or not to get nodes recursively.
            Default is False, meaning that only direct children will be returned.

        Returns
        -------
        Node or None
            Node object if node is found. None otherwise
        """
        result = None
        if hasattr(self, "nodes"):
            try:
                return self.nodes[node_name]
            except KeyError:
                if recurse:
                    for node in self.nodes.values():
                        result = node.get_node(node_name, recurse=True)
                        if result:
                            break

        return result

    def get_all_nodes(self, recurse=False):
        """Gets all Node objects associated with this Node

        Parameters
        ----------
        recurse : bool
            Whether or not to get nodes recursively.
            Default is False, meaning that only direct children will be returned.

        Returns
        ------
        list of Node
            Node objects inside this Node.
            If `recurse` is True, all children, grandchildren, etc. are returned.
            If False, only direct children are returned.
        """
        nodes = []
        if hasattr(self, "nodes"):
            nodes = list(self.nodes.values())
            if recurse:
                for node in self.nodes.values():
                    nodes = nodes + node.get_all_nodes(recurse=True)

        return nodes

    def get_connection(self, connection_name, recurse=False):
        """Get a connection from the network
        Parameters
        ----------
        connection_name : str
            name of connection to retrieve

        recurse : bool
            Whether or not to get connections recursively.
            Default is False, meaning that only direct children will be returned.

        Returns
        -------
        Connection or None
            Connection object if node is found. None otherwise
        """
        result = None
        if hasattr(self, "connections"):
            try:
                return self.connections[connection_name]
            except KeyError:
                if recurse:
                    for node in self.nodes.values():
                        result = node.get_connection(connection_name, recurse=True)
                        if result:
                            break

        return result

    def get_all_connections(self, recurse=False):
        """Gets all Connection objects associated with this Node

        Parameters
        ----------
        recurse : bool
            Whether or not to get connections recursively.
            Default is False, meaning that only direct children will be returned.

        Returns
        ------
        list of Connection
            Connection objects inside this Node.
            If `recurse` is True, all children, grandchildren, etc. are returned.
            If False, only direct children are returned.
        """
        connections = []
        if hasattr(self, "connections"):
            connections = list(self.connections.values())

        if recurse:
            if hasattr(self, "nodes"):
                for node in self.nodes.values():
                    connections = connections + node.get_all_connections(recurse=True)
        return connections

    def get_all_connections_to(self, node):
        """Gets all connections entering the specified Node, including those
        from a different level of the hierarchy with `entry_point` specified.

        Paremeters
        ----------
        node : Node
            wwtp_configuration `Node` object for which we want to get connections

        Returns
        -------
        list of Connection
            List of `Connection` objects entering the specified `node`
        """
        if node is None:
            return []

        connections = self.get_all_connections(recurse=True)
        return [
            connection
            for connection in connections
            if connection.destination == node or connection.entry_point == node
        ]

    def get_all_connections_from(self, node):
        """Gets all connections leaving the specified Node, including those
        from a different level of the hierarchy with `exit_point` specified.

        Paremeters
        ----------
        node : Node
            wwtp_configuration `Node` object for which we want to get connections

        Returns
        -------
        list of Connection
            List of `Connection` objects leaving the specified `node`
        """
        if node is None:
            return []

        connections = self.get_all_connections(recurse=True)
        return [
            connection
            for connection in connections
            if connection.source == node or connection.exit_point == node
        ]

    def get_node_or_connection(self, obj_id, recurse=False):
        """Gets the `Node` or `Connection` object with name `obj_id`

        Parameters
        ----------
        obj_id : str
            name of the object to query

        recurse : bool
            Whether or not to get connections or nodes recursively.
            Default is False, meaning that only direct children will be returned.

        Returns
        -------
        Node or Connection
            object with the name `obj_id`
        """
        obj = self.get_node(obj_id, recurse=recurse)
        if obj is None:
            obj = self.get_connection(obj_id, recurse=recurse)

        return obj

    def get_parent_from_tag(self, tag):
        """Gets the parent object of a `Tag` object, as long as both the tag and its
        parent object are children of `self`

        Parameters
        ----------
        tag : Tag
            wwtp_configuration `Node` object for which we want the parent object

        Returns
        -------
        Node or Connection
            parent object of the Tag
        """
        # this logic relies on the guarantee from parse_json that
        # only tags associated with connections will have a valid destination unit ID
        if tag.dest_unit_id:
            parent_obj = self.get_connection(tag.parent_id, recurse=True)
        else:
            parent_obj = self.get_node(tag.parent_id, recurse=True)

        return parent_obj


class Network(Node):
    """A water utility represented as a set of connections and nodes

    Parameters
    ----------
    id : str
        Network ID

    input_contents : ContentsType
        Contents entering the network.

    output_contents : ContentsType
        Contents leaving the network.

    tags : dict of Tag
        Data tags associated with this network

    nodes : dict of Node
        nodes in the network, e.g. pumps, tanks, or facilities

    connections : dict of Connections
        connections in the network, e.g. pipes

    Attributes
    ----------
    id : str
        Network ID

    input_contents : ContentsType
        Contents entering the network.

    output_contents : ContentsType
        Contents leaving the network.

    tags : dict of Tag
        Data tags associated with this network

    nodes : dict of Node
        nodes in the network, e.g. pumps, tanks, or facilities

    connections : dict of Connections
        connections in the network, e.g. pipes
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        tags={},
        nodes={},
        connections={},
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.tags = tags
        self.nodes = nodes
        self.connections = connections

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Network id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} tags:{self.tags} "
            f"nodes:{self.nodes} connections:{self.connections}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.tags == other.tags
            and self.nodes == other.nodes
            and self.connections == other.connections
        )

    def add_node(self, node):
        """Adds a node to the network

        Parameters
        ----------
        node : Node
            Node object to add to the network
        """
        self.nodes[node.id] = node

    def remove_node(self, node_name):
        """Removes a node from the network

        Parameters
        ----------
        node_name : str
            name of node to remove

        Raises
        ------
        KeyError
            if `node_name` is not found
        """
        del self.nodes[node_name]

    def add_connection(self, connection):
        """Adds a connection to the network

        Parameters
        ----------
        connection : Connection
            Connection object to add to the network
        """
        self.connections[connection.id] = connection

    def remove_connection(self, connection_name):
        """Removes a connection from the network
        Parameters
        ----------
        connection_name : str
            name of connection to remove

        Raises
        ------
        KeyError
            if `connection_name` is not found
        """
        del self.connections[connection_name]

    def get_list_of_type(self, desired_type, recurse=False):
        """Searches the Facility and returns a list of all objects of `desired_type`

        Parameters
        ----------
        desired_type : Node or Connection subclass

        recurse : bool
            Whether or not to get objects recursively.
            Default is False, meaning that only direct children will be returned.

        Returns
        ------
        list of `desired_type`
            Objects of `desired_type` inside this Facility.
            If `recurse` is True, all children, grandchildren, etc. are returned.
            If False, only direct children are returned.
        """
        desired_objs = []
        if issubclass(desired_type, Node):
            objs = self.get_all_nodes(recurse=recurse)
        else:
            objs = self.get_all_connections(recurse=recurse)

        for obj in objs:
            if isinstance(obj, desired_type):
                desired_objs.append(obj)

        return desired_objs


class Facility(Network):
    """
    Parameters
    ----------
    id : str
        Facility ID

    input_contents : ContentsType
        Contents entering the facility.

    output_contents : ContentsType
        Contents leaving the facility.

    elevation : int
        Elevation of the facility

    min_flow : int
        Minimum flow rate through the facility

    max_flow : int
        Maximum flow rate through the facility

    avg_flow : int
        Average flow rate through the facility

    tags : dict of Tag
        Data tags associated with this facility

    nodes : dict of Node
        nodes in the facility, e.g. pumps, tanks, or processes

    connections : dict of Connections
        connections in the facility, e.g. pipes

    Attributes
    ----------
    id : str
        Facility ID

    input_contents : ContentsType
        Contents entering the facility.

    output_contents : ContentsType
        Contents leaving the facility.

    elevation : int
        Elevation of the facility in meters above sea level

    tags : dict of Tag
        Data tags associated with this facility

    flow_rate : tuple
        Tuple of minimum, maximum, and average facility flow rate

    nodes : dict of Node
        nodes in the facility, e.g. pumps, tanks, or processes

    connections : dict of Connections
        connections in the facility, e.g. pipes
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        elevation,
        min_flow,
        max_flow,
        avg_flow,
        tags={},
        nodes={},
        connections={},
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.elevation = elevation
        self.nodes = nodes
        self.connections = connections
        self.tags = tags
        self.set_flow_rate(min_flow, max_flow, avg_flow)

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Facility id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} elevation:{self.elevation} "
            f"flow_rate:{self.flow_rate} tags:{self.tags} "
            f"nodes:{self.nodes} connections:{self.connections}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.elevation == other.elevation
            and self.nodes == other.nodes
            and self.connections == other.connections
            and self.flow_rate == other.flow_rate
            and self.tags == other.tags
        )


class Pump(Node):
    """
    Parameters
    ----------
    id : str
        Pump ID

    input_contents : ContentsType
        Contents entering the pump

    output_contents : ContentsType
        Contents leaving the pump

    elevation : int
        Elevation of the pump in meters above sea level

    horsepower : int
        Horsepower of a single pump

    num_units : int
        Number of pumps running in parallel

    min_flow : int
        Minimum flow rate supplied by the pump

    max_flow : int
        Maximum flow rate supplied by the pump

    avg_flow : int
        Average flow rate supplied by the pump

    pump_type : PumpType
        Type of pump (either VFD or constant)

    tags : dict of Tag
        Data tags associated with this pump

    Attributes
    ----------
    id : str
        Pump ID

    input_contents : ContentsType
        Contents entering the pump

    output_contents : ContentsType
        Contents leaving the pump

    elevation : int
        Elevation of the pump in meters above sea level

    horsepower : int
        Horsepower of a single pump

    num_units : int
        Number of pumps running in parallel

    flow_rate : tuple
        Tuple of minimum, maximum, and average pump flow rate

    tags : dict of Tag
        Data tags associated with this pump

    energy_efficiency : function
        Function which takes in the current flow rate and returns the energy
        required to pump at that rate
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        avg_flow,
        elevation,
        horsepower,
        num_units,
        pump_type=utils.PumpType.Constant,
        tags={},
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.elevation = elevation
        self.pump_type = pump_type
        self.horsepower = horsepower
        self.num_units = num_units
        self.tags = tags
        self.set_flow_rate(min_flow, max_flow, avg_flow)
        self.set_energy_efficiency(None)

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Pump id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} "
            f"flow_rate:{self.flow_rate} elevation:{self.elevation} "
            f"horsepower:{self.horsepower} num_units:{self.num_units} "
            f"tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.elevation == other.elevation
            and self.pump_type == other.pump_type
            and self.horsepower == other.horsepower
            and self.num_units == other.num_units
            and self.tags == other.tags
            and self.flow_rate == other.flow_rate
            and self.energy_efficiency == other.energy_efficiency
        )

    def set_pump_type(self, pump_type):
        """Set the pump curve to the given function

        Parameters
        ----------
        pump_type : PumpType
        """
        # TODO: check that pump_type is a valid enum
        self.pump_type = pump_type

    def set_energy_efficiency(self, pump_curve):
        """Set the pump curve to the given function

        Parameters
        ----------
        pump_curve : function
            function which takes in the current flow rate and returns the energy
            required to pump at that rate
        """
        # TODO: type check that pump_curve is a function
        self.energy_efficiency = pump_curve


class Tank(Node):
    """
    Parameters
    ----------
    id : str
        Tank ID

    input_contents : ContentsType
        Contents entering the tank.

    output_contents : ContentsType
        Contents leaving the tank.

    elevation : int
        Elevation of the tank in meters above sea level

    volume : int
        Volume of the tank in cubic meters

    tags : dict of Tag
        Data tags associated with this tank

    Attributes
    ----------
    id : str
        Tank ID

    input_contents : ContentsType
        Contents entering the tank.

    output_contents : ContentsType
        Contents leaving the tank.

    elevation : int
        Elevation of the tank in meters above sea level

    volume : int
        Volume of the tank in cubic meters

    tags : dict of Tag
        Data tags associated with this tank
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        elevation,
        volume,
        tags={},
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.elevation = elevation
        self.volume = volume
        self.tags = tags

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Tank id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} elevation:{self.elevation} "
            f"volume:{self.volume} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.elevation == other.elevation
            and self.volume == other.volume
            and self.tags == other.tags
        )


class Reservoir(Node):
    """
    Parameters
    ----------
    id : str
        Reservoir ID

    input_contents : ContentsType
        Contents entering the reservoir.

    output_contents : ContentsType
        Contents leaving the reservoir.

    elevation : int
        Elevation of the reservoir in meters above sea level

    volume : int
        Volume of the reservoir in cubic meters

    tags : dict of Tag
        Data tags associated with this reservoir

    Attributes
    ----------
    id : str
        Reservoir ID

    input_contents : ContentsType
        Contents entering the reservoir.

    output_contents : ContentsType
        Contents leaving the reservoir.

    elevation : int
        Elevation of the reservoir in meters above sea level

    volume : int
        Volume of the reservoir in cubic meters

    tags : dict of Tag
        Data tags associated with this reservoir
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        elevation,
        volume,
        tags={},
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.elevation = elevation
        self.volume = volume
        self.tags = tags

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Reservoir id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} elevation:{self.elevation} "
            f"volume:{self.volume} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.elevation == other.elevation
            and self.volume == other.volume
            and self.tags == other.tags
        )


class Battery(Node):
    """
    Parameters
    ----------
    id : str
        Battery ID

    capacity : int
        Storage capacity of the battery in kWh

    discharge_rate : int
        Maximum discharge rate of the battery in kW

    tags : dict of Tag
        Data tags associated with this battery

    Attributes
    ----------
    id : str
        Battery ID

    input_contents : ContentsType
        Contents entering the reservoir.

    output_contents : ContentsType
        Contents leaving the reservoir.

    capacity : int
        Storage capacity of the battery in kWh

    discharge_rate : int
        Maximum discharge rate of the battery in kW

    tags : dict of Tag
        Data tags associated with this reservoir
    """

    def __init__(
        self,
        id,
        capacity,
        discharge_rate,
        tags={},
    ):
        self.id = id
        self.input_contents = utils.ContentsType.Electricity
        self.output_contents = utils.ContentsType.Electricity
        self.capacity = capacity
        self.discharge_rate = discharge_rate
        self.tags = tags

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Reservoir id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} capacity:{self.capacity} "
            f"discharge_rate:{self.discharge_rate} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.capacity == other.capacity
            and self.discharge_rate == other.discharge_rate
            and self.tags == other.tags
        )


class Digestion(Node):
    """
    Parameters
    ----------
    id : str
        Digester ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the digester (e.g. biogas or wastewater)

    output_contents : ContentsType or list of ContentsType
        Contents leaving the digester (e.g. biogas or wastewater)

    min_flow : int
        Minimum flow rate through the process

    max_flow : int
        Maximum flow rate through the process

    avg_flow : int
        Average flow rate through the process

    num_units : int
        Number of digesters running in parallel

    volume : int
        Volume of the digester in cubic meters

    digester_type : DigesterType
        Type of digestion (aerobic or anaerobic)

    tags : dict of Tag
        Data tags associated with this digester

    Attributes
    ----------
    id : str
        Digester ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the digester (e.g. biogas or wastewater)

    output_contents : ContentsType or list of ContentsType
        Contents leaving the digester (e.g. biogas or wastewater)

    num_units : int
        Number of digesters running in parallel

    volume : int
        Volume of the digester in cubic meters

    flow_rate : tuple
        Tuple of minimum, maximum, and average digester flow rate

    digester_type : DigesterType
        Type of digestion (aerobic or anaerobic)

    tags : dict of Tag
        Data tags associated with this digester
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        avg_flow,
        num_units,
        volume,
        digester_type,
        tags={},
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.num_units = num_units
        self.volume = volume
        self.digester_type = digester_type
        self.tags = tags
        self.set_flow_rate(min_flow, max_flow, avg_flow)

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Digestion id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"volume:{self.volume} flow_rate:{self.flow_rate} "
            f"digester_type:{self.digester_type} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.volume == other.volume
            and self.digester_type == other.digester_type
            and self.flow_rate == other.flow_rate
            and self.tags == other.tags
        )


class Cogeneration(Node):
    """
    Parameters
    ----------
    id : str
        Cogenerator ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the cogenerator

    min_gen : int
        Minimum generation capacity of a single cogenerator

    max_gen : int
        Maximum generation capacity of a single cogenerator

    avg_gen : int
        Average generation capacity of a single cogenerator

    num_units : int
        Number of cogenerator units running in parallel

    tags : dict of Tag
        Data tags associated with this cogenerator

    Attributes
    ----------
    id : str
        Cogenerator ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the cogenerator
        (biogas, natural gas, or a blend of the two)

    output_contents : ContentsType
        Contents leaving the cogenerator (Electricity)

    gen_capacity : tuple
        Minimum, maximum, and average generation capacity

    num_units : int
        Number of cogenerator units running in parallel

    tags : dict of Tag
        Data tags associated with this cogenerator

    energy_efficiency : function
        Function which takes in the current heat produced in BTU and returns
        the energy produced in kWh
    """

    def __init__(
        self, id, input_contents, min_gen, max_gen, avg_gen, num_units, tags={}
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = utils.ContentsType.Electricity
        self.num_units = num_units
        self.tags = tags
        self.set_gen_capacity(min_gen, max_gen, avg_gen)

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Cogeneration id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.input_contents} num_units:{self.num_units} "
            f"gen_capacity:{self.gen_capacity} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.num_units == other.num_units
            and self.gen_capacity == other.gen_capacity
            and self.tags == other.tags
        )

    def set_gen_capacity(self, min, max, avg):
        """Set the minimum, maximum, and average generation capacity

        Parameters
        ----------
        min : int
            Minimum generation by a single cogenerator

        max : int
            Maximum generation by a single cogenerator

        avg : int
            Average generation by a single cogenerator
        """
        self.gen_capacity = (min, max, avg)

    def set_energy_efficiency(self, efficiency_curve):
        """Set the cogeneration efficiency to the given function

        Parameters
        ----------
        efficiency_curve : function
            function takes in the current heat produced in BTU and returns
            the energy produced in kWh
        """
        # TODO: type check that efficiency_curve is a function
        self.energy_efficiency = efficiency_curve


class Clarification(Node):
    """
    Parameters
    ----------
    id : str
        Clarifier ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the clarifier

    output_contents : ContentsType or list of ContentsType
        Contents leaving the clarifier

    min_flow : int
        Minimum flow rate of a single clarifier

    max_flow : int
        Maximum flow rate of a single clarifier

    avg_flow : int
        Average flow rate of a single clarifier

    num_units : int
        Number of clarifiers running in parallel

    volume : int
        Volume of the clarifier in cubic meters

    tags : dict of Tag
        Data tags associated with this clarifier

    Attributes
    ----------
    id : str
        Clarifier ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the clarifier

    output_contents : ContentsType or list of ContentsType
        Contents leaving the clarifier

    num_units : int
        Number of clarifiers running in parallel

    volume : int
        Volume of a single clarifier in cubic meters

    flow_rate : tuple
        Tuple of minimum, maximum, and average digester flow rate

    tags : dict of Tag
        Data tags associated with this clarifier
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        avg_flow,
        num_units,
        volume,
        tags={},
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.num_units = num_units
        self.volume = volume
        self.tags = tags
        self.set_flow_rate(min_flow, max_flow, avg_flow)

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Clarification id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"volume:{self.volume} flow_rate:{self.flow_rate} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.volume == other.volume
            and self.flow_rate == other.flow_rate
            and self.tags == other.tags
        )


class Filtration(Node):
    """
    Parameters
    ----------
    id : str
        Filter ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the filter

    output_contents : ContentsType or list of ContentsType
        Contents leaving the filter

    min_flow : int
        Minimum flow rate of a single filter

    max_flow : int
        Maximum flow rate of a single filter

    avg_flow : int
        Average flow rate of a single filter

    num_units : int
        Number of filters running in parallel

    volume : int
        Volume of a single filter in cubic meters

    tags : dict of Tag
        Data tags associated with this filter

    Attributes
    ----------
    id : str
        Filter ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the filter

    output_contents : ContentsType or list of ContentsType
        Contents leaving the filter

    num_units : int
        Number of filters running in parallel

    volume : int
        Volume of a single filter in cubic meters

    flow_rate : tuple
        Minimum, maximum, and average flow rate

    tags : dict of Tag
        Data tags associated with this filter
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        avg_flow,
        num_units,
        volume,
        tags={},
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.num_units = num_units
        self.volume = volume
        self.tags = tags
        self.set_flow_rate(min_flow, max_flow, avg_flow)

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Filtration id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"volume:{self.volume} flow_rate:{self.flow_rate} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.volume == other.volume
            and self.flow_rate == other.flow_rate
            and self.tags == other.tags
        )


class Screening(Node):
    """
    Parameters
    ----------
    id : str
        Screen ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the screen

    output_contents : ContentsType or list of ContentsType
        Contents leaving the screen

    min_flow : int
        Minimum flow rate of a single screen

    max_flow : int
        Maximum flow rate of a single screen

    avg_flow : int
        Average flow rate of a single screen

    num_units : int
        Number of screens running in parallel

    tags : dict of Tag
        Data tags associated with this screen

    Attributes
    ----------
    id : str
        Screen ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the screen

    output_contents : ContentsType or list of ContentsType
        Contents leaving the screen

    num_units : int
        Number of screens running in parallel

    flow_rate : tuple
        Minimum, maximum, and average flow rate

    tags : dict of Tag
        Data tags associated with this screen
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        avg_flow,
        num_units,
        tags={},
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.num_units = num_units
        self.tags = tags
        self.set_flow_rate(min_flow, max_flow, avg_flow)

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Screening id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"flow_rate:{self.flow_rate} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.flow_rate == other.flow_rate
            and self.tags == other.tags
        )


class Conditioning(Node):
    """
    Parameters
    ----------
    id : str
        Conditioner ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the biogas conditioner

    output_contents : ContentsType or list of ContentsType
        Contents leaving the biogas conditioner

    min_flow : int
        Minimum flow rate of a single biogas conditioner

    max_flow : int
        Maximum flow rate of a single biogas conditioner

    avg_flow : int
        Average flow rate of a single biogas conditioner

    num_units : int
        Number of biogas conditioners running in parallel

    tags : dict of Tag
        Data tags associated with this biogas conditioner

    Attributes
    ----------
    id : str
        Conditioner ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the biogas conditioner

    output_contents : ContentsType or list of ContentsType
        Contents leaving the biogas conditioner

    num_units : int
        Number of biogas conditioners running in parallel

    flow_rate : tuple
        Minimum, maximum, and average flow rate

    tags : dict of Tag
        Data tags associated with this screen
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        avg_flow,
        num_units,
        tags={},
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.num_units = num_units
        self.tags = tags
        self.set_flow_rate(min_flow, max_flow, avg_flow)

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Conditioning id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"flow_rate:{self.flow_rate} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.flow_rate == other.flow_rate
            and self.tags == other.tags
        )


class Thickening(Node):
    """
    Parameters
    ----------
    id : str
        Thickener ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the thickener

    output_contents : ContentsType or list of ContentsType
        Contents leaving the thickener

    min_flow : int
        Minimum flow rate of a single thickener

    max_flow : int
        Maximum flow rate of a single thickener

    avg_flow : int
        Average flow rate of a single thickener

    num_units : int
        Number of thickeners running in parallel

    volume : int
        Volume of a single thickener in cubic meters

    tags : dict of Tag
        Data tags associated with this thickener

    Attributes
    ----------
    id : str
        Thickener ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the thickener

    output_contents : ContentsType or list of ContentsType
        Contents leaving the thickener

    num_units : int
        Number of thickeners running in parallel

    volume : int
        Volume of a single thickener in cubic meters

    flow_rate : tuple
        Minimum, maximum, and average flow rate

    tags : dict of Tag
        Data tags associated with this thickener
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        avg_flow,
        num_units,
        volume,
        tags={},
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.num_units = num_units
        self.volume = volume
        self.tags = tags
        self.set_flow_rate(min_flow, max_flow, avg_flow)

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Thickening id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"volume:{self.volume} flow_rate:{self.flow_rate} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.volume == other.volume
            and self.flow_rate == other.flow_rate
            and self.tags == other.tags
        )


class Aeration(Node):
    """
    Parameters
    ----------
    id : str
        Aerator ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the aeration basin

    output_contents : ContentsType or list of ContentsType
        Contents leaving the aeration basin

    min_flow : int
        Minimum flow rate of a single aeration basin

    max_flow : int
        Maximum flow rate of a single aeration basin

    avg_flow : int
        Average flow rate of a single aeration basin

    num_units : int
        Number of aeration basins running in parallel

    volume : int
        Volume of a single aeration basin in cubic meters

    tags : dict of Tag
        Data tags associated with this aerator

    Attributes
    ----------
    id : str
        Aerator ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the aeration basin

    output_contents : ContentsType or list of ContentsType
        Contents leaving the aeration basin

    num_units : int
        Number of aeration basins running in parallel

    volume : int
        Volume of a single aeration basin in cubic meters

    flow_rate : tuple
        Minimum, maximum, and average flow rate

    tags : dict of Tag
        Data tags associated with this aerator
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        avg_flow,
        num_units,
        volume,
        tags={},
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.num_units = num_units
        self.volume = volume
        self.tags = tags
        self.set_flow_rate(min_flow, max_flow, avg_flow)

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Aeration id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"volume:{self.volume} flow_rate:{self.flow_rate} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.volume == other.volume
            and self.flow_rate == other.flow_rate
            and self.tags == other.tags
        )


class Chlorination(Node):
    """
    Parameters
    ----------
    id : str
        Chlorinator ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the chlorinator

    output_contents : ContentsType or list of ContentsType
        Contents leaving the chlorinator

    min_flow : int
        Minimum flow rate of a single chlorinator

    max_flow : int
        Maximum flow rate of a single chlorinator

    avg_flow : int
        Average flow rate of a single chlorinator

    num_units : int
        Number of chlorinators running in parallel

    volume : int
        Volume of a single chlorinator in cubic meters

    tags : dict of Tag
        Data tags associated with this chlorinator

    Attributes
    ----------
    id : str
        Chlorinator ID

    input_contents : ContentsType or list of ContentsType
        Contents entering the chlorinator

    output_contents : ContentsType or list of ContentsType
        Contents leaving the chlorinator

    num_units : int
        Number of chlorinators running in parallel

    volume : int
        Volume of a single chlorinator in cubic meters

    flow_rate : tuple
        Minimum, maximum, and average flow rate

    tags : dict of Tag
        Data tags associated with this chlorinator
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        min_flow,
        max_flow,
        avg_flow,
        num_units,
        volume,
        tags={},
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.num_units = num_units
        self.volume = volume
        self.tags = tags
        self.set_flow_rate(min_flow, max_flow, avg_flow)

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Chlorination id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} num_units:{self.num_units} "
            f"volume:{self.volume} flow_rate:{self.flow_rate} tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.output_contents == other.output_contents
            and self.num_units == other.num_units
            and self.volume == other.volume
            and self.flow_rate == other.flow_rate
            and self.tags == other.tags
        )


class Flaring(Node):
    """
    Parameters
    ----------
    id : str
        Flare ID

    num_units : int
        Number of flares running in parallel

    tags : dict of Tag
        Data tags associated with this flare

    Attributes
    ----------
    id : str
        Flare ID

    input_contents : ContentsType
        Contents entering the flare

    num_units : int
        Number of flares running in parallel

    tags : dict of Tag
        Data tags associated with this flare
    """

    def __init__(self, id, num_units, tags={}):
        self.id = id
        self.input_contents = utils.ContentsType.Biogas
        self.num_units = num_units
        self.tags = tags

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Flaring id:{self.id} "
            f"input_contents:{self.input_contents} num_units:{self.num_units} "
            f"tags:{self.tags}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        return (
            self.id == other.id
            and self.input_contents == other.input_contents
            and self.num_units == other.num_units
            and self.tags == other.tags
        )
