import warnings
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
        Whether flow can go from destination to source. False by default

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
            f"<pype_schema.connection.Connection id:{self.id} "
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
        if not tag.parent_id:
            tag.parent_id = self.id
        self.tags[tag.id] = tag

    def remove_tag(self, tag_name):
        """Removes a tag from the node

        Parameters
        ----------
        tag_name : str
            name of tag to remove
        """
        del self.tags[tag_name]

    def get_tag(self, tag_name):
        """Adds a tag to the node

        Parameters
        ----------
        tag_name : str
            Name of the tag to receive
        """
        return self.tags[tag_name]

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

    def get_exit_point(self):
        """
        Returns
        -------
        str
            name of the exit point Node (if it exists - None otherwise)
        """
        try:
            id = self.exit_point
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

    def get_entry_point(self):
        """
        Returns
        -------
        str
            name of the entry point Node (if it exists - None otherwise)
        """
        try:
            id = self.entry_point
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
        """Gets a connection's source node returning its exit point if `recurse` is True

        Parameters
        ----------
        recurse : bool
            Return `exit_point` if True. Otherwise just return `source`

        Returns
        -------
        pype_schema.Node
            The source node corresponding to `connection`
        """
        node_obj = self.source
        if recurse:
            node_obj = self.exit_point
            if node_obj is None:
                node_obj = self.source
        return node_obj

    def get_dest_node(self, recurse=False):
        """Gets a connection's destination node,
        returning its entry point if `recurse` is True

        Parameters
        ----------
        recurse : bool
            Return `entry_point` if True. Otherwise just return `destination`

        Returns
        -------
        pype_schema.Node
            The destination node corresponding to `connection`
        """
        node_obj = self.destination
        if recurse:
            node_obj = self.entry_point
            if node_obj is None:
                node_obj = self.destination
        return node_obj


