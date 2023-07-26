import warnings
from enum import Enum, auto
from pandas import DataFrame, Series
from numpy import ndarray, array, issubdtype
from .utils import binary_helper, unary_helper, parse_units


UNARY_OPS = ["noop", "delta", "<<", ">>", "~", "-"]
BINARY_OPS = ["+", "-", "*", "/"]


class TagType(Enum):
    """Enum to represent types of SCADA tags"""

    Flow = auto()
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
    a combination of existing tags. First `unary_operations`
    ("noop", "delta", "<<", ">>", "~", and "-") are applied,
    then tags are combined according to `binary_operations`,
    with the current supported operations limited to "+", "-", "*", and "/"

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
        When `unary_operations` or `binary_operations` includes
        unsupported operations or is the wrong length.
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
        unary_operations=None,
        binary_operations=None,
        tag_type=None,
        parent_id=None,
        contents=None,
    ):
        self.id = id
        self.parent_id = parent_id
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

        if isinstance(unary_operations, list):
            if len(unary_operations) != len(tags):
                raise ValueError(
                    "Unary operations list must be same length as Tag list"
                )
            else:
                for i, unit in enumerate(units):
                    if isinstance(unary_operations[i], list):
                        for j in range(len(unary_operations[i])):
                            if unary_operations[i][j] not in UNARY_OPS:
                                raise ValueError(
                                    "Unsupported unary operator:", unary_operations[i]
                                )
                            elif unary_operations[i][j] == "~":
                                units[i] = None
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
                            units[i] = None
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
                    "Binary operations list must be of length one less than Tag list"
                )
            else:
                self.binary_operations = binary_operations
                prev_unit = None
                for i, unit in enumerate(units):
                    if isinstance(unit, str):
                        unit = parse_units(unit)

                    if prev_unit is not None:
                        # check that operation is supported
                        if binary_operations[i - 1] not in BINARY_OPS:
                            raise ValueError(
                                "Unsupported binary operator:", binary_operations[i - 1]
                            )
                        prev_unit = binary_helper(
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
            for unit in units:
                if isinstance(unit, str):
                    unit = parse_units(unit)

                if prev_unit is not None:
                    prev_unit = binary_helper(
                        binary_operations, unit, prev_unit, totalized_mix=totalized_mix
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
            prev_unit = units[0]

        self.units = prev_unit

    def __repr__(self):
        return (
            f"<wwtp_configuration.utils.VirtualTag id:{self.id} units:{self.units} "
            f"tag_type:{self.tag_type} totalized:{self.totalized} "
            f"contents:{self.contents} tags:{[tag.id for tag in self.tags]} "
            f"unary_operations:{self.unary_operations} "
            f"binary_operations:{self.binary_operations} "
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
            and self.parent_id == other.parent_id
        )

    def __hash__(self):
        return hash(
            (
                self.id,
                str(self.tags),
                str(self.unary_operations),
                str(self.binary_operations),
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
            return self.unary_operations < other.unary_operations
        elif self.binary_operations != other.binary_operations:
            return self.binary_operations < other.binary_operations
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
        result = data.copy()
        num_ops = len(self.unary_operations)
        if isinstance(data, list):
            if len(self.unary_operations) != len(data):
                raise ValueError(
                    "Data must have the correct dimensions "
                    "(same length as unary operations). "
                    "Currently there are {} unary operations and {} data tags".format(
                        num_ops, len(data)
                    )
                )
            else:
                for i in range(num_ops):
                    result[i] = unary_helper(data[i], self.unary_operations[i])
        elif isinstance(data, ndarray):
            if issubdtype(data.dtype, (int)):
                result = result.astype("float")
            if len(self.unary_operations) != data.shape[1]:
                raise ValueError(
                    "Data must have the correct dimensions "
                    "(same length as unary operations). "
                    "Currently there are {} unary operations and {} data tags".format(
                        len(self.unary_operations), data.shape[1]
                    )
                )
            else:
                for i in range(num_ops):
                    result[:, i] = unary_helper(data[:, i], self.unary_operations[i])
        elif isinstance(data, (dict, DataFrame)):
            for i, tag_obj in enumerate(self.tags):
                if isinstance(tag_obj, self.__class__):
                    relevant_data = tag_obj.calculate_values(data)
                elif tag_to_var_map:
                    relevant_data = result[tag_to_var_map[tag_obj.id]]
                else:
                    relevant_data = result[tag_obj.id]

                relevant_data = unary_helper(relevant_data, self.unary_operations[i])

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
        if isinstance(data, list):
            if len(self.binary_operations) != len(data) - 1:
                raise ValueError(
                    "Data must have the correct dimensions "
                    "(one more element than binary operations). "
                    "Currently there are {} binary operations and {} data tags".format(
                        len(self.binary_operations), len(data)
                    )
                )
            else:
                arr = array(data)
                result = data[0]
                for i in range(arr.shape[0] - 1):
                    if self.binary_operations[i] == "+":
                        for j in range(arr.shape[1]):
                            result[j] = result[j] + data[i + 1][j]
                    elif self.binary_operations[i] == "-":
                        for j in range(arr.shape[1]):
                            result[j] = result[j] - data[i + 1][j]
                    elif self.binary_operations[i] == "*":
                        for j in range(arr.shape[1]):
                            result[j] = result[j] * data[i + 1][j]
                    elif self.binary_operations[i] == "/":
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
                    if self.binary_operations[i - 1] == "+":
                        result += relevant_data
                    elif self.binary_operations[i - 1] == "-":
                        result -= relevant_data
                    elif self.binary_operations[i - 1] == "*":
                        result *= relevant_data
                    elif self.binary_operations[i - 1] == "/":
                        result /= relevant_data
        elif isinstance(data, ndarray):
            if len(self.binary_operations) != data.shape[1] - 1:
                raise ValueError(
                    "Data must have the correct dimensions "
                    "(one more element than binary operations). "
                    "Currently there are {} binary operations and {} data tags".format(
                        len(self.binary_operations), data.shape[1]
                    )
                )
            else:
                result = data[:, 0]
                for i in range(data.shape[1] - 1):
                    if self.binary_operations[i] == "+":
                        result += data[:, i + 1]
                    elif self.binary_operations[i] == "-":
                        result -= data[:, i + 1]
                    elif self.binary_operations[i] == "*":
                        result *= data[:, i + 1]
                    elif self.binary_operations[i] == "/":
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
        if self.unary_operations is not None:
            data = self.process_unary_ops(data, tag_to_var_map=tag_to_var_map)

        if self.binary_operations is not None:
            data = self.process_binary_ops(data, tag_to_var_map=tag_to_var_map)
        elif isinstance(data, (dict, DataFrame)):
            # if no binary ops, get appropriate column from unary ops and rename
            data = data[self.tags[0].id].rename(self.id)
        elif isinstance(data, ndarray):
            # flatten array since binary operations do that automatically
            data = data[:, 0]

        return data
