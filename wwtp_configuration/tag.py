import warnings
from enum import Enum, auto
from numpy import ndarray, array
from pandas import DataFrame, Series
from .utils import operation_helper, parse_units


class TagType(Enum):
    """Enum to represent types of SCADA tags"""

    Flow = auto()
    Volume = auto()
    Level = auto()
    Pressure = auto()
    RunTime = auto()
    RunStatus = auto()
    VSS = auto()
    TSS = auto()  # total suspended solids
    TDS = auto()  # total dissolved solids
    COD = auto()  # chemical oxygen demand
    BOD = auto()  # biochemical oxygen demand
    pH = auto()
    Rotation = auto()
    Efficiency = auto()
    StateOfCharge = auto()


CONTENTLESS_TYPES = [
    TagType.RunTime,
    TagType.RunStatus,
    TagType.Rotation,
    TagType.Efficiency,
]


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

    Attributes
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
        across all units of the sources node

    dest_unit_id : int or str
        integer representing unit number, or `total` if a combined data point
        across all units of the destination node

    parent_id : str
        ID for the parent object (either a Node or Connection)

    totalized : bool
        True if data is totalized. False otherwise

    contents : ContentsType
        Contents moving through the node
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
    ):
        self.id = id
        self.units = units
        self.contents = contents
        self.tag_type = tag_type
        self.totalized = totalized
        self.source_unit_id = source_unit_id
        self.dest_unit_id = dest_unit_id
        self.parent_id = parent_id

    def __repr__(self):
        return (
            f"<wwtp_configuration.tag.Tag id:{self.id} units:{self.units} "
            f"tag_type:{self.tag_type} source_unit_id:{self.source_unit_id} "
            f"dest_unit_id:{self.dest_unit_id} parent_id:{self.parent_id} "
            f"totalized:{self.totalized} contents:{self.contents}>\n"
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
        else:
            return self.parent_id < other.parent_id


class VirtualTag:
    """Representation for data that is not in the SCADA system, but is instead
     a combination of existing tags. Tags are combined according to `operations`,
     with the current supported operations limited to "+", "-", "*", and "/"

    Parameters
    ----------
    id : str
        VirtualTag ID

    tags : list of Tag
        List of Tag objects to combine

    operations : function or list
        Function to apply when combining tags.
        If a single function it will be applied to all Tags.
        Otherwise, the `operations` must be one shorter than `tags`, and
        functions will be applied in order

    tag_type : TagType
        Type of data saved under the tag. E.g., `InfluentFlow` or `RunTime`.
        Default is None, and it will be automatically determined from constituent
        Tags if they all have the same type.

    contents : ContentsType
        Contents moving through the node. Default is None, and it will be automatically
        determined from consituent Tag contents

    Raises
    ------
    ValueError
        When the `operations` includes unsupported operations or is the wrong length.
        When `tag_type` is not specified and constituent tags have different types.
        When `contents` of the constituent tags are different types.

    UserWarning
        When a mix of totalized and detotalized tags are combined

    Attributes
    ----------
    id : str
        Tag ID

    tags : list of Tag
        List of Tag objects to combine

    operations : ["+", "-", "*", "/"]
        Function to apply when combining tags.
        Supported functions are "+", "-", "*", and "/".
        If a single string is passed, it will be applied to all Tags.
        Otherwise, the `operations` list must be one shorter than `tags`, and
        functions will be applied in order from left to right

    units : str or Unit
        Units represented as a string or Pint unit.
        E.g., 'MGD' or 'cubic meters' or <Unit('MGD')>

    tag_type : TagType
        Type of data saved under the tag. E.g., `InfluentFlow` or `RunTime`

    totalized : bool
        True if data is totalized. False otherwise

    contents : ContentsType
        Contents moving through the node
    """

    def __init__(self, id, tags, operations="+", tag_type=None, contents=None):
        self.id = id
        self.tags = tags

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
                    if tag_type != tag.tag_type:
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

        if isinstance(operations, list):
            if len(operations) != len(tags) - 1:
                raise ValueError(
                    "Operations list must be of length one less than the Tag list"
                )
            else:
                self.operations = operations
                prev_unit = None
                for i, unit in enumerate(units):
                    if isinstance(unit, str):
                        unit = parse_units(unit)

                    if prev_unit is not None:
                        prev_unit = operation_helper(
                            operations[i - 1],
                            unit,
                            prev_unit,
                            totalized_mix=totalized_mix,
                        )
                    else:
                        prev_unit = unit
        else:
            prev_unit = None
            for unit in units:
                if isinstance(unit, str):
                    unit = parse_units(unit)

                if prev_unit is not None:
                    prev_unit = operation_helper(
                        operations, unit, prev_unit, totalized_mix=totalized_mix
                    )
                else:
                    prev_unit = unit

            self.operations = [operations] * (len(self.tags) - 1)

        self.units = prev_unit

    def __repr__(self):
        return (
            f"<wwtp_configuration.utils.VirtualTag id:{self.id} units:{self.units} "
            f"tag_type:{self.tag_type} totalized:{self.totalized} "
            f"contents:{self.contents} tags:{[tag.id for tag in self.tags]} "
            "operations:{self.operations}>\n"
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

    def calculate_values(self, data, tag_to_var_map={}):
        """Combine the given data according to the VirtualTag's operations

        Parameters
        ----------
        data : list, array, dict, or DataFrame
            a list, numpy array, or pandas DataFrame of data that has the
            correct dimensions. I.e., the number of columns is one more than operations

        tag_to_var_map : dict
            dictionary of the form { tag.id : variable_name } for using data files
            that differ from the original SCADA tag naming system

        Returns
        -------
        list, array, or Series
            numpy array of combined dataset
        """
        if isinstance(data, list):
            if len(self.operations) != len(data) - 1:
                raise ValueError(
                    "Data must have the correct dimensions "
                    "(one more element than operations). "
                    "Currently there are {} operations and {} data tags".format(
                        len(self.operations), len(data)
                    )
                )
            else:
                arr = array(data)
                result = data[0]
                for i in range(arr.shape[0] - 1):
                    if self.operations[i] == "+":
                        for j in range(arr.shape[1]):
                            result[j] = result[j] + data[i + 1][j]
                    elif self.operations[i] == "-":
                        for j in range(arr.shape[1]):
                            result[j] = result[j] - data[i + 1][j]
                    elif self.operations[i] == "*":
                        for j in range(arr.shape[1]):
                            result[j] = result[j] * data[i + 1][j]
                    elif self.operations[i] == "/":
                        for j in range(arr.shape[1]):
                            result[j] = result[j] / data[i + 1][j]
        elif isinstance(data, DataFrame):
            result = None
            for i, tag_obj in enumerate(self.tags):
                if isinstance(tag_obj, self.__class__):
                    relevant_data = tag_obj.calculate_values(data)
                elif tag_to_var_map:
                    relevant_data = data[tag_to_var_map[tag_obj.id]]
                else:
                    relevant_data = data[tag_obj.id]

                if result is None:
                    result = relevant_data.rename(self.id, inplace=False)
                else:
                    if self.operations[i - 1] == "+":
                        result += relevant_data
                    elif self.operations[i - 1] == "-":
                        result -= relevant_data
                    elif self.operations[i - 1] == "*":
                        result *= relevant_data
                    elif self.operations[i - 1] == "/":
                        result /= relevant_data
        elif isinstance(data, ndarray):
            if len(self.operations) != data.shape[1] - 1:
                raise ValueError(
                    "Data must have the correct dimensions "
                    "(one more element than operations). "
                    "Currently there are {} operations and {} data tags".format(
                        len(self.operations), data.shape[1]
                    )
                )
            else:
                result = data[:, 0]
                for i in range(data.shape[1] - 1):
                    if self.operations[i] == "+":
                        result += data[:, i + 1]
                    elif self.operations[i] == "-":
                        result -= data[:, i + 1]
                    elif self.operations[i] == "*":
                        result *= data[:, i + 1]
                    elif self.operations[i] == "/":
                        result /= data[:, i + 1]
        elif isinstance(data, dict):
            result = None
            for i, tag_obj in enumerate(self.tags):
                if isinstance(tag_obj, self.__class__):
                    relevant_data = tag_obj.calculate_values(data)
                elif tag_to_var_map:
                    relevant_data = data[tag_to_var_map[tag_obj.id]]
                else:
                    relevant_data = data[tag_obj.id]

                if result is None:
                    result = relevant_data
                else:
                    if self.operations[i - 1] == "+":
                        result += relevant_data
                    elif self.operations[i - 1] == "-":
                        result -= relevant_data
                    elif self.operations[i - 1] == "*":
                        result *= relevant_data
                    elif self.operations[i - 1] == "/":
                        result /= relevant_data

            if isinstance(result, Series):
                result.rename(self.id, inplace=True)

        else:
            raise TypeError("Data must be either a list, array, dict, or DataFrame")

        return result
