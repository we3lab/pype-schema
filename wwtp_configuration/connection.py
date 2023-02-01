from abc import ABC
from . import utils
from . import node


class Connection(ABC):
    """Abstract class for all connections

    Attributes
    ----------
    id : str
        Connection ID

    contents : ContentsType
        Contents moving through the node

    source : Node
        Starting point of the connection

    destination : Node
        Endpoint of the connection

    tags : dict of Tag
        Data tags associated with this connection

    bidirectional : bool
        whether flow can go from destination to source. False by default

    exit_point : Node
        The child node from which this connection leaves its source.
        Default is None, indicating the source does not have any children

    entry_point : Node
        The child node at which this connection enters its destination.
        Default is None, indicating the destination does not have any children
    """

    id: str = NotImplemented
    contents: utils.ContentsType = NotImplemented
    source: node.Node = NotImplemented
    destination: node.Node = NotImplemented
    tags: dict = NotImplemented
    bidirectional: bool = False
    exit_point: node.Node = None
    entry_point: node.Node = None

    def __repr__(self):
        if self.exit_point is None:
            exit_point_id = "None"
        else:
            exit_point_id = self.exit_point.id

        if self.entry_point is None:
            entry_point_id = "None"
        else:
            entry_point_id = self.entry_point.id

        return (
            f"<wwtp_configuration.connection.Connection id:{self.id} "
            f"contents:{self.contents} source:{self.source.id} "
            f"destination:{self.destination.id} "
            f"tags:{self.tags} bidirectional:{self.bidirectional} "
            f"exit_point:{exit_point_id} entry_point:{entry_point_id}>\n"
        )

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

    def get_source_id(self):
        """
        Returns
        -------
        str
            name of the source node
        """
        try:
            id = self.source.id
        except AttributeError:
            id = None

        return id

    def get_dest_id(self):
        """
        Returns
        -------
        str
            name of the destination node
        """
        try:
            id = self.destination.id
        except AttributeError:
            id = None

        return id

    def get_num_source_units(self):
        """
        Returns
        -------
        int
            number of units in the source node
        """
        try:
            num_units = self.source.num_units
        except AttributeError:
            num_units = None

        return num_units

    def get_num_dest_units(self):
        """
        Returns
        -------
        int
            number of units in the destination node
        """
        try:
            num_units = self.destination.num_units
        except AttributeError:
            num_units = None

        return num_units

    def get_source_node(self, recurse=False):
        """ Gets a connection's source node returning its exit point if `recurse` is True

        Parameters
        ----------
        recurse : bool
            Return `exit_point` if True. Otherwise just return `source`

        Returns
        -------
        wwtp_configuration.Node
            The source node corresponding to `connection`
        """
        node_obj = self.source
        if recurse:
            node_obj = self.exit_point
            if node_obj is None:
                node_obj = self.source
        return node_obj

    def get_dest_node(self, recurse=False):
        """ Gets a connection's destination node, returning its entry point if `recurse` is True

        Parameters
        ----------
        recurse : bool
            Return `entry_point` if True. Otherwise just return `destination`

        Returns
        -------
        wwtp_configuration.Node
            The destination node corresponding to `connection`
        """
        node_obj = self.destination
        if recurse:
            node_obj = self.entry_point
            if node_obj is None:
                node_obj = self.destination
        return node_obj

    def select_objs(
        contents_type=None,
        tag_type=None,
        recurse=False,
        source_id=None,
        dest_id=None,
        source_node_type=None,
        dest_node_type=None,
    ):
        """ Selects from this Connection all Tag objects which match source/destination node-type/unit_id/contents
        (if none given, returns all objects in the Node)

        Parameters
        ----------
        source_id : str, None
            Optional id of the source node whose connections we want to subset to

        dest_id : str, None
            Optional id of the destination node whose connections we want to subset to

        source_node_type : wwtp_configuration.NodeType, None
            Optional type of source node whose connections we want to subset to

        dest_node_type : wwtp_configuration.NodeType, None
            Optional type of destination node whose connections we want to subset to

        contents_type : wwtp_configuration.utils.ContentsType, None
            Optional contents of the objects we want to subset to

        Raises
        ------
        ValueError
            When a source/destination node type is provided to subset tags

        TypeError
            When the objects to select among are not of type {'wwtp_configuration.Tag' or `wwtp_configuration.Connection`}

        Returns
        -------
        list
            List of 'wwtp_configuration.Tag' or `wwtp_configuration.Connection` objects subset according to source/destination
            id and `content_type`

        """
        selected_objs = []
        if isinstance(objs, list):
            objs = {obj.id : obj for obj in objs}
        # Select according to source/destination node type/id
        for obj in objs.values():
            if isinstance(obj, Tag):
                if source_node_type is not None or dest_node_type is not None:
                    raise ValueError("Only Connections objects have source and destination nodes/node-types")
                obj_source_unit_id = str(obj.source_unit_id)
                obj_dest_unit_id = str(obj.dest_unit_id)
                obj_source_id, obj_entry_point, obj_dest_id, obj_exit_point = None, None, None, None
            elif isinstance(obj, Connection):
                obj_source_unit_id, obj_dest_unit_id = None, None
                source_node = obj.get_source_node(recurse=True)
                obj_exit_point = source_node.id
                obj_source_id = obj.source.id
                destination_node = obj.get_dest_node(recurse=True)
                obj_entry_point = destination_node.id
                obj_dest_id = obj.destination.id
            else:
                raise TypeError("Object must be of type 'Connection' or 'Tag'")
            if source_id:
                if source_id == dest_id and (
                    source_id in [obj_source_id, obj_exit_point, obj_source_unit_id]
                    or dest_id in [obj_dest_id, obj_entry_point, obj_dest_unit_id]
                ):
                    selected_objs.append(obj)
                elif source_id in [obj_source_id, obj_exit_point, obj_source_unit_id]:
                    if dest_id:
                        if dest_id in [obj_dest_id, obj_entry_point, obj_dest_unit_id]:
                            selected_objs.append(obj)
                    else:
                        selected_objs.append(obj)
            elif dest_id:
                if dest_id in [obj_dest_id, obj_entry_point, obj_dest_unit_id]:
                    selected_objs.append(obj)
            elif source_node_type:
                if source_node_type == dest_node_type and (
                    isinstance(source_node, source_node_type)
                    or isinstance(obj.source, source_node_type)
                    or isinstance(destination_node, dest_node_type)
                    or isinstance(obj.destination, dest_node_type)
                ):
                    selected_objs.append(obj)
                elif (
                    isinstance(source_node, source_node_type)
                    or isinstance(obj.source, source_node_type)
                ):
                    if dest_node_type:
                        if (
                            isinstance(destination_node, dest_node_type)
                            or isinstance(obj.destination, dest_node_type)
                        ):
                            selected_objs.append(obj)
                    else:
                        selected_objs.append(obj)
            elif dest_node_type:
                if (
                    isinstance(destination_node, dest_node_type)
                    or isinstance(obj.destination, dest_node_type)
                ):
                    selected_objs.append(obj)
            else:
                selected_objs.append(obj)
            # Select according to contents
            if contents_type is not None:
                selected_objs = [obj for obj in selected_objs if obj.contents == contents_type]

        return selected_objs


