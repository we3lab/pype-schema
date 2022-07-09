from abc import ABC
from . import helper


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

    elevation : int
        Elevation of the node in meters above sea level
    """

    id: str = NotImplemented
    input_contents: helper.ContentsType = NotImplemented
    output_contents: helper.ContentsType = NotImplemented
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

    trains : dict of Train
        Treatment trains that make up this facility

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

    trains : dict of Train
        Treatment trains that make up this facility

    flow_rate : tuple
        Tuple of minimum, maximum, and average facility flow rate
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
        trains={},
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.elevation = elevation
        self.trains = trains
        self.set_flow_rate(min_flow, max_flow, avg_flow)

    def add_train(self, train):
        """Adds a node to the network

        Parameters
        ----------
        train : Train
            Train object to add to the network
        """
        self.trains[train.id] = train

    def remove_train(self, train_name):
        """Removes a node from the network

        Parameters
        ----------
        train_name : str
            name of node to remove

        Raises
        ------
        KeyError
            if `train_name` is not found
        """
        del self.trains[train_name]


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
    """

    def __init__(self, id, input_contents, output_contents, elevation, volume):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.elevation = elevation
        self.volume = volume


class Pump(Node):
    """
    Parameters
    ----------
    id : str
        Pump ID

    input_contents : ContentsType
        Contents entering the pump.

    output_contents : ContentsType
        Contents leaving the pump.

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

    Attributes
    ----------
    id : str
        Pump ID

    input_contents : ContentsType
        Contents entering the pump.

    output_contents : ContentsType
        Contents leaving the pump.

    elevation : int
        Elevation of the pump in meters above sea level

    horsepower : int
        Horsepower of a single pump

    num_units : int
        Number of pumps running in parallel

    flow_rate : tuple
        Tuple of minimum, maximum, and average pump flow rate

    energy_efficiency : function
        Function which takes in the current flow rate and returns the energy
        required to pump at that rate
    """

    def __init__(
        self,
        id,
        input_contents,
        output_contents,
        elevation,
        horsepower,
        num_units,
        min_flow,
        max_flow,
        avg_flow=None,
        pump_type=helper.PumpType.Constant,
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.elevation = elevation
        self.pump_type = pump_type
        self.horsepower = horsepower
        self.num_units = num_units
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
