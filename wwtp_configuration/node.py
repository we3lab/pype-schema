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

    elevation : int
        Elevation of the node in meters above sea level

    tags : dict of Tag
        Data tags associated with this node
    """

    id: str = NotImplemented
    input_contents: utils.ContentsType = NotImplemented
    output_contents: utils.ContentsType = NotImplemented
    elevation: int = NotImplemented
    tags: dict = NotImplemented

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Node id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} "
            f"elevation:{self.elevation} tags:{self.tags}>"
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
        # TODO: attach units to flow rate
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

    tags : dict of Tag
        Data tags associated with this facility

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

    tags : dict of Tag
        Data tags associated with this facility

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
        tags={},
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.elevation = elevation
        self.trains = trains
        self.tags = tags
        self.set_flow_rate(min_flow, max_flow, avg_flow)

    def __repr__(self):
        return (
            f"<wwtp_configuration.node.Facility id:{self.id} "
            f"input_contents:{self.input_contents} "
            f"output_contents:{self.output_contents} elevation:{self.elevation} "
            f"trains:{self.trains} flow_rate:{self.flow_rate} tags:{self.tags}>"
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
            and self.trains == other.trains
            and self.flow_rate == other.flow_rate
            and self.tags == other.tags
        )

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

    def __init__(self, id, input_contents, output_contents, elevation, volume, tags={}):
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
            f"volume:{self.volume} tags:{self.tags}>"
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

    tags : dict of Tag
        Data tags associated with this pump

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
        elevation,
        horsepower,
        num_units,
        min_flow,
        max_flow,
        avg_flow=None,
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
            f"output_contents:{self.output_contents} elevation:{self.elevation} "
            f"horsepower:{self.horsepower} num_units:{self.num_units} "
            f"flow_rate:{self.flow_rate} tags:{self.tags}>"
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
