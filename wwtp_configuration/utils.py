import warnings
from enum import Enum, auto
from pint import UndefinedUnitError, DimensionalityError
from .units import u


def parse_quantity(value, units):
    """Convert a value and unit string to a Pint quantity

    Parameters
    ----------
    value : float

    units : str

    Returns
    -------
    Quantity
        a Pint Quantity with the given value and units
    """
    if value is not None:
        if units:
            return value * parse_units(units)
        else:
            return value
    else:
        return None


def parse_units(units):
    """Convert a unit string to a Pint Unit object

    Parameters
    ----------
    units : str

    Returns
    -------
    Unit
        a Pint Unit for the given string
    """
    clean_units = units.lower().replace(" ", "")
    try:
        return u(clean_units).units
    except UndefinedUnitError:
        if (
            clean_units == "mgd"
            or clean_units == "milliongalperday"
            or clean_units == "milliongal/day"
            or clean_units == "10**6gal/day"
            or clean_units == "milliongallonperday"
            or clean_units == "milliongallon/day"
            or clean_units == "10**6gallon/day"
            or clean_units == "milliongallonsperday"
            or clean_units == "milliongallons/day"
            or clean_units == "10**6gallons/day"
            or clean_units == "milliongalperd"
            or clean_units == "milliongal/d"
            or clean_units == "10**6gal/d"
            or clean_units == "milliongallonperd"
            or clean_units == "milliongallon/d"
            or clean_units == "10**6gallon/d"
            or clean_units == "milliongallonsperd"
            or clean_units == "milliongallons/d"
            or clean_units == "10**6gallons/d"
        ):
            return u.MGD
        elif (
            clean_units == "cubicmeters"
            or clean_units == "cubicmeter"
            or clean_units == "m**3"
            or clean_units == "m^3"
            or clean_units == "m3"
            or clean_units == "meter3"
            or clean_units == "meter**3"
            or clean_units == "meter^3"
            or clean_units == "meters3"
            or clean_units == "meters**3"
            or clean_units == "meters^3"
        ):
            return u.m**3
        elif clean_units == "horsepower" or clean_units == "hp":
            return u.hp
        elif (
            clean_units == "scfm"
            or clean_units == "cfm"
            or clean_units == "cubicfeet/min"
            or clean_units == "cubicfoot/min"
            or clean_units == "ft3/min"
            or clean_units == "ft**3/min"
            or clean_units == "ft^3/min"
            or clean_units == "foot3/min"
            or clean_units == "foot^3/min"
            or clean_units == "foot**3/min"
            or clean_units == "feet3/min"
            or clean_units == "feet**3/min"
            or clean_units == "feet^3/min"
            or clean_units == "cubicfeet/minute"
            or clean_units == "cubicfoot/minute"
            or clean_units == "ft3/minute"
            or clean_units == "ft**3/minute"
            or clean_units == "ft^3/minute"
            or clean_units == "foot3/minute"
            or clean_units == "foot^3/minute"
            or clean_units == "foot**3/minute"
            or clean_units == "feet3/minute"
            or clean_units == "feet**3/minute"
            or clean_units == "feet^3/minute"
        ):
            return u.ft**3 / u.min
        elif (
            clean_units == "scf"
            or clean_units == "cubicfeet"
            or clean_units == "cubicfoot"
            or clean_units == "ft3"
            or clean_units == "ft**3"
            or clean_units == "ft^3"
            or clean_units == "foot3"
            or clean_units == "foot**3"
            or clean_units == "foot^3"
            or clean_units == "feet3"
            or clean_units == "feet**3"
            or clean_units == "feet^3"
        ):
            return u.ft**3
        elif (
            clean_units == "gpm"
            or clean_units == "galpermin"
            or clean_units == "gallonpermin"
            or clean_units == "gallonspermin"
            or clean_units == "galperminute"
            or clean_units == "gallonperminute"
            or clean_units == "gallonsperminute"
            or clean_units == "gal/min"
            or clean_units == "gal/minute"
            or clean_units == "gallon/min"
            or clean_units == "gallon/minute"
            or clean_units == "gallons/min"
            or clean_units == "gallons/minute"
        ):
            return u.gal / u.min
        elif (
            clean_units == "gal" or clean_units == "gallon" or clean_units == "gallons"
        ):
            return u.gal
        elif (
            clean_units == "gpd"
            or clean_units == "galperday"
            or clean_units == "gallonperday"
            or clean_units == "gallonsperday"
            or clean_units == "gal/d"
            or clean_units == "gal/day"
            or clean_units == "gallon/d"
            or clean_units == "gallon/day"
            or clean_units == "gallons/d"
            or clean_units == "gallons/day"
        ):
            return u.gal / u.day
        elif (
            clean_units == "m/s"
            or clean_units == "meter/s"
            or clean_units == "meters/s"
            or clean_units == "m/second"
            or clean_units == "meter/second"
            or clean_units == "meters/second"
        ):
            return u.m / u.s
        elif (
            clean_units == "psi"
            or clean_units == "poundspersquareinch"
            or clean_units == "poundpersquareinch"
            or clean_units == "poundspersquarein"
            or clean_units == "poundpersquarein"
            or clean_units == "poundspersqin"
            or clean_units == "poundpersqin"
            or clean_units == "pound/inch**2"
            or clean_units == "pounds/inch**2"
            or clean_units == "lbs/inch**2"
            or clean_units == "lb/inch**2"
            or clean_units == "pound/inch^2"
            or clean_units == "pounds/inch^2"
            or clean_units == "lbs/inch^2"
            or clean_units == "lb/inch^2"
            or clean_units == "pound/squareinch"
            or clean_units == "pounds/squareinch"
            or clean_units == "lbs/squareinch"
            or clean_units == "lb/squareinch"
            or clean_units == "pound/in**2"
            or clean_units == "pounds/in**2"
            or clean_units == "lbs/in**2"
            or clean_units == "lb/in**2"
            or clean_units == "pound/in^2"
            or clean_units == "pounds/in^2"
            or clean_units == "lbs/in^2"
            or clean_units == "lb/in^2"
        ):
            return u.lb / (u.inch**2)
        elif (
            clean_units == "btu"
            or clean_units == "btus"
            or clean_units == "britishthermalunit"
            or clean_units == "britishthermalunits"
        ):
            return u.BTU
        elif (
            clean_units == "btu/scf"
            or clean_units == "btus/scf"
            or clean_units == "britishthermalunit/scf"
            or clean_units == "britishthermalunits/scf"
            or clean_units == "btu/cubicfeet"
            or clean_units == "btus/cubicfeet"
            or clean_units == "britishthermalunit/cubicfeet"
            or clean_units == "britishthermalunits/cubicfeet"
            or clean_units == "btu/cubicfoot"
            or clean_units == "btus/cubicfoot"
            or clean_units == "britishthermalunit/cubicfoot"
            or clean_units == "britishthermalunits/cubicfoot"
            or clean_units == "btu/ft3"
            or clean_units == "btus/ft3"
            or clean_units == "britishthermalunit/ft3"
            or clean_units == "britishthermalunits/ft3"
            or clean_units == "btu/ft**3"
            or clean_units == "btus/ft**3"
            or clean_units == "britishthermalunit/ft**3"
            or clean_units == "britishthermalunits/ft**3"
            or clean_units == "btu/ft^3"
            or clean_units == "btus/ft^3"
            or clean_units == "britishthermalunit/ft^3"
            or clean_units == "britishthermalunits/ft^3"
            or clean_units == "btu/foot3"
            or clean_units == "btus/foot3"
            or clean_units == "britishthermalunit/foot3"
            or clean_units == "britishthermalunits/foot3"
            or clean_units == "btu/foot**3"
            or clean_units == "btus/foot**3"
            or clean_units == "britishthermalunit/foot**3"
            or clean_units == "britishthermalunits/foot**3"
            or clean_units == "btu/feet3"
            or clean_units == "btus/feet3"
            or clean_units == "britishthermalunit/feet3"
            or clean_units == "britishthermalunits/feet3"
            or clean_units == "btu/foot^3"
            or clean_units == "btus/foot^3"
            or clean_units == "britishthermalunit/foot^3"
            or clean_units == "britishthermalunits/foot^3"
            or clean_units == "btu/feet**3"
            or clean_units == "btus/feet**3"
            or clean_units == "britishthermalunit/feet**3"
            or clean_units == "britishthermalunits/feet**3"
            or clean_units == "btu/feet^3"
            or clean_units == "btus/feet^3"
            or clean_units == "britishthermalunit/feet^3"
            or clean_units == "britishthermalunits/feet^3"
        ):
            return u.BTU / (u.ft**3)
        elif (
            clean_units == "kwh"
            or clean_units == "kwhr"
            or clean_units == "kilowatthr"
            or clean_units == "hour*kilowatt"
            or clean_units == "kilowatt*hour"
            or clean_units == "kilowatthour"
        ):
            return u.kW * u.hr
        elif (
            clean_units == "kilowatt*hour/meter**3"
            or clean_units == "hour*kilowatt/meter**3"
            or clean_units == "kwh/meter**3"
            or clean_units == "kwhr/meter**3"
            or clean_units == "kilowatthr/meter**3"
            or clean_units == "kilowatthour/meter**3"
            or clean_units == "kilowatt*hour/m^3"
            or clean_units == "hour*kilowatt/m^3"
            or clean_units == "kwh/m^3"
            or clean_units == "kwhr/m^3"
            or clean_units == "kilowatthr/m^3"
            or clean_units == "kilowatthour/m^3"
            or clean_units == "kilowatt*hour/cubicmeters"
            or clean_units == "hour*kilowatt/cubicmeters"
            or clean_units == "kwh/cubicmeters"
            or clean_units == "kwhr/cubicmeters"
            or clean_units == "kilowatthr/cubicmeters"
            or clean_units == "kilowatthour/cubicmeters"
            or clean_units == "kilowatt*hour/cubicmeter"
            or clean_units == "hour*kilowatt/cubicmeter"
            or clean_units == "kwh/cubicmeter"
            or clean_units == "kwhr/cubicmeter"
            or clean_units == "kilowatthr/cubicmeter"
            or clean_units == "kilowatthour/cubicmeter"
            or clean_units == "kilowatt*hour/m**3"
            or clean_units == "hour*kilowatt/m**3"
            or clean_units == "kwh/m**3"
            or clean_units == "kwhr/m**3"
            or clean_units == "kilowatthr/m**3"
            or clean_units == "kilowatthour/m**3"
            or clean_units == "kilowatt*hour/m3"
            or clean_units == "hour*kilowatt/m3"
            or clean_units == "kwh/m3"
            or clean_units == "kwhr/m3"
            or clean_units == "kilowatthr/m3"
            or clean_units == "kilowatthour/m3"
            or clean_units == "kilowatt*hour/meter3"
            or clean_units == "hour*kilowatt/meter3"
            or clean_units == "kwh/meter3"
            or clean_units == "kwhr/meter3"
            or clean_units == "kilowatthr/meter3"
            or clean_units == "kilowatthour/meter3"
            or clean_units == "kilowatt*hour/meter^3"
            or clean_units == "hour*kilowatt/meter^3"
            or clean_units == "kwh/meter^3"
            or clean_units == "kwhr/meter^3"
            or clean_units == "kilowatthr/meter^3"
            or clean_units == "kilowatthour/meter^3"
            or clean_units == "kilowatt*hour/meters3"
            or clean_units == "hour*kilowatt/meters3"
            or clean_units == "kwh/meters3"
            or clean_units == "kwhr/meters3"
            or clean_units == "kilowatthr/meters3"
            or clean_units == "kilowatthour/meters3"
            or clean_units == "kilowatt*hour/meters**3"
            or clean_units == "hour*kilowatt/meters**3"
            or clean_units == "kwh/meters**3"
            or clean_units == "kwhr/meters**3"
            or clean_units == "kilowatthr/meters**3"
            or clean_units == "kilowatthour/meters**3"
            or clean_units == "kilowatt*hour/meters^3"
            or clean_units == "hour*kilowatt/meters^3"
            or clean_units == "kwh/meters^3"
            or clean_units == "kwhr/meters^3"
            or clean_units == "kilowatthr/meters^3"
            or clean_units == "kilowatthour/meters^3"
        ):
            return u.kW * u.hr / (u.m**3)
        elif clean_units == "kw" or clean_units == "kilowatt":
            return u.kW
        elif clean_units == "meters" or clean_units == "m" or clean_units == "meter":
            return u.m
        elif clean_units == "inches" or clean_units == "in" or clean_units == "inch":
            return u.inch
        else:
            raise UndefinedUnitError("Unsupported unit: " + units)


