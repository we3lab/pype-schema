import warnings
from enum import Enum, auto
from pandas import DataFrame, Series
import pandas as pd  # noqa: F401
import numpy as np  # noqa: F401
import scipy as sp  # noqa: F401
from numpy import ndarray, issubdtype
from .utils import count_args
from .units import u
from .operations import *  # noqa: F401, F403
from .logbook import Logbook


class TagType(Enum):
    """Enum to represent types of SCADA tags"""

    Flow = auto()  # flow through a connection
    Volume = auto()
    Level = auto()
    Pressure = auto()
    Temperature = auto()
    RunTime = auto()
    RunStatus = auto()
    VSS = auto()  # volatile suspended solids
    TSS = auto()  # total suspended solids
    TDS = auto()  # total dissolved solids
    COD = auto()  # chemical oxygen demand
    BOD = auto()  # biochemical oxygen demand
    pH = auto()
    Conductivity = auto()
    Turbidity = auto()
    Rotation = auto()
    Efficiency = auto()
    StateOfCharge = auto()
    InFlow = auto()  # flow into a node
    OutFlow = auto()  # flow out of a node
    NetFlow = auto()  # net flow through a node
    Speed = auto()
    Frequency = auto()
    Current = auto()
    Voltage = auto()
    Concentration = auto()
    SetPoint = auto()  # history of control set points


class DownsampleType(Enum):
    """Enum to represent common methods of downsampling data"""

    Average = auto()
    Decimation = auto()
    Reservoir = auto()


CONTENTLESS_TYPES = [
    TagType.RunTime,
    TagType.RunStatus,
    TagType.Rotation,
    TagType.Efficiency,
    TagType.Speed,
    TagType.Frequency,
]


def check_type_compatibility(tag_type, other_type):
    """Check if the given tag_type is compatible with another

    Parameters
    ----------
    tag_type : TagType
        Type of the first tag
    other_type : TagType
        Type of tag to compare against

    Returns
    -------
    bool
        True if compatible, False otherwise
    """
    if not isinstance(other_type, TagType):
        raise TypeError("tag_type must be a TagType object")

    flow_types = [TagType.Flow, TagType.InFlow, TagType.OutFlow, TagType.NetFlow]

    if tag_type in flow_types and other_type in flow_types:
        return True

    if tag_type == other_type:
        return True

    return False


