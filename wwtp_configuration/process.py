from abc import ABC
from collections import OrderedDict
from . import utils


class Train:
    """A class representing a treatment train. Trains could be complementary,
    e.g. a biogas train and a wastewater treatment train,
    or multiple copies of the same processes built for redundancy

    Parameters
    ----------
    id : str
        Train ID

    processes : OrderedDict of Process or Pump
        processes and pummps which make up this treatment train

    Attributes
    ----------
    id : str
        Train ID

    processes : OrderedDict of Process
        processes which make up this treatment train
    """

    def __init__(self, id, processes=OrderedDict()):
        self.id = id
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

    input_contents : ContentsType or list of ContentsType
        Contents entering the process (e.g. biogas or wastewater)

    output_contents : ContentsType or list of ContentsType
        Contents leaving the process (e.g. biogas or wastewater)

    flow_rate : tuple
        Tuple of minimum, maximum, and average process flow rate

    num_units : int
        Number of processes running in parallel

    tags : dict of Tag
        Data tags associated with this process
    """

    id: str = NotImplemented
    input_contents: utils.ContentsType = NotImplemented
    output_contents: utils.ContentsType = NotImplemented
    num_units: int = NotImplemented
    tags: dict = NotImplemented

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

    def add_tag(self, tag):
        """Adds a tag to the process

        Parameters
        ----------
        tag : Tag
            Tag object to add to the process
        """
        self.tags[tag.id] = tag

    def remove_tag(self, tag_name):
        """Removes a tag from the process

        Parameters
        ----------
        tag_name : str
            name of tag to remove
        """
        del self.tags[tag_name]


class Digestion(Process):
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

    flow_rate : tuple
        Tuple of minimum, maximum, and average digester flow rate

    num_units : int
        Number of digesters running in parallel

    volume : int
        Volume of the digester in cubic meters

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
        tags={}
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.num_units = num_units
        self.volume = volume
        self.digester_type = digester_type
        self.tags = tags
        self.set_flow_rate(min_flow, max_flow, avg_flow)


class Cogeneration(Process):
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
        Contents entering the cogenerator (biogas, natural gas, or a blend of the two)

    gen_capacity : tuple
        Minimum, maximum, and average generation capacity

    num_units : int
        Number of cogenerator units running in parallel

    tags : dict of Tag
        Data tags associated with this cogenerator
    """

    def __init__(self, id, input_contents, min_gen, max_gen, avg_gen, num_units, tags={}):
        self.id = id
        self.input_contents = input_contents
        self.num_units = num_units
        self.tags = tags
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


class Clarification(Process):
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

    flow_rate : tuple
        Minimum, maximum, and average flow rate

    num_units : int
        Number of clarifiers running in parallel

    volume : int
        Volume of a single clarifier in cubic meters

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
        tags={}
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.num_units = num_units
        self.volume = volume
        self.tags = tags
        self.set_flow_rate(min_flow, max_flow, avg_flow)


class Filtration(Process):
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

    flow_rate : tuple
        Minimum, maximum, and average flow rate

    num_units : int
        Number of filters running in parallel

    volume : int
        Volume of a single filter in cubic meters

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
        tags={}
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.num_units = num_units
        self.volume = volume
        self.tags = tags
        self.set_flow_rate(min_flow, max_flow, avg_flow)


class Thickener(Process):
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

    flow_rate : tuple
        Minimum, maximum, and average flow rate

    num_units : int
        Number of thickeners running in parallel

    volume : int
        Volume of a single thickener in cubic meters

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
        tags={}
    ):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.num_units = num_units
        self.volume = volume
        self.tags = tags
        self.set_flow_rate(min_flow, max_flow, avg_flow)


class Aeration(Process):
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

    flow_rate : tuple
        Minimum, maximum, and average flow rate

    num_units : int
        Number of aeration basins running in parallel

    volume : int
        Volume of a single aeration basin in cubic meters

    tags : dict of Tag
        Data tags associated with this aerator
    """

    def __init__(self, id, input_contents, output_contents, min_flow, max_flow, avg_flow, num_units, volume, tags={}):
        self.id = id
        self.input_contents = input_contents
        self.output_contents = output_contents
        self.num_units = num_units
        self.volume = volume
        self.tags = tags
        self.set_flow_rate(min_flow, max_flow, avg_flow)


class Flare(Process):
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

    def __init__(self, id, num_units, volume, tags={}):
        self.id = id
        self.input_contents = utils.GasType.Biogas
        self.num_units = num_units
        self.tags = tags
