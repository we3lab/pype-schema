from abc import ABC
from collections import OrderedDict


class Train:
    """A class representing a treatment train. Trains could be complementary,
    e.g. a biogas train and a wastewater treatment train,
    or multiple copies of the same processes built for redundancy

    Parameters
    ----------
    processes : OrderedDict of Process
        processes which make up this treatment train

    Attributes
    ----------
    processes : OrderedDict of Process
        processes which make up this treatment train
    """

    def __init__(self, processes=OrderedDict()):
        self.processes = processes

    def add_process(self, process):
        """Adds a process to the treatment train

        Parameters
        ----------
        process : Process
            Process object to add to the train
        """
        self.processes[process.id] = process

    def remove_process(self, process_name):
        """Removes a process from the treatment train

        Parameters
        ----------
        process_name : str
            name of process to remove
        """
        del self.processes[process_name]


class Process(ABC):
    """Abstract class for all unit processes

    Attributes
    ----------
    id : str
        Process ID

    contents : ContentsType
        Contents of the process (e.g. biogas or wastewater)

    flow_rate : tuple
        Tuple of minimum, maximum, and average process flow rate
    """
    id: str = NotImplemented
    contents: enums.ContentsType = NotImplemented

    def set_flow_rate(self, min, max, avg):
        """Set the minimum, maximum, and average flow rate of the process

        Parameters
        ----------
        min : int
            Minimum flow rate through the process

        max : int
            Maximum flow rate through the process

        avg : int
            Average flow rate through the process
        """
        # TODO: attach units to flow rate
        self.flow_rate = (min, max, avg)


class Digester(Process):
    """
    Parameters
    ----------
    id : str
        Process ID

    contents : ContentsType
        Contents of the digester

    min_flow : int
        Minimum flow rate through the process

    max_flow : int
        Maximum flow rate through the process

    avg_flow : int
        Average flow rate through the process

    volume : int
        Volume of the digester in cubic meters

    digester_type : DigesterType
        Type of digestion (aerobic or anaerobic)

    Attributes
    ----------
    id : str
        Process ID

    contents : ContentsType
        Contents of the digester

    flow_rate : tuple
        Tuple of minimum, maximum, and average digester flow rate

    volume : int
        Volume of the digester in cubic meters

    digester_type : DigesterType
        Type of digestion (aerobic or anaerobic)
    """

    def __init__(self, id, contents, min_flow, max_flow, avg_flow, volume, digester_type):
        self.id = id
        self.contents = contents
        self.volume = volume
        self.digester_type = digester_type
        self.set_flow_rate(min_flow, max_flow, avg_flow)


class Cogeneration(Process):
    """
    Parameters
    ----------
    id : str
        Cogenerator ID

    contents : ContentsType
        Contents of the digester

    min_flow : int
        Minimum generation capacity of a single cogenerator

    max_flow : int
        Maximum generation capacity of a single cogenerator

    avg_flow : int
        Average generation capacity of a single cogenerator

    units : int
        Number of cogenerator units running in parallel

    Attributes
    ----------
    id : str
        Cogenerator ID

    contents : ContentsType
        Contents of the cogenerator (biogas, natural gas, or a blend of the two)

    gen_capacity : tuple
        Minimum, maximum, and average generation capacity

    num_units : int
        Number of cogenerator units running in parallel
    """

    def __init__(self, id, contents, min_gen, max_gen, avg_gen, units):
        self.id = id
        self.contents = contents
        self.num_units = units
        self.set_gen_capacity(min_gen, max_gen, avg_gen)

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
        # TODO: attach units to generation capacity
        self.flow_rate = (min, max, avg)