class Tag:
    """Class to represent a SCADA or other data tag

    Parameters
    ----------
    id : str
        Tag ID

    units : str or Unit
        Units represented as a string or Pint unit.
        E.g., 'MGD' or 'cubic meters' or <Unit('MGD')>

    tag_type : TagType
        Type of data saved under the tag. E.g., `InfluentFlow` or `RunTime`

    source_unit_id : int or str
        integer representing unit number, or `total` if a combined data point
        across all units of the source node

    dest_unit_id : int or str
        integer representing unit number, or `total` if a combined data point
        across all units of the destination node.
        None if the Tag is associated with a Node object instead of a Connection

    parent_id : str
        ID for the parent object (either a Node or Connection)

    totalized : bool
        True if data is totalized. False otherwise

    contents : ContentsType
        Data stream contents. E.g., `WasteActivatedSludge` or `NaturalGas`

    manufacturer : str
        Name of the manufacturer for the physical sensor hardware. Default is None

    measure_freq : pint.Quantity
        Measurement frequency of the data with units. None by default

    report_freq : pint.Quantity
        Reporting frequency of the data with units. None by default

    downsample_method : DownsampleType
        None by default, meaning that data is reported on the same frequency as measured

    calibration : Logbook
        A history of sensor calibration.

    Attributes
    ----------
    id : str
        Tag ID

    units : Unit
        Units represented as a Pint unit. E.g., <Unit('MGD')>

    tag_type : TagType
        Type of data saved under the tag. E.g., `InfluentFlow` or `RunTime`

    source_unit_id : int or str
        integer representing unit number, or `total` if a combined data point
        across all units of the sources node

    dest_unit_id : int or str
        integer representing unit number, or `total` if a combined data point
        across all units of the destination node

    parent_id : str
        ID for the parent object (either a Node or Connection)

    totalized : bool
        True if data is totalized. False by default

    contents : ContentsType
        Contents moving through the node

    manufacturer : str
        Name of the manufacturer for the physical sensor hardware. Default is None

    measure_freq : pint.Quantity
        Measurement frequency of the data with units. None by default

    report_freq : pint.Quantity
        Reporting frequency of the data with units. None by default

    downsample_method : DownsampleType
        None by default, meaning that data is reported on the same frequency as measured

    calibration : Logbook
        A history of sensor calibration.
    """

    def __init__(
        self,
        id,
        units,
        tag_type,
        source_unit_id,
        dest_unit_id,
        parent_id,
        totalized=False,
        contents=None,
        manufacturer=None,
        measure_freq=None,
        report_freq=None,
        downsample_method=None,
        calibration=Logbook(),
    ):
        self.id = id
        self.units = units
        self.contents = contents
        self.tag_type = tag_type
        self.totalized = totalized
        self.source_unit_id = source_unit_id
        self.dest_unit_id = dest_unit_id
        self.parent_id = parent_id
        self.manufacturer = manufacturer
        # convert to Pint units if string value
        if isinstance(measure_freq, str):
            self.measure_freq = u.Quantity(measure_freq)
        else:
            self.measure_freq = measure_freq
        if isinstance(report_freq, str):
            self.report_freq = u.Quantity(report_freq)
        else:
            self.report_freq = report_freq
        self.downsample_method = downsample_method
        self.calibration = calibration

    def __repr__(self):
        return (
            f"<pype_schema.tag.Tag id:{self.id} units:{self.units} "
            f"tag_type:{self.tag_type} source_unit_id:{self.source_unit_id} "
            f"dest_unit_id:{self.dest_unit_id} parent_id:{self.parent_id} "
            f"totalized:{self.totalized} contents:{self.contents} "
            f"manufacturer:{self.manufacturer} measure_freq:{self.measure_freq} "
            f"report_freq:{self.report_freq} "
            f"downsample_method:{self.downsample_method} "
            f"calibration:{self.calibration}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.contents == other.contents
            and self.tag_type == other.tag_type
            and self.totalized == other.totalized
            and self.source_unit_id == other.source_unit_id
            and self.dest_unit_id == other.dest_unit_id
            and self.units == other.units
            and self.parent_id == other.parent_id
            and self.manufacturer == other.manufacturer
            and self.measure_freq == other.measure_freq
            and self.report_freq == other.report_freq
            and self.downsample_method == other.downsample_method
            and self.calibration == other.calibration
        )

    def __hash__(self):
        return hash(
            (
                self.id,
                self.contents,
                self.tag_type,
                self.totalized,
                self.source_unit_id,
                self.dest_unit_id,
                self.units,
                self.parent_id,
                self.manufacturer,
                self.measure_freq,
                self.report_freq,
                self.downsample_method,
                self.calibration,
            )
        )

    def __lt__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

        if self.id != other.id:
            return self.id < other.id
        elif self.contents != other.contents:
            return self.contents.value < other.contents.value
        elif self.tag_type != other.tag_type:
            return self.tag_type.value < other.tag_type.value
        elif self.totalized != other.totalized:
            return not self.totalized
        elif self.source_unit_id != other.source_unit_id:
            if self.source_unit_id == "total":
                return False
            elif other.source_unit_id == "total":
                return True
            else:
                return self.source_unit_id < other.source_unit_id
        elif self.dest_unit_id != other.dest_unit_id:
            if self.dest_unit_id == "total":
                return False
            elif other.dest_unit_id == "total":
                return True
            else:
                return self.dest_unit_id < other.dest_unit_id
        elif self.units != other.units:
            return str(self.units) < str(other.units)
        elif self.measure_freq != other.measure_freq:
            return self.measure_freq < other.measure_freq
        elif self.report_freq != other.report_freq:
            return self.report_freq < other.report_freq
        elif self.downsample_method != other.downsample_method:
            return self.downsample_method < other.downsample_method
        elif self.calibration != other.calibration:
            return len(self.calibration) < len(other.calibration)
        else:
            return self.parent_id < other.parent_id

    def get_manufacturer(self):
        try:
            return self._manufacturer
        except AttributeError:
            return None

    def set_manufacturer(self, manufacturer):
        self._manufacturer = manufacturer

    def del_manufacturer(self):
        del self._manufacturer

    manufacturer = property(get_manufacturer, set_manufacturer, del_manufacturer)

    def get_report_freq(self):
        try:
            return self._report_freq
        except AttributeError:
            return None

    def set_report_freq(self, report_freq):
        self._report_freq = report_freq

    def del_report_freq(self):
        del self._report_freq

    report_freq = property(get_report_freq, set_report_freq, del_report_freq)

    def get_measure_freq(self):
        try:
            return self._measure_freq
        except AttributeError:
            return None

    def set_measure_freq(self, measure_freq):
        self._measure_freq = measure_freq

    def del_measure_freq(self):
        del self._measure_freq

    measure_freq = property(get_measure_freq, set_measure_freq, del_measure_freq)

    def get_downsample_method(self):
        try:
            return self._downsample_method
        except AttributeError:
            return None

    def set_downsample_method(self, downsample_method):
        self._downsample_method = downsample_method

    def del_downsample_method(self):
        del self._downsample_method

    downsample_method = property(
        get_downsample_method, set_downsample_method, del_downsample_method
    )

    def get_calibration(self):
        try:
            return self._calibration
        except AttributeError:
            return Logbook()

    def set_calibration(self, calibration):
        self._calibration = calibration

    def del_calibration(self):
        del self._calibration

    calibration = property(get_calibration, set_calibration, del_calibration)

    def check_type_compatibility(self, other_type):
        """Check if the given tag_type is compatible with another

        Parameters
        ----------
        other_type : TagType
            Type of tag to compare against

        Returns
        -------
        bool
            True if compatible, False otherwise
        """
        return check_type_compatibility(self.tag_type, other_type)


