from abc import ABC
from . import enums


class Node(ABC):
    """Abstract class for all nodes

    Attributes
    ----------
    id : str
        Node ID

    contents : ContentsType
        Contents moving through the node. Either WaterType, SolidsType, or GasType

    elevation : int
        Elevation of the node in meters above sea level
    """
    id: str = NotImplemented
    contents: enums.ContentsType = NotImplemented
    elevation: int = NotImplemented

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
        # TODO: attach units to flow rate
        self.flow_rate = (min, max, avg)


class Facility(Node):
    """
    Parameters
    ----------
    id : str
        Facility ID

    contents : ContentsType
        Contents of the facility

    elevation : int
        Elevation of the facility

    min_flow : int
        Minimum flow rate through the facility

    max_flow : int
        Maximum flow rate through the facility

    avg_flow : int
        Average flow rate through the facility

    trains : dict of Train
        Treatment trains that make up this facility

    Attributes
    ----------
    id : str
        Facility ID

    contents : ContentsType
        Contents of the facility

    elevation : int
        Elevation of the facility in meters above sea level

    trains : dict of Train
        Treatment trains that make up this facility

    flow_rate : tuple
        Tuple of minimum, maximum, and average pump flow rate
    """

    def __init__(self, id, contents, elevation, min_flow, max_flow, avg_flow, trains={}):
        self.id = id
        self.contents = contents
        self.elevation = elevation
        self.trains = trains
        self.set_flow_rate(min_flow, max_flow, avg_flow)


class Tank(Node):
    """
    Parameters
    ----------
    id : str
        Tank ID

    contents : ContentsType
        Contents of the tank

    elevation : int
        Elevation of the tank in meters above sea level

    volume : int
        Volume of the tank in cubic meters

    Attributes
    ----------
    id : str
        Tank ID

    contents : ContentsType
        Contents of the tank

    elevation : int
        Elevation of the tank in meters above sea level

    volume : int
        Volume of the tank in cubic meters
    """

    def __init__(self, id, contents, elevation, volume):
        self.id = id
        self.contents = contents
        self.elevation = elevation
        self.volume = volume


class Pump(Node):
    """
    Parameters
    ----------
    id : str
        Pump ID

    contents : ContentsType
        Contents being pumped

    elevation : int
        Elevation of the pump in meters above sea level

    min_flow : int
        Minimum flow rate supplied by the pump

    max_flow : int
        Maximum flow rate supplied by the pump

    avg_flow : int
        Average flow rate supplied by the pump

    pump_type : PumpType
        Type of pump (either VFD or constant)

    Attributes
    ----------
    id : str
        Pump ID

    contents : ContentsType
        Contents being pumped

    elevation : int
        Elevation of the pump in meters above sea level

    flow_rate : tuple
        Tuple of minimum, maximum, and average pump flow rate
    """

    def __init__(
        self,
        id,
        contents,
        elevation,
        min_flow,
        max_flow,
        avg_flow=None,
        pump_type=enums.PumpType.Constant,
    ):
        self.id = id
        self.contents = contents
        self.elevation = elevation
        self.pump_type = pump_type
        self.set_flow_rate(min_flow, max_flow, avg_flow)

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