class ContentsType(Enum):
    """Class to represent any possible contents,
    whether they are sludge, water, or gas"""

    UntreatedSewage = auto()
    PrimaryEffluent = auto()
    SecondaryEffluent = auto()
    TertiaryEffluent = auto()
    TreatedSewage = auto()
    DrinkingWater = auto()
    PotableReuse = auto()
    NonpotableReuse = auto()
    Biogas = auto()
    NaturalGas = auto()
    GasBlend = auto()
    FatOilGrease = auto()
    PrimarySludge = auto()
    TPS = auto()  # thickened primary sludge
    WasteActivatedSludge = auto()
    TWAS = auto()  # thickened waste activated sludge
    Scum = auto()
    FoodWaste = auto()
    SludgeBlend = auto()
    ThickenedSludgeBlend = auto()
    Electricity = auto()
    Brine = auto()
    Seawater = auto()
    SurfaceWater = auto()
    Groundwater = auto()
    Stormwater = auto()


class PumpType(Enum):
    """Enum to represent constant vs. variable drive pumps"""

    Constant = auto()
    VFD = auto()


class DigesterType(Enum):
    """Enum to represent types of digesters"""

    Aerobic = auto()
    Anaerobic = auto()


def select_objs_helper(
    obj,
    obj_source_node=None,
    obj_dest_node=None,
    obj_source_unit_id=None,
    obj_dest_unit_id=None,
    obj_exit_point=None,
    obj_entry_point=None,
    source_id=None,
    dest_id=None,
    source_unit_id=None,
    dest_unit_id=None,
    exit_point_id=None,
    entry_point_id=None,
    source_node_type=None,
    dest_node_type=None,
    exit_point_type=None,
    entry_point_type=None,
    tag_type=None,
    recurse=False,
):
    """Helper to select from objects which match source/destination node class,
    unit ID, and contents

    Parameters
    ----------
    obj : [Node, Connection, Tag]
        Object to check if it meets the specified filtering criteria

    obj_source_node : Node
        Optional source `Node` to check the type and id of. None by default

    obj_dest_node : Node
        Optional destination `Node` to check the type and id of. None by default

    obj_source_unit_id : int, str
        Object's source unit ID to match against. None by default

    obj_dest_unit_id : int, str
        Object's destination unit ID to match against. None by default

    obj_exit_point : Node
        Optional `exit_point` `Node` to check the type and id of. None by default

    obj_entry_point : Node
        Optional `entry_point` `Node` to check the type and id of. None by default

    source_id : str
        Optional id of the source node to filter by. None by default

    dest_id : str
        Optional id of the destination node to filter by. None by default

    source_unit_id : int, str
        Optional unit id of the source to filter by. None by default

    dest_unit_id : int, str
        Optional unit id of the destination to filter by. None by default

    source_node_type : class
        Optional source `Node` subclass to filter by. None by default

    dest_node_type : class
        Optional destination `Node` subclass to filter by. None by default

    tag_type : TagType
        Optional tag type to filter by. None by default

    recurse : bool
        Whether to search for objects within nodes. False by default

    Raises
    ------
    ValueError
        When a source/destination node type is provided to subset tags

    TypeError
        When the objects to select among are not of type
        {'wwtp_configuration.Tag' or `wwtp_configuration.Connection`}

    Returns
    -------
    bool
        True if `obj` fits the filter criteria; False otherwise.
    """
    # convert string source and destination unit IDs to integers
    if isinstance(source_unit_id, str) and source_unit_id != "total":
        source_unit_id = int(source_unit_id)
    if isinstance(dest_unit_id, str) and dest_unit_id != "total":
        dest_unit_id = int(dest_unit_id)

    if source_id is not None and (
        not hasattr(obj_source_node, "id") or obj_source_node.id != source_id
    ):
        if (
            not recurse
            or not hasattr(obj_exit_point, "id")
            or obj_exit_point.id != source_id
        ):
            return False

    if dest_id is not None and (
        not hasattr(obj_dest_node, "id") or obj_dest_node.id != dest_id
    ):
        if (
            not recurse
            or not hasattr(obj_entry_point, "id")
            or obj_entry_point.id != dest_id
        ):
            return False

    if source_unit_id is not None and source_unit_id != obj_source_unit_id:
        return False

    if dest_unit_id is not None and dest_unit_id != obj_dest_unit_id:
        return False

    if exit_point_id is not None and (
        not hasattr(obj_exit_point, "id") or obj_exit_point.id != exit_point_id
    ):
        return False

    if entry_point_id is not None and (
        not hasattr(obj_entry_point, "id") or obj_entry_point.id != entry_point_id
    ):
        return False

    if source_node_type is not None and not isinstance(
        obj_source_node, source_node_type
    ):
        if not recurse or not isinstance(obj_exit_point, source_node_type):
            return False

    if dest_node_type is not None and not isinstance(obj_dest_node, dest_node_type):
        if not recurse or not isinstance(obj_entry_point, dest_node_type):
            return False

    if exit_point_type is not None and not isinstance(obj_exit_point, exit_point_type):
        return False

    if entry_point_type is not None and isinstance(obj_entry_point, entry_point_type):
        return False

    if tag_type is not None and (
        not hasattr(obj, "tag_type") or obj.tag_type != tag_type
    ):
        return False

    return True