class Pipe(Connection):
    """A generic class for pipes that transport any fluid,
    such as drinking water, natural gas, or industrial wastewater.

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

    min_flow : pint.Quantity or int
        Minimum flow rate through the pipe

    max_flow : pint.Quantity or int
        Maximum flow rate through the pipe

    avg_flow : pint.Quantity or int
        Average flow rate through the pipe

    diameter : pint.Quantity or int
        Pipe diameter

    friction : float
        Friction coefficient for the pipe

    min_pres : pint.Quantity or int
        Minimum pressure inside the pipe

    max_pres : pint.Quantity or int
        Maximum pressure inside the pipe

    design_pres : pint.Quantity or int
        Design pressure of the pipe

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

    min_flow : pint.Quantity or int
        Minimum flow rate through the pipe

    max_flow : pint.Quantity or int
        Maximum flow rate through the pipe

    design_flow : pint.Quantity or int
        Design flow rate through the pipe

    diameter : pint.Quantity or int
        Pipe diameter

    friction_coeff : int
        Friction coefficient for the pipe

    min_pressure : pint.Quantity or int
        Minimum pressure inside the pipe

    max_pressure : pint.Quantity or int
        Maximum pressure inside the pipe

    design_pressure : pint.Quantity or int
        Design pressure of the pipe

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
        design_flow,
        diameter=None,
        friction=None,
        min_pres=None,
        max_pres=None,
        design_pres=None,
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
        self.min_pressure = min_pres
        self.max_pressure = max_pres
        self.design_pressure = design_pres
        self.min_flow = min_flow
        self.max_flow = max_flow
        self.design_flow = design_flow
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
            f"<pype_schema.connection.Pipe id:{self.id} "
            f"contents:{self.contents} source:{self.source.id} "
            f"destination:{self.destination.id} "
            f"min_flow:{self.min_flow} max_flow:{self.max_flow} "
            f"design_flow:{self.design_flow} min_pressure:{self.min_pressure} "
            f"max_pressure:{self.max_pressure} "
            f"design_pressure:{self.design_pressure}"
            f"heating_values:{self.heating_values} "
            f"diameter:{self.diameter} friction_coeff:{self.friction_coeff} "
            f"tags:{self.tags} bidirectional:{self.bidirectional} "
            f"exit_point:{exit_point_id} entry_point:{entry_point_id}>\n"
        )

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            # don't attempt to compare against unrelated types
            return False

        return (
            self.id == other.id
            and self.contents == other.contents
            and self.source == other.source
            and self.destination == other.destination
            and self.diameter == other.diameter
            and self.friction_coeff == other.friction_coeff
            and self.min_pressure == other.min_pressure
            and self.max_pressure == other.max_pressure
            and self.design_pressure == other.design_pressure
            and self.heating_values == other.heating_values
            and self.min_flow == other.min_flow
            and self.max_flow == other.max_flow
            and self.design_flow == other.design_flow
            and self.tags == other.tags
            and self.bidirectional == other.bidirectional
            and self.exit_point == other.exit_point
            and self.entry_point == other.entry_point
        )

    def __lt__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        if self.diameter != other.diameter:
            return self.diameter < other.diameter
        elif self.min_flow != other.min_flow:
            return self.min_flow < other.min_flow
        elif self.max_flow != other.max_flow:
            return self.max_flow < other.max_flow
        elif self.design_flow != other.design_flow:
            return self.design_flow < other.design_flow
        elif self.friction_coeff != other.friction_coeff:
            return self.friction_coeff < other.friction_coeff
        elif self.min_pressure != other.min_pressure:
            return self.min_pressure < other.min_pressure
        elif self.max_pressure != other.max_pressure:
            return self.max_pressure < other.max_pressure
        elif self.design_pressure != other.design_pressure:
            return self.design_pressure < other.design_pressure
        elif self.heating_values != other.heating_values:
            return self.heating_values < other.heating_values
        elif self.contents != other.contents:
            return self.contents.value < other.contents.value
        elif self.bidirectional != other.bidirectional:
            return not self.bidirectional
        elif self.exit_point != self.exit_point:
            return self.exit_point < self.exit_point
        elif self.entry_point != self.entry_point:
            return self.entry_point < self.entry_point
        elif len(self.tags) < len(other.tags):
            return True
        elif len(self.tags) > len(other.tags):
            return False
        elif self.tags == other.tags:
            if self.source != other.source:
                # TODO: uncomment when node comparison are supported
                # if isinstance(self.source, type(other.source)):
                #     return self.source < other.source
                # else:
                return self.source.id < other.source.id
            elif self.destination != other.destination:
                # if isinstance(self.destination, type(other.destination)):
                #     return self.destination < other.destination
                # else:
                return self.destination.id < other.destination.id
            else:
                return self.id < other.id
        # case with same number of different tags, so we compare tags in order
        else:
            other_tags = [tag for _, tag in sorted(other.tags.items())]
            for i, tag in enumerate([tag for _, tag in sorted(self.tags.items())]):
                if tag != other_tags[i]:
                    return tag < other_tags[i]

    def set_flow_rate(self, min, max, design):
        """Set the minimum, maximum, and average flow rate through the connection

        Parameters
        ----------
        min : int
            Minimum flow rate through the connection

        max : int
            Maximum flow rate through the connection

        design : int
            Design flow rate through the connection
        """
        warnings.warn(
            "Please switch from `flow_rate` tuple to separate "
            + "`min_flow`, `max_flow` and `design_flow` attributes",
            DeprecationWarning,
        )
        self.flow_rate = (min, max, design)
        self._min_flow = min
        self._max_flow = max
        self._design_flow = design

    def get_min_flow(self):
        try:
            return self._min_flow
        except AttributeError:
            warnings.warn(
                "Please switch from `flow_rate` tuple to new `min_flow` attribute",
                DeprecationWarning,
            )
            return self.flow_rate[0]

    def set_min_flow(self, min_flow):
        self._min_flow = min_flow

    def del_min_flow(self):
        del self._min_flow
        if hasattr(self, "flow_rate"):
            self.flow_rate = (None, self.flow_rate[1], self.flow_rate[2])

    def get_max_flow(self):
        try:
            return self._max_flow
        except AttributeError:
            warnings.warn(
                "Please switch from `flow_rate` tuple to new `max_flow` attribute",
                DeprecationWarning,
            )
            return self.flow_rate[1]

    def set_max_flow(self, max_flow):
        self._max_flow = max_flow

    def del_max_flow(self):
        del self._max_flow
        if hasattr(self, "flow_rate"):
            self.flow_rate = (self.flow_rate[0], None, self.flow_rate[2])

    def get_design_flow(self):
        try:
            return self._design_flow
        except AttributeError:
            warnings.warn(
                "Please switch from `flow_rate` tuple to new `design_flow` attribute",
                DeprecationWarning,
            )
            return self.flow_rate[2]

    def set_design_flow(self, design_flow):
        self._design_flow = design_flow

    def del_design_flow(self):
        del self._design_flow
        if hasattr(self, "flow_rate"):
            self.flow_rate = (self.flow_rate[0], self.flow_rate[1], None)

    min_flow = property(get_min_flow, set_min_flow, del_min_flow)
    max_flow = property(get_max_flow, set_max_flow, del_max_flow)
    design_flow = property(get_design_flow, set_design_flow, del_design_flow)

    def set_pressure(self, min, max, design):
        """Set the minimum, maximum, and average pressure inside the connection

        Parameters
        ----------
        min : int
            Minimum pressure inside the connection

        max : int
            Maximum pressure inside the connection

        design : int
            Design pressure inside the connection
        """
        warnings.warn(
            "Please switch from `pressure` tuple to separate "
            + "`min_pressure`, `max_pressure` and `design_pressure` attributes",
            DeprecationWarning,
        )
        self.pressure = (min, max, design)
        self._min_pressure = min
        self._max_pressure = max
        self._design_pressure = design

    def get_min_pressure(self):
        try:
            return self._min_pressure
        except AttributeError:
            warnings.warn(
                "Please switch from `pressure` tuple to new `min_pressure` attribute",
                DeprecationWarning,
            )
            return self.pressure[0]

    def set_min_pressure(self, min_pressure):
        self._min_pressure = min_pressure

    def del_min_pressure(self):
        del self._min_pressure
        if hasattr(self, "pressure"):
            self.pressure = (None, self.pressure[1], self.pressure[2])

    def get_max_pressure(self):
        try:
            return self._max_pressure
        except AttributeError:
            warnings.warn(
                "Please switch from `pressure` tuple to new `max_pressure` attribute",
                DeprecationWarning,
            )
            return self.pressure[1]

    def set_max_pressure(self, max_pressure):
        self._max_pressure = max_pressure

    def del_max_pressure(self):
        del self._max_pressure
        if hasattr(self, "pressure"):
            self.pressure = (self.pressure[0], None, self.pressure[2])

    def get_design_pressure(self):
        try:
            return self._design_pressure
        except AttributeError:
            warnings.warn(
                "Please switch from `pressure` tuple to "
                + "new `design_pressure` attribute",
                DeprecationWarning,
            )
            return self.pressure[2]

    def set_design_pressure(self, design_pressure):
        self._design_pressure = design_pressure

    def del_design_pressure(self):
        del self._design_pressure
        if hasattr(self, "pressure"):
            self.pressure = (self.pressure[0], self.pressure[1], None)

    min_pressure = property(get_min_pressure, set_min_pressure, del_min_pressure)
    max_pressure = property(get_max_pressure, set_max_pressure, del_max_pressure)
    design_pressure = property(
        get_design_pressure, set_design_pressure, del_design_pressure
    )

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
    """A class for representing electrical connections.

    Parameters
    ---------
    id : str
        Wire ID

    source : Node
        Starting point of the connection

    destination : Node
        Endpoint of the connection

    tags : dict of Tag
        Data tags associated with this wire

    bidirectional : bool
        Whether electricity can flow from destination to source. False by default

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
        Contents moving through the connection.

    source : Node
        Starting point of the connection

    destination : Node
        Endpoint of the connection

    tags : dict of Tag
        Data tags associated with this pipe

    bidirectional : bool
        Whether electricity can flow from destination to source. False by default

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
            f"<pype_schema.connection.Wire id:{self.id} "
            f"contents:{self.contents} source:{self.source.id} "
            f"destination:{self.destination.id} "
            f"tags:{self.tags} bidirectional:{self.bidirectional} "
            f"exit_point:{exit_point_id} entry_point:{entry_point_id}>\n"
        )

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            # don't attempt to compare against unrelated types
            return False

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

    def __lt__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        if self.contents != other.contents:
            return self.contents.value < other.contents.value
        elif self.bidirectional != other.bidirectional:
            return not self.bidirectional
        elif self.exit_point != self.exit_point:
            return self.exit_point < self.exit_point
        elif self.entry_point != self.entry_point:
            return self.entry_point < self.entry_point
        elif len(self.tags) < len(other.tags):
            return True
        elif len(self.tags) > len(other.tags):
            return False
        elif self.tags == other.tags:
            if self.source != other.source:
                # TODO: uncomment when node comparison are supported
                # if isinstance(self.source, type(other.source)):
                #     return self.source < other.source
                # else:
                return self.source.id < other.source.id
            elif self.destination != other.destination:
                # if isinstance(self.destination, type(other.destination)):
                #     return self.destination < other.destination
                # else:
                return self.destination.id < other.destination.id
            else:
                return self.id < other.id
        # case with same number of different tags, so we compare tags in order
        else:
            other_tags = [tag for _, tag in sorted(other.tags.items())]
            for i, tag in enumerate([tag for _, tag in sorted(self.tags.items())]):
                if tag != other_tags[i]:
                    return tag < other_tags[i]