class Pipe(Connection):
    """
    Parameters
    ---------
    id : str
        Pipe ID

    contents : ContentsType
        Contents moving through the connection

    source : Node
        Starting point of the connection

    destination : Node
        Endpoint of the connection

    min_flow : int
        Minimum flow rate through the pipe

    max_flow : int
        Maximum flow rate through the pipe

    avg_flow : int
        Average flow rate through the pipe

    diameter : int
        Pipe diameter in meters

    friction_coeff : int
        Friction coefficient for the pipe

    min_pres : int
        Minimum pressure inside the pipe

    max_pres : int
        Maximum pressure inside the pipe

    avg_pres : int
        Average pressure inside the pipe

    lower_heating_value : float
        Lower heating value of gas in the pipe

    higher_heating_value : float
        Higher heating value of gas in the pipe

    tags : dict of Tag
        Data tags associated with this pipe

    bidirectional : bool
        Whether flow can go from destination to source. False by default

    exit_point : Node
        The child node from which this connection leaves its source.
        Default is None, indicating the source does not have any children

    entry_point : Node
        The child node at which this connection enters its destination.
        Default is None, indicating the destination does not have any children

    Attributes
    ----------
    id : str
        Pipe ID

    contents : ContentsType
        Contents moving through the connection

    source : Node
        Starting point of the connection

    destination : Node
        Endpoint of the connection

    flow_rate : tuple
        Minimum, maximum, and average flow rate through the pipe

    diameter : int
        Pipe diameter in meters

    friction_coeff : int
        Friction coefficient for the pipe

    pressure : tuple
        Minimum, maximum, and average pressure in the pipe

    heating_values : tuple
        The lower and higher heating values of the gas in the pipe.
        None if the pipe is not transporting gas

    tags : dict of Tag
        Data tags associated with this pipe

    bidirectional : bool
        Whether flow can go from destination to source. False by default

    exit_point : Node
        The child node from which this connection leaves its source.
        Default is None, indicating the source does not have any children

    entry_point : Node
        The child node at which this connection enters its destination.
        Default is None, indicating the destination does not have any children
    """

    def __init__(
        self,
        id,
        contents,
        source,
        destination,
        min_flow,
        max_flow,
        avg_flow,
        diameter=None,
        friction=None,
        min_pres=None,
        max_pres=None,
        avg_pres=None,
        lower_heating_value=None,
        higher_heating_value=None,
        tags={},
        bidirectional=False,
        exit_point=None,
        entry_point=None,
    ):
        self.id = id
        self.contents = contents
        self.source = source
        self.destination = destination
        self.diameter = diameter
        self.friction_coeff = friction
        self.set_pressure(min_pres, max_pres, avg_pres)
        self.set_flow_rate(min_flow, max_flow, avg_flow)
        self.set_heating_values(lower_heating_value, higher_heating_value)
        self.tags = tags
        self.bidirectional = bidirectional
        self.exit_point = exit_point
        self.entry_point = entry_point

    def __repr__(self):
        if self.exit_point is None:
            exit_point_id = "None"
        else:
            exit_point_id = self.exit_point.id

        if self.entry_point is None:
            entry_point_id = "None"
        else:
            entry_point_id = self.entry_point.id

        return (
            f"<wwtp_configuration.connection.Pipe id:{self.id} "
            f"contents:{self.contents} source:{self.source.id} "
            f"destination:{self.destination.id} "
            f"flow_rate:{self.flow_rate} pressure:{self.pressure} "
            f"heating_values:{self.heating_values} "
            f"diameter:{self.diameter} friction_coeff:{self.friction_coeff} "
            f"tags:{self.tags} bidirectional:{self.bidirectional} "
            f"exit_point:{exit_point_id} entry_point:{entry_point_id}>\n"
        )

    def __eq__(self, other):
        if not isinstance(other, Pipe):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return (
            self.id == other.id
            and self.contents == other.contents
            and self.source == other.source
            and self.destination == other.destination
            and self.diameter == other.diameter
            and self.friction_coeff == other.friction_coeff
            and self.pressure == other.pressure
            and self.heating_values == other.heating_values
            and self.flow_rate == other.flow_rate
            and self.tags == other.tags
            and self.bidirectional == other.bidirectional
            and self.exit_point == other.exit_point
            and self.entry_point == other.entry_point
        )

    def set_flow_rate(self, min, max, avg):
        """Set the minimum, maximum, and average flow rate through the connection

        Parameters
        ----------
        min : int
            Minimum flow rate through the connection

        max : int
            Maximum flow rate through the connection

        avg : int
            Average flow rate through the connection
        """
        self.flow_rate = (min, max, avg)

    def set_pressure(self, min, max, avg):
        """Set the minimum, maximum, and average pressure inside the connection

        Parameters
        ----------
        min : int
            Minimum pressure inside the connection

        max : int
            Maximum pressure inside the connection

        avg : int
            Average pressure inside the connection
        """
        self.pressure = (min, max, avg)

    def set_heating_values(self, lower, higher):
        """Set the lower and higher heating values for gas in the connection

        Parameters
        ----------
        lower : float
            Lower heating value of gas in the pipe

        higher : float
            Higher heating value of gas in the pipe
        """
        self.heating_values = (lower, higher)


