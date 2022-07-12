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

    sink : Node
        Endpoint of the connection

    pressure : tuple
        Minimum, maximum, and average pressure in the pipe

    flow_rate : tuple
        Minimum, maximum, and average flow rate through the pipe
    """

    id: str = NotImplemented
    contents: utils.ContentsType = NotImplemented
    source: node.Node = NotImplemented
    sink: node.Node = NotImplemented
    tags: dict = NotImplemented

    def __repr__(self):
        return f"<wwtp_configuration.connection.Connection id:{self.id} contents:{self.contents} source:{self.source} sink:{self.sink} tags:{self.tags}>"

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
        # TODO: attach units to flow rate
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
        # TODO: attach units to flow rate
        self.pressure = (min, max, avg)


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

    sink : Node
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

    Attributes
    ----------
    id : str
        Pipe ID

    contents : ContentsType
        Contents moving through the connection.

    source : Node
        Starting point of the connection

    sink : Node
        Endpoint of the connection

    flow_rate : tuple
        Minimum, maximum, and average flow rate through the pipe

    diameter : int
        Pipe diameter in meters

    friction_coeff : int
        Friction coefficient for the pipe

    pressure : tuple
        Minimum, maximum, and average pressure in the pipe
    """

    def __init__(
        self,
        id,
        contents,
        source,
        sink,
        min_flow,
        max_flow,
        avg_flow,
        diameter=None,
        friction=None,
        min_pres=None,
        max_pres=None,
        avg_pres=None,
    ):
        self.id = id
        self.contents = contents
        self.source = source
        self.sink = sink
        self.diameter = diameter
        self.friction_coeff = friction
        self.set_pressure(min_pres, max_pres, avg_pres)
        self.set_flow_rate(min_flow, max_flow, avg_flow)

    def __repr__(self):
        return f"<wwtp_configuration.connection.Pipe id:{self.id} contents:{self.contents} source:{self.source} sink:{self.sink} flow_rate:{self.flow_rate} pressure:{self.pressure} diameter:{self.diameter} friction_coeff:{self.friction_coeff}  tags:{self.tags}>"

    def __eq__(self, other):
        if not isinstance(other, Pipe):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return (
            self.id == other.id
            and self.contents == other.contents
            and self.source == other.source
            and self.sink == other.sink
            and self.diameter == other.diameter
            and self.friction_coeff == other.friction_coeff
            and self.pressure == other.pressure
            and self.flow_rate == other.flow_rate
        )