class Delivery(Connection):
    """A class to represent a connection via delivery,
    such as monthly chemical deliveries or weekly trash disposal.

    Parameters
    ---------
    id : str
        Delivery ID

    contents : ContentsType
        Contents moving through the connection

    source : Node
        Starting point of the connection

    destination : Node
        Endpoint of the connection

    frequency : pint.Quantity or float
        If a pint quantity it will be interpreted based on units.
        E.g., `0.25 days` will be interpreted as 0.25 days between deliveries,
        or in other words 4 deliveries per day.
        Whereas `0.25 / day` would indicate there is a quarter of a delivery per day,
        or more intuitively 4 days between each delivery.
        If unitless, assumed to be number of days between delivery

    tags : dict of Tag
        Data tags associated with this pump

    bidirectional : bool
        Whether deliveries are made from destination to source. False by default

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
        Contents moving through the connection.

    source : Node
        Starting point of the connection

    destination : Node
        Endpoint of the connection

    tags : dict of Tag
        Data tags associated with this pipe

    bidirectional : bool
        Whether deliveries are made from destination to source. False by default

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
        tags={},
        bidirectional=False,
        exit_point=None,
        entry_point=None,
    ):
        self.id = id
        self.contents = contents
        self.source = source
        self.destination = destination
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
            f"<pype_schema.connection.Wire id:{self.id} "
            f"contents:{self.contents} source:{self.source.id} "
            f"destination:{self.destination.id} "
            f"tags:{self.tags} bidirectional:{self.bidirectional} "
            f"exit_point:{exit_point_id} entry_point:{entry_point_id}>\n"
        )

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            # don't attempt to compare against unrelated types
            return False

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

    def __lt__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        if self.contents != other.contents:
            return self.contents.value < other.contents.value
        elif self.bidirectional != other.bidirectional:
            return not self.bidirectional
        elif self.exit_point != self.exit_point:
            return self.exit_point < self.exit_point
        elif self.entry_point != self.entry_point:
            return self.entry_point < self.entry_point
        elif len(self.tags) < len(other.tags):
            return True
        elif len(self.tags) > len(other.tags):
            return False
        elif self.tags == other.tags:
            if self.source != other.source:
                # TODO: uncomment when node comparison are supported
                # if isinstance(self.source, type(other.source)):
                #     return self.source < other.source
                # else:
                return self.source.id < other.source.id
            elif self.destination != other.destination:
                # if isinstance(self.destination, type(other.destination)):
                #     return self.destination < other.destination
                # else:
                return self.destination.id < other.destination.id
            else:
                return self.id < other.id
        # case with same number of different tags, so we compare tags in order
        else:
            other_tags = [tag for _, tag in sorted(other.tags.items())]
            for i, tag in enumerate([tag for _, tag in sorted(self.tags.items())]):
                if tag != other_tags[i]:
                    return tag < other_tags[i]