class Wire(Connection):
    """
    Parameters
    ---------
    id : str
        Pipe ID

    source : Node
        Starting point of the connection

    destination : Node
        Endpoint of the connection

    tags : dict of Tag
        Data tags associated with this pump

    bidirectional
        whether electricity can flow from destination to source. False by default

    Attributes
    ----------
    id : str
        Pipe ID

    contents : ContentsType
        Contents moving through the connection.

    source : Node
        Starting point of the connection

    destination : Node
        Endpoint of the connection

    tags : dict of Tag
        Data tags associated with this pipe

    bidirectional
        Whether electricity can flow from destination to source. False by default
    """

    def __init__(
        self,
        id,
        source,
        destination,
        tags={},
        bidirectional=False,
        exit_point=None,
        entry_point=None,
    ):
        self.id = id
        self.source = source
        self.destination = destination
        self.tags = tags
        self.bidirectional = bidirectional
        self.exit_point = exit_point
        self.entry_point = entry_point
        self.contents = utils.ContentsType.Electricity

    def __repr__(self):
        if self.exit_point is None:
            exit_point_id = "None"
        else:
            exit_point_id = self.exit_point.id

        if self.entry_point is None:
            entry_point_id = "None"
        else:
            entry_point_id = self.entry_point.id

        return (
            f"<wwtp_configuration.connection.Wire id:{self.id} "
            f"contents:{self.contents} source:{self.source.id} "
            f"destination:{self.destination.id} "
            f"tags:{self.tags} bidirectional:{self.bidirectional} "
            f"exit_point:{exit_point_id} entry_point:{entry_point_id}>\n"
        )

    def __eq__(self, other):
        if not isinstance(other, Wire):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return (
            self.id == other.id
            and self.contents == other.contents
            and self.source == other.source
            and self.destination == other.destination
            and self.tags == other.tags
            and self.bidirectional == other.bidirectional
            and self.exit_point == other.exit_point
            and self.entry_point == other.entry_point
        )
