from enum import Enum, auto
from pandas import DataFrame
from numpy import array


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
            f"<wwtp_configuration.utils.Tag id:{self.id} units:{self.units} "
            f"tag_type:{self.tag_type} source_unit_id:{self.source_unit_id} "
            f"dest_unit_id:{self.dest_unit_id} parent_id:{self.parent_id} "
            f"totalized:{self.totalized} contents:{self.contents}>\n"
        )

    def __eq__(self, other):
        # don't attempt to compare against unrelated types
        if not isinstance(other, self.__class__):
            return NotImplemented

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


class VirtualTag:
    """Representation for data that is not in the SCADA system,
    but is instead a combination of existing tags. Tags are combined according
    to `operations`, with the current supported operations limited to "+", "-", "*", and "/"

    Parameters
    ----------
    id : str
        Tag ID

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

    Raises
    ------
    ValueError
        When the `operations` includes unsupported operations or is not the correct length.
        When `tag_type` is not specified and constituent tags have different types.
        When `contents` of the constituent tags are different types.

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

        def __init__(
            self,
            id,
            tags,
            operations="+",
            tag_type=None
        ):
            self.id = id
            self.tags = tags

            units = []
            contents = None
            totalized = None

            if tag_type is not None:
                determine_type = False
            else:
                determine_type = True

            for tag in tags:
                units.append(tag.units)
                if totalized is not None:
                    if totalized != tag.totalized:
                        raise ValueError("All Tags must have the same value for 'totalized'")
                else:
                    totalized = tag.totalized

                if determine_type:
                    if tag_type is not None:
                        if tag_type != tag.tag_type:
                            raise ValueError("All Tags must have the same value for 'tag_type'")
                    else:
                        tag_type = tag.tag_type

                if contents is not None:
                    if contents != tag.contents:
                        raise ValueError("All Tags must have the same value for 'contents'")
                else:
                    contents = tag.contents

            self.contents = contents
            self.tag_type = tag_type
            self.totalized = totalized

            if isinstance(operations, list):
                if len(operations) != len(tags) - 1:
                    raise ValueError("Operations list must be of length one less than the Tag list")
                else:
                    self.operations = operations
                    prev_unit = None
                    for i, unit in enumerate(units):
                        if isinstance(unit, str):
                            unit = parse_units(unit)

                        if prev_unit is not None:
                            prev_unit = operation_helper(operations[i-1], unit, prev_unit)
                        else:
                            prev_unit = unit
            else:
                prev_unit = None
                for unit in units:
                    if isinstance(unit, str):
                        unit = parse_units(unit)

                    if prev_unit is not None:
                        prev_unit = operation_helper(operations, unit, prev_unit)
                    else:
                        prev_unit = unit

                self.operations = [operations] * (len(self.tags) - 1)

            self.units = prev_unit

        def __repr__(self):
            return (
                f"<wwtp_configuration.utils.VirtualTag id:{self.id} units:{self.units} "
                f"tag_type:{self.tag_type} totalized:{self.totalized} contents:{self.contents}"
                f"tags:{[tag.id for tag in self.tags]} operations:{self.operations}>\n"
            )

        def __eq__(self, other):
            # don't attempt to compare against unrelated types
            if not isinstance(other, self.__class__):
                return NotImplemented

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
                    self.tags,
                    self.operations,
                    self.contents,
                    self.tag_type,
                    self.totalized,
                    self.units,
                )
            )

        def calculate_values(self, data):
            """Combine the given data according to the VirtualTag's operations

            Parameters
            ----------
            data : list, array, or DataFrame
                a list, numpy array, or pandas DataFrame of data that has the
                correct dimensions. I.e., the number of columns is one more than operations

            Returns
            -------
            array
                numpy array of combined dataset
            """
            # TODO: check units are handled correctly
            if isinstance(data, list):
                if len(self.operations) != len(data) - 1:
                    raise ValueError("Data must have the correct dimensions (one more element than operations). "
                        "Currently there are {} operations and {} data tags".format(
                        len(self.operations, len(data)))
                    )
                else:
                    result = data[0]
                    for i in range(len(data) - 1):
                        if operations[i] == "+":
                            result += data[i+1]
                        elif operations[i] == "-":
                            result -= data[i+1]
                        elif operations[i] == "*":
                            result *= data[i+1]
                        elif operations[i] == "/":
                            result /= data[i+1]
            if isinstance(data, DataFrame):
                if len(self.operations) != len(data.columns) - 1:
                    raise ValueError("Data must have the correct dimensions (one more element than operations). "
                        "Currently there are {} operations and {} data tags".format(
                        len(self.operations, len(data.columns)))
                    )
                else:
                    result = None
                    for _, colData in data.iteritems():
                        if result is None:
                            result = colData
                        else:
                            if operations[i] == "+":
                                result += colData
                            elif operations[i] == "-":
                                result -= colData
                            elif operations[i] == "*":
                                result *= colData
                            elif operations[i] == "/":
                                result /= colData
            if isinstance(data, array):
                if len(self.operations) != data.shape[1] - 1:
                    raise ValueError("Data must have the correct dimensions (one more element than operations). "
                        "Currently there are {} operations and {} data tags".format(
                        len(self.operations, data.shape[1]))
                    )
                else:
                    result = data[:, 0]
                    for i in range(data.shape[1] - 1):
                        if operations[i] == "+":
                            result += data[:, i+1]
                        elif operations[i] == "-":
                            result -= data[:, i+1]
                        elif operations[i] == "*":
                            result *= data[:, i+1]
                        elif operations[i] == "/":
                            result /= data[:, i+1]
            else:
                raise TypeError("Data must be either a list, array, or DataFrame")
