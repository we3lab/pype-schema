import warnings
from enum import Enum, auto
from pandas import DataFrame, Series
import pandas as pd  # noqa: F401
import numpy as np  # noqa: F401
import scipy as sp  # noqa: F401
from numpy import ndarray, array, issubdtype
from .utils import count_args, parse_units
from .units import u
from .operations import *  # noqa: F401, F403
from .logbook import Logbook
from .operations import Constant


UNARY_OPS = ["noop", "delta", "<<", ">>", "~", "-"]
BINARY_OPS = ["+", "-", "*", "/"]


class TagType(Enum):
    """Enum to represent types of SCADA tags."""

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
    """Enum to represent common methods of downsampling data."""

    Average = auto()
    Decimation = auto()
    Reservoir = auto()


class OperationMode(Enum):
    """Enum to represent methods of VirtualTag operations."""

    Algebraic = auto()
    Custom = auto()


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
    a combination of existing tags.

    Tags are combined via either `custom_operations` lambda function string or the
    `unary_operations` and `binary_operations` lists depending on whether
    `mode` is `Algebraic` or `Custom`.

    In `Algebraic` mode, all unary operations are applied before any binary operations.

    Parameters
    ----------
    id : str
        VirtualTag ID

    tags : list of Tag
        List of Tag objects to combine

    unary_operations : str or list
        Function to apply when combining tags.
        If a single string it will be applied to all Tags.
        Otherwise, the `unary_operations` must be same length as `tags`,
        and functions will be applied in order

    binary_operations : str or list
        Function to apply when combining tags.
        If a single string it will be applied to all Tags.
        Otherwise, the `binary_operations` must be one shorter than `tags`,
        and functions will be applied in order

    custom_operations : str
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

    unary_operations : ["noop", "delta", "<<", ">>", "~", "-"]
        Unary operations to apply before combining tags.

            "noop" : null operator, useful when
            skipping tags in a list of unary operations.

            "delta" : calculate the difference between
            the current timestep and previous timestep

            "<<" : shift all data left one timestep,
            so that the last time step will be NaN

            ">>" : shift all data right one timestep,
            so that the first time step will be NaN

            "~" : Boolean not

            "-" : unary negation

        Note that "delta", "<<", and ">>" return a timeseries padded
        with NaN so that it is the same length as input data

    binary_operations : ["+", "-", "*", "/"]
        Binary operaitons to apply when combining tags.
        Supported functions are "+", "-", "*", and "/".
        If a single string is passed, it will be applied to all Tags.
        Otherwise, the `binary_operations` list must be one shorter than `tags`,
        and functions will be applied in order from left to right

    custom_operations : str
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

    mode : OperationMode
        Mode of operation. Either `Algebraic` or `Custom`.
        Automatically determined based on values of `unary_operations`,
        `binary_operations` and `custom_operations`.
    """

    def __init__(
        self,
        id,
        tags,
        unary_operations=None,
        binary_operations=None,
        custom_operations=None,
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
        self.num_constants = sum([isinstance(tag, Constant) for tag in self.tags])

        # determine OperationMode
        if (unary_operations is not None) or (binary_operations is not None):
            if custom_operations is not None:
                raise ValueError(
                    "`custom_operations` cannot be used with binary "
                    "and unary operations. I.e., select either "
                    "`OperationMode.Algebraic` or `OperationMode.Custom`."
                )
            else:
                self.mode = OperationMode.Algebraic
                self.custom_operations = None
        elif custom_operations is not None:
            self.mode = OperationMode.Custom
            self.unary_operations = None
            self.binary_operations = None
        else:
            raise ValueError(
                "At least one of `unary_operations`, `binary_operations`, "
                "and `custom_operations` must be provided."
            )

        unit_list = []
        totalized = None

        determine_type = True if tag_type is None else False
        determine_contents = True if contents is None else False
        totalized_mix = False
        for tag in tags:
            if not isinstance(tag, Constant):
                unit_list.append(tag.units)
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

        if self.mode == OperationMode.Algebraic:
            if isinstance(unary_operations, list):
                if len(unary_operations) != len(tags):
                    raise ValueError(
                        "`unary_operations` must be same length as Tag list"
                    )
                else:
                    for i, unit in enumerate(unit_list):
                        if isinstance(unary_operations[i], list):
                            for j in range(len(unary_operations[i])):
                                if unary_operations[i][j] not in UNARY_OPS:
                                    raise ValueError(
                                        "Unsupported unary operator:",
                                        unary_operations[i],
                                    )
                                elif unary_operations[i][j] == "~":
                                    unit_list[i] = None
                                elif unary_operations[i][j] == "delta":
                                    # TODO: convert from volume to flow rate
                                    # once resolution argument exists
                                    pass
                        else:
                            if unary_operations[i] not in UNARY_OPS:
                                raise ValueError(
                                    "Unsupported unary operator:", unary_operations[i]
                                )
                            elif unary_operations[i] == "~":
                                unit_list[i] = None
                            elif unary_operations[i] == "delta":
                                # TODO: convert from volume to flow rate
                                # once resolution argument exists
                                pass
                self.unary_operations = unary_operations
            elif unary_operations is not None:
                if unary_operations not in UNARY_OPS:
                    raise ValueError("Unsupported unary operator:", unary_operations)
                self.unary_operations = [unary_operations] * (len(self.tags))
            else:
                self.unary_operations = None

            if isinstance(binary_operations, list):
                if len(binary_operations) != len(tags) - 1:
                    raise ValueError(
                        "`binary_operations` must be of length one less than Tag list"
                    )
                else:
                    self.binary_operations = binary_operations
                    prev_unit = None
                    for i, unit in enumerate(unit_list):
                        if isinstance(unit, str):
                            unit = parse_units(unit)

                        if prev_unit is not None:
                            # check that operation is supported
                            if binary_operations[i - 1] not in BINARY_OPS:
                                raise ValueError(
                                    "Unsupported binary operator:",
                                    binary_operations[i - 1],
                                )
                            prev_unit = binary_helper(  # noqa: F405
                                binary_operations[i - 1],
                                unit,
                                prev_unit,
                                totalized_mix=totalized_mix,
                            )
                        else:
                            prev_unit = unit
            elif binary_operations is not None:
                if binary_operations not in BINARY_OPS:
                    raise ValueError("Unsupported binary operator:", binary_operations)
                prev_unit = None
                for unit in unit_list:
                    if isinstance(unit, str):
                        unit = parse_units(unit)

                    if prev_unit is not None:
                        prev_unit = binary_helper(  # noqa: F405
                            binary_operations,
                            unit,
                            prev_unit,
                            totalized_mix=totalized_mix,
                        )
                    else:
                        prev_unit = unit

                self.binary_operations = [binary_operations] * (len(self.tags) - 1)
            else:
                if len(self.tags) != 1:
                    raise ValueError(
                        "Binary operations must be specified "
                        "when more than one tag is given."
                    )
                self.binary_operations = None
                prev_unit = unit_list[0]

            # only overwrite if user did not define units
            if self.units is None:
                self.units = prev_unit

        elif self.mode == OperationMode.Custom:
            if custom_operations is not None and custom_operations:
                if count_args(custom_operations) != len(tags):
                    raise ValueError(
                        "Operations lambda function must have the same "
                        "number of arguments as the Tag list"
                    )
            elif len(tags) > 1:
                raise ValueError(
                    "Operations lambda function must be specified "
                    "if multiple tags are given"
                )

            self.custom_operations = custom_operations
        else:
            raise ValueError(
                f"{self.mode} not currently supported. "
                "Select either `OperationMode.Algebraic` or `OperationMode.Custom`."
            )

    def __repr__(self):
        return (
            f"<pype_schema.tag.VirtualTag id:{self.id} units:{self.units} "
            f"tag_type:{self.tag_type} totalized:{self.totalized} "
            f"contents:{self.contents} tags:{[tag.id for tag in self.tags]} "
            f"unary_operations:{self.unary_operations} "
            f"binary_operations:{self.binary_operations} "
            f"custom_operations:{self.custom_operations} "
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
            and self.unary_operations == other.unary_operations
            and self.binary_operations == other.binary_operations
            and self.custom_operations == other.custom_operations
        )

    def __hash__(self):
        return hash(
            (
                self.id,
                str(self.tags),
                str(self.unary_operations),
                str(self.binary_operations),
                str(self.custom_operations),
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
        elif self.unary_operations != other.unary_operations:
            try:
                return self.unary_operations < other.unary_operations
            except TypeError:  # list of list of operations leads to error
                flattened_self_ops = [
                    item for sublist in self.unary_operations for item in sublist
                ]
                flattened_other_ops = [
                    item for sublist in other.unary_operations for item in sublist
                ]
                return flattened_self_ops < flattened_other_ops
        elif self.binary_operations != other.binary_operations:
            return self.binary_operations < other.binary_operations
        elif self.custom_operations != other.custom_operations:
            return self.custom_operations < other.custom_operations
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

    def process_unary_ops(self, data, tag_to_var_map={}):
        """Transform the given data according to the VirtualTag's unary operator

        Parameters
        ----------
        data : list, array, dict, or DataFrame
            a list, numpy array, or pandas DataFrame of data that has the
            correct dimensions. I.e., the number of columns is one more than
            binary operations and same length as unary operations

        un_op : ["noop", "delta", "<<", ">>", "~", "-"]
            Supported operations are:

                "noop" : null operator, useful when
                skipping tags in a list of unary operations.

                "delta" : calculate the difference between
                the current timestep and previous timestep

                "<<" : shift all data left one timestep,
                so that the last time step will be NaN

                ">>" : shift all data right one timestep,
                so that the first time step will be NaN

                "~" : Boolean not

                "-" : unary negation

            Note that "delta", "<<", and ">>" return a timeseries padded
            with NaN so that it is the same length as input data

        tag_to_var_map : dict
            dictionary of the form { tag.id : variable_name } for using data files
            that differ from the original SCADA tag naming system

        Returns
        -------
        list, array, or Series
            numpy array of combined dataset
        """
        constant_count = 0
        num_ops = len(self.unary_operations)
        if isinstance(data, list):
            if num_ops != len(data) + self.num_constants:
                raise ValueError(
                    "Data must have the correct dimensions "
                    "(same length as unary operations). "
                    "Currently there are {} unary operations and {} data tags".format(
                        num_ops, len(data)
                    )
                )
            else:
                result = data.copy()
                for i in range(num_ops):
                    if isinstance(self.tags[i], Constant):
                        constant_count += 1
                        relevant_data = (
                            np.ones(len(data[0])) * self.tags[i].value
                        ).tolist()
                        # ensure that result is of the correct length
                        # the value will be overwritten
                        result.append(relevant_data)
                        result[i] = unary_helper(  # noqa: F405
                            relevant_data, self.unary_operations[i]
                        )
                    else:
                        result[i] = unary_helper(  # noqa: F405
                            data[i - constant_count], self.unary_operations[i]
                        )
        elif isinstance(data, ndarray):
            if num_ops != data.shape[1] + self.num_constants:
                raise ValueError(
                    "Data must have the correct dimensions "
                    "(same length as unary operations). "
                    "Currently there are {} unary operations and {} data tags".format(
                        len(self.unary_operations), data.shape[1]
                    )
                )
            else:
                result = np.zeros((len(data[:, 0]), num_ops))
                if issubdtype(data.dtype, (int)):
                    result = result.astype("float")
                for i in range(num_ops):
                    if isinstance(self.tags[i], Constant):
                        relevant_data = np.ones(len(data[:, 0])) * self.tags[i].value
                        result[:, i] = unary_helper(  # noqa: F405
                            relevant_data, self.unary_operations[i]
                        )
                        constant_count += 1
                    else:
                        result[:, i] = unary_helper(  # noqa: F405
                            data[:, i - constant_count], self.unary_operations[i]
                        )
        elif isinstance(data, (dict, DataFrame)):
            result = data.copy()
            for i, tag_obj in enumerate(self.tags):
                if isinstance(tag_obj, Constant):
                    if isinstance(data, dict):
                        first_key = next(iter(data))
                        relevant_data = np.ones(len(data[first_key])) * tag_obj.value
                    else:  # must be a DataFrame
                        relevant_data = pd.Series([tag_obj.value] * len(data))
                elif isinstance(tag_obj, self.__class__):
                    relevant_data = tag_obj.calculate_values(data, tag_to_var_map)
                elif tag_to_var_map:
                    relevant_data = result[tag_to_var_map[tag_obj.id]]
                else:
                    relevant_data = result[tag_obj.id]

                is_series = isinstance(relevant_data, pd.Series)
                if is_series:  # store info, then convert to np array
                    original_index = relevant_data.index
                    original_name = relevant_data.name
                    relevant_data = relevant_data.values

                processed_relevant_data = unary_helper(  # noqa: F405
                    relevant_data, self.unary_operations[i]
                )

                # Convert back if original was Series
                if is_series:
                    relevant_data = pd.Series(
                        processed_relevant_data,
                        index=original_index,
                        name=original_name,
                    )
                else:
                    relevant_data = processed_relevant_data

                if tag_to_var_map:
                    result[tag_to_var_map[tag_obj.id]] = relevant_data
                else:
                    result[tag_obj.id] = relevant_data
        else:
            raise TypeError("Data must be either a list, array, dict, or DataFrame")

        return result

    def process_binary_ops(self, data, tag_to_var_map={}):
        """Combine the given data according to the VirtualTag's binary operations

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
        constant_count = 0
        # if there are unary operations, then constants have alrady been added to data
        if self.unary_operations is not None:
            num_constants = 0
        else:
            num_constants = self.num_constants
        if isinstance(data, list):
            if len(self.binary_operations) != len(data) + num_constants - 1:
                raise ValueError(
                    "Data must have the correct dimensions "
                    "(one more element than binary operations). "
                    "Currently there are {} binary operations and {} data tags".format(
                        len(self.binary_operations), len(data)
                    )
                )
            else:
                arr = array(data)
                if isinstance(self.tags[0], Constant) and num_constants != 0:
                    constant_count += 1
                    result = (np.ones(arr.shape[1]) * self.tags[0].value).tolist()
                else:
                    result = data.copy()[0]
                for i in range(arr.shape[0] + num_constants - 1):
                    if isinstance(self.tags[i + 1], Constant) and num_constants != 0:
                        constant_count += 1
                        if self.binary_operations[i] == "+":
                            for j in range(arr.shape[1]):
                                result[j] = result[j] + self.tags[i + 1].value
                        elif self.binary_operations[i] == "-":
                            for j in range(arr.shape[1]):
                                result[j] = result[j] - self.tags[i + 1].value
                        elif self.binary_operations[i] == "*":
                            for j in range(arr.shape[1]):
                                result[j] = result[j] * self.tags[i + 1].value
                        elif self.binary_operations[i] == "/":
                            for j in range(arr.shape[1]):
                                result[j] = result[j] / self.tags[i + 1].value
                    else:
                        if self.binary_operations[i] == "+":
                            for j in range(arr.shape[1]):
                                result[j] = result[j] + data[i - constant_count + 1][j]
                        elif self.binary_operations[i] == "-":
                            for j in range(arr.shape[1]):
                                result[j] = result[j] - data[i - constant_count + 1][j]
                        elif self.binary_operations[i] == "*":
                            for j in range(arr.shape[1]):
                                result[j] = result[j] * data[i - constant_count + 1][j]
                        elif self.binary_operations[i] == "/":
                            for j in range(arr.shape[1]):
                                result[j] = result[j] / data[i - constant_count + 1][j]
        elif isinstance(data, DataFrame):
            result = None
            for i, tag_obj in enumerate(self.tags):
                if isinstance(tag_obj, Constant):
                    if num_constants != 0:
                        relevant_data = pd.Series([tag_obj.value] * len(data))
                    else:
                        relevant_data = data[tag_obj.id].copy()
                elif isinstance(tag_obj, self.__class__):
                    relevant_data = tag_obj.calculate_values(data, tag_to_var_map)
                elif tag_to_var_map:
                    relevant_data = data[tag_to_var_map[tag_obj.id]].copy()
                else:
                    relevant_data = data[tag_obj.id].copy()

                if result is None:
                    result = relevant_data.rename(self.id, inplace=False)
                else:
                    if self.binary_operations[i - 1] == "+":
                        result += relevant_data
                    elif self.binary_operations[i - 1] == "-":
                        result -= relevant_data
                    elif self.binary_operations[i - 1] == "*":
                        result *= relevant_data
                    elif self.binary_operations[i - 1] == "/":
                        result /= relevant_data
        elif isinstance(data, ndarray):
            if len(self.binary_operations) != data.shape[1] + num_constants - 1:
                raise ValueError(
                    "Data must have the correct dimensions "
                    "(one more element than binary operations). "
                    "Currently there are {} binary operations and {} data tags".format(
                        len(self.binary_operations), data.shape[1]
                    )
                )
            else:
                if isinstance(self.tags[0], Constant) and num_constants != 0:
                    constant_count += 1
                    result = np.ones(data.shape[0]) * self.tags[0].value
                else:
                    result = data.copy()[:, 0]
                for i in range(data.shape[1] + num_constants - 1):
                    if isinstance(self.tags[i + 1], Constant) and num_constants != 0:
                        constant_count += 1
                        if self.binary_operations[i] == "+":
                            result += self.tags[i + 1].value
                        elif self.binary_operations[i] == "-":
                            result -= self.tags[i + 1].value
                        elif self.binary_operations[i] == "*":
                            result *= self.tags[i + 1].value
                        elif self.binary_operations[i] == "/":
                            result /= self.tags[i + 1].value
                    else:
                        if self.binary_operations[i] == "+":
                            result += data[:, i - constant_count + 1]
                        elif self.binary_operations[i] == "-":
                            result -= data[:, i - constant_count + 1]
                        elif self.binary_operations[i] == "*":
                            result *= data[:, i - constant_count + 1]
                        elif self.binary_operations[i] == "/":
                            result /= data[:, i - constant_count + 1]
        elif isinstance(data, dict):
            result = None
            for i, tag_obj in enumerate(self.tags):
                if isinstance(tag_obj, Constant):
                    if num_constants != 0:
                        first_key = next(iter(data))
                        relevant_data = np.ones(len(data[first_key])) * tag_obj.value
                    else:
                        relevant_data = data[tag_obj.id].copy()
                elif isinstance(tag_obj, self.__class__):
                    relevant_data = tag_obj.calculate_values(data, tag_to_var_map)
                elif tag_to_var_map:
                    relevant_data = data[tag_to_var_map[tag_obj.id]].copy()
                else:
                    relevant_data = data[tag_obj.id].copy()

                if result is None:
                    result = relevant_data
                else:
                    if self.binary_operations[i - 1] == "+":
                        result += relevant_data
                    elif self.binary_operations[i - 1] == "-":
                        result -= relevant_data
                    elif self.binary_operations[i - 1] == "*":
                        result *= relevant_data
                    elif self.binary_operations[i - 1] == "/":
                        result /= relevant_data

            if isinstance(result, Series):
                result.rename(self.id, inplace=True)

        else:
            raise TypeError("Data must be either a list, array, dict, or DataFrame")

        return result

    def process_custom_ops(self, data, tag_to_var_map={}):
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
        num_ops = count_args(self.custom_operations)
        func_ = eval(self.custom_operations)
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
                    data[varname] = tag_obj.calculate_values(data, tag_to_var_map)
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
        if self.mode == OperationMode.Algebraic:
            # check if there are unary ops or just
            if self.unary_operations is not None:
                data = self.process_unary_ops(data, tag_to_var_map=tag_to_var_map)

            if self.binary_operations is not None:
                data = self.process_binary_ops(data, tag_to_var_map=tag_to_var_map)
            elif isinstance(data, (dict, DataFrame)):
                # if no binary ops, get appropriate column from unary ops and rename
                if isinstance(data, dict):
                    data = pd.Series(data[self.tags[0].id], name=self.id)
                else:
                    data = data[self.tags[0].id].rename(self.id)
            elif isinstance(data, ndarray):
                # flatten array since binary operations do that automatically
                data = data[:, 0]
        elif self.mode == OperationMode.Custom:
            if self.custom_operations is not None and self.custom_operations:
                data = self.process_custom_ops(data, tag_to_var_map=tag_to_var_map)
            elif isinstance(data, (dict, DataFrame)):
                # if custom_operations is empty, get appropriate column and rename
                if isinstance(data, dict):
                    data = pd.Series(data[self.tags[0].id], name=self.id)
                else:
                    data = data[self.tags[0].id].rename(self.id)
            elif isinstance(data, ndarray):
                # flatten array since operations do that automatically
                data = data[:, 0]
        else:
            raise ValueError(
                f"{self.mode} not currently supported. "
                "Select either `OperationMode.Algebraic` or `OperationMode.Custom`."
            )

        return data
