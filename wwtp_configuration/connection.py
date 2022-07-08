from abc import ABC
from . import enums
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
    contents: enums.ContentsType = NotImplemented
    source: node.Node = NotImplemented
    sink: node.Node = NotImplemented

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
    Paramters
    ---------
    id : str
        Pipe ID

    contents : ContentsType
        Contents moving through the node. Either WaterType, SolidsType, or GasType

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

    min_flow : int
        Minimum flow rate through the pipe

    max_flow : int
        Maximum flow rate through the pipe

    avg_flow : int
        Average flow rate through the pipe

    source : Node
        Starting point of the connection

    sink : Node
        Endpoint of the connection

    Attributes
    ----------
    id : str
        Pipe ID

    contents : ContentsType
        Contents moving through the node. Either WaterType, SolidsType, or GasType

    source : Node
        Starting point of the connection

    sink : Node
        Endpoint of the connection

    diameter : int
        Pipe diameter in meters

    friction_coeff : int
        Friction coefficient for the pipe

    pressure : tuple
        Minimum, maximum, and average pressure in the pipe

    flow_rate : tuple
        Minimum, maximum, and average flow rate through the pipe
    """

    def __init__(
        self,
        id,
        contents,
        diameter,
        friction,
        min_pres,
        max_pres,
        avg_pres,
        min_flow,
        max_flow,
        avg_flow,
        source=None,
        sink=None
    ):
        self.id = id
        self.contents = contents
        if source:
            self.source = source
        if sink:
            self.sink = sink
        self.diameter = diameter
        self.friction_coeff = friction
        self.set_pressure(min_pres, max_pres, avg_pres)
        self.set_flow_rate(min_flow, max_flow, avg_flow)