class VirtualTag:
    """Representation for data that is not in the SCADA system, but is instead
    a combination of existing tags combined via the `operations` lambda function string

    Parameters
    ----------
    id : str
        VirtualTag ID

    tags : list of Tag
        List of Tag objects to combine

    operations : str
        String a lambda function to apply to all tags,
        must have number of args equal to number of tags

    tag_type : TagType
        Type of data saved under the tag. E.g., `InfluentFlow` or `RunTime`.
        Default is None, and it will be automatically determined from constituent
        Tags if they all have the same type.

    parent_id : str
        ID for the parent object (either a Node or Connection)

    contents : ContentsType
        Contents moving through the node. Default is None, and it will be automatically
        determined from consituent Tag contents

    Raises
    ------
    ValueError
        When `operations` lambda function has the wrong number of elements
        When `tag_type` is not specified and constituent tags have different types.
        When `contents` of the constituent tags are different types.

    UserWarning
        When a mix of totalized and detotalized tags are combined
        When tags have different units

    Attributes
    ----------
    id : str
        Tag ID

    tags : list of Tag
        List of Tag objects to combine

    operations :
        String giving a lambda function to apply to constituent tags

    units : str or Unit
        Units represented as a string or Pint unit.
        E.g., 'MGD' or 'cubic meters' or <Unit('MGD')>

    tag_type : TagType
        Type of data saved under the tag. E.g., `InfluentFlow` or `RunTime`

    totalized : bool
        True if data is totalized. False otherwise

    parent_id : str
        ID for the parent object (either a Node or Connection)

    contents : ContentsType
        Contents moving through the node
    """

    def __init__(
        self,
        id,
        tags,
        operations=None,
        units=None,
        tag_type=None,
        parent_id=None,
        contents=None,
    ):
        # TODO: inherit report_freq from child tags
        # TODO: incorporate DownsampleMethod for different report_freq
        self.id = id
        self.parent_id = parent_id
        self.tags = tags
        self.units = units

        units = []
        totalized = None

        determine_type = True if tag_type is None else False
        determine_contents = True if contents is None else False
        totalized_mix = False
        for tag in tags:
            units.append(tag.units)
            if totalized is not None and not totalized_mix:
                if totalized != tag.totalized:
                    warnings.warn(
                        "Tags should have the same value for 'totalized'. "
                        "Setting `totalized` to false under the assumption "
                        "that data has been cleaned and detotalized already."
                    )
                    totalized = False
                    totalized_mix = True
            else:
                totalized = tag.totalized

            if determine_type:
                if tag_type is not None:
                    if not check_type_compatibility(tag.tag_type, tag_type):
                        raise ValueError(
                            "All Tags must have the same value for 'tag_type'"
                        )
                else:
                    tag_type = tag.tag_type

            if determine_contents and tag_type not in CONTENTLESS_TYPES:
                if contents is not None:
                    if contents != tag.contents:
                        raise ValueError(
                            "All Tags must have the same value for 'contents'"
                        )
                else:
                    contents = tag.contents

        if tag_type in CONTENTLESS_TYPES:
            self.contents = None
        else:
            self.contents = contents
        self.tag_type = tag_type
        self.totalized = totalized

        if operations is not None and operations:
            if count_args(operations) != len(tags):
                raise ValueError(
                    "Operations lambda function must have the same "
                    "number of arguments as the Tag list"
                )
        elif len(tags) > 1:
            raise ValueError(
                "Operations lambda function must be specified "
                "if multiple tags are given"
            )

        self.operations = operations

    def __repr__(self):
        return (
            f"<pype_schema.tag.VirtualTag id:{self.id} units:{self.units} "
            f"tag_type:{self.tag_type} totalized:{self.totalized} "
            f"contents:{self.contents} tags:{[tag.id for tag in self.tags]} "
            f"operations:{self.operations} "
            f"parent_id:{self.parent_id}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return False

        return (
            self.id == other.id
            and self.contents == other.contents
            and self.tag_type == other.tag_type
            and self.totalized == other.totalized
            and self.units == other.units
            and self.tags == other.tags
            and self.operations == other.operations
        )

    def __hash__(self):
        return hash(
            (
                self.id,
                str(self.tags),
                str(self.operations),
                self.contents,
                self.tag_type,
                self.totalized,
                self.units,
            )
        )

    def __lt__(self, other):
        if isinstance(other, Tag):
            return False
        elif not isinstance(other, self.__class__):
            raise NotImplementedError
        elif len(self.tags) < len(other.tags):
            return True
        elif len(self.tags) > len(other.tags):
            return False
        elif self.operations != other.operations:
            return self.operations < other.operations
        elif self.id != other.id:
            return self.id < other.id
        elif self.contents != other.contents:
            return self.contents.value < other.contents.value
        elif self.tag_type != other.tag_type:
            return self.tag_type.value < other.tag_type.value
        elif self.totalized != other.totalized:
            return other.totalized
        else:
            return str(self.units) < str(other.units)

    def process_ops(self, data, tag_to_var_map={}):
        """Transform the given data according to the VirtualTag's lambda string

        Parameters
        ----------
        data : list, array, dict, or DataFrame
            a list, numpy array, or pandas DataFrame of data that has the
            correct dimensions. I.e., the number of columns is one more than
            binary operations and same length as unary operations

        tag_to_var_map : dict
            dictionary of the form { tag.id : variable_name } for using data files
            that differ from the original SCADA tag naming system

        Returns
        -------
        list, array, or Series
            numpy array of combined dataset
        """
        result = data.copy()
        num_ops = count_args(self.operations)
        func_ = eval(self.operations)
        if isinstance(data, list):
            if num_ops == len(data):
                result = func_(*[data_ for data_ in data])
            else:
                raise ValueError(
                    "Data must have the correct dimensions "
                    "(same length as unary operations). "
                    "Currently there are {} unary operations and {} data tags".format(
                        num_ops, len(data)
                    )
                )
        elif isinstance(data, ndarray):
            if issubdtype(data.dtype, (int)):
                result = result.astype("float")
            if num_ops == data.shape[1]:
                result = func_(*[data[:, i] for i in range(data.shape[1])])
            else:
                raise ValueError(
                    "Data must have the correct dimensions "
                    "(same length as number of args in operations lambda function). "
                    "Currently there are {} args and {} data tags".format(
                        num_ops, data.shape[1]
                    )
                )
        elif isinstance(data, (dict, DataFrame)):
            varnames = []
            for tag_obj in self.tags:
                varname = tag_to_var_map[tag_obj.id] if tag_to_var_map else tag_obj.id
                varnames.append(varname)
                if isinstance(tag_obj, self.__class__):
                    data[varname] = tag_obj.calculate_values(data)
            result = func_(*[data[varname] for varname in varnames])
            if isinstance(result, Series):
                result.rename(self.id, inplace=True)

        else:
            raise TypeError("Data must be either a list, array, dict, or DataFrame")

        return result

    def calculate_values(self, data, tag_to_var_map={}):
        """Combine the given data according to the VirtualTag's operations

        Parameters
        ----------
        data : list, array, dict, or DataFrame
            a list, numpy array, or pandas DataFrame of data that has the
            correct dimensions. I.e., the number of columns is one more than
            binary operations and same length as unary operations

        tag_to_var_map : dict
            dictionary of the form { tag.id : variable_name } for using data files
            that differ from the original SCADA tag naming system

        Returns
        -------
        list, array, or Series
            numpy array of combined dataset
        """
        if self.operations is not None and self.operations:
            data = self.process_ops(data, tag_to_var_map=tag_to_var_map)
        elif isinstance(data, (dict, DataFrame)):
            # if ops, get appropriate column and rename
            data = data[self.tags[0].id].rename(self.id)
        elif isinstance(data, ndarray):
            # flatten array since operations do that automatically
            data = data[:, 0]

        return data