def operation_helper(operation, unit, prev_unit, totalized_mix=False):
    """Helper for parsing operations and checking units

    Parameters
    ----------
    operation : ["+", "-", "*", "/"]
        Function to apply when combining tags.
        Supported functions are "+", "-", "*", and "/".

    unit : Unit
        Units for the right side of the operation, represented as a Pint unit.

    prev_unit : Unit
        Units for the left side of the operation, represented as a Pint unit.

    Raises
    ------
    ValueError
        When units are incompatible for addition or subtraction.
        When `operation` is unsupported.

    UserWarning
        When a mix of totalized and detotalized variables makes it impossible
        to verify unit compatibility

    Returns
    -------
    Unit
        Resulting Pint Unit from combining the `unit` and `prev_unit`
        according to `operation`
    """
    if operation == "+" or operation == "-":
        if unit != prev_unit:
            try:
                u.convert(1, unit, prev_unit)
            except DimensionalityError:
                if totalized_mix:
                    warnings.warn(
                        "Unable to verify units since there is a mix of "
                        "totalized and detotalized variables"
                    )
                else:
                    raise ValueError(
                        "Units for addition and subtraction must be compatible"
                    )
    elif operation == "*" or operation == "/":
        if operation == "/":
            prev_unit = prev_unit / unit
        else:
            prev_unit = prev_unit * unit
    else:
        raise ValueError("Unsupported operation " + operation)

    return prev_unit
