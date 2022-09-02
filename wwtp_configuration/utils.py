from enum import Enum, auto
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
        return value * parse_units(units)
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
    if clean_units == "mgd" or clean_units == "milliongallonsday":
        return u.MGD
    elif (
        clean_units == "cubicmeters"
        or clean_units == "m**3"
        or clean_units == "m^3"
        or clean_units == "m3"
    ):
        return u.m**3
    elif clean_units == "horsepower" or clean_units == "hp":
        return u.hp
    elif clean_units == "scfm":
        return u.ft**3 / u.min
    elif (
        clean_units == "cubicfeet"
        or clean_units == "ft3"
        or clean_units == "ft**3"
        or clean_units == "ft^3"
    ):
        return u.ft**3
    elif clean_units == "gpm" or clean_units == "gallon/min":
        return u.gal / u.min
    elif (
        clean_units == "gal"
        or clean_units == "gallon"
        or clean_units == "gallons"
    ):
        return u.gal
    elif clean_units == "gpd":
        return u.gal / u.day
    elif clean_units == "m/s" or clean_units == "meter/s":
        return u.m / u.s
    elif (
        clean_units == "kwh"
        or clean_units == "hour*kilowatt"
        or clean_units == "kilowatt*hour"
        or clean_units == "kilowatthour"
    ):
        return u.kW * u.hr
    elif clean_units == "kw":
        return u.kW
    elif clean_units == "meters" or clean_units == "m" or clean_units == "meter":
        return u.m
    elif clean_units == "inches" or clean_units == "in" or clean_units == "inch":
        return u.inch
    else:
        raise TypeError("Unsupported unit: " + units)


class ContentsType(Enum):
    """Class to represent any possible contents,
    whether they are sludge, water, or gas"""

    UntreatedSewage = auto()
    TreatedSewage = auto()
    DrinkingWater = auto()
    PotableReuse = auto()
    NonpotableReuse = auto()
    Biogas = auto()
    NaturalGas = auto()
    GasBlend = auto()
    FatOilGrease = auto()
    PrimarySludge = auto()
    TPS = auto()
    WasteActivatedSludge = auto()
    TWAS = auto()
    Scum = auto()
    FoodWaste = auto()
    SludgeBlend = auto()
    ThickenedSludgeBlend = auto()
    Electricity = auto()
    Brine = auto()
    Seawater = auto()
    SurfaceWater = auto()
    Groundwater = auto()


class PumpType(Enum):
    """Enum to represent constant vs. variable drive pumps"""

    Constant = auto()
    VFD = auto()


class DigesterType(Enum):
    """Enum to represent types of digesters"""

    Aerobic = auto()
    Anaerobic = auto()


class TagType(Enum):
    """Enum to represent types of SCADA tags"""

    Flow = auto()
    Volume = auto()
    Level = auto()
    Pressure = auto()
    RunTime = auto()
    RunStatus = auto()
    VSS = auto()
    TSS = auto()
    COD = auto()


class Tag:
    """Class to represent a SCADA or other data tag

    Parameters
    ----------
    id : str
        Tag ID

    units : str
        Units represented as a string. E.g., `MGD` or `cubic meters`

    tag_type : TagType
        Type of data saved under the tag. E.g., `InfluentFlow` or `RunTime`

    source_unit_id : int or str
        integer representing unit number, or `total` if a combined data point
        across all units of the sources node

    dest_unit_id : int or str
        integer representing unit number, or `total` if a combined data point
        across all units of the destination node

    totalized : bool
        True if data is totalized. False otherwise

    contents : ContentsType
        Data stream contents. E.g., `WasteActivatedSludge` or `NaturalGas`

    Attributes
    ----------
    id : str
        Tag ID

    units : str
        Units represented as a string. E.g., `MGD` or `cubic meters`

    tag_type : TagType
        Type of data saved under the tag. E.g., `InfluentFlow` or `RunTime`

    source_unit_id : int or str
        integer representing unit number, or `total` if a combined data point
        across all units of the sources node

    dest_unit_id : int or str
        integer representing unit number, or `total` if a combined data point
        across all units of the destination node

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

    def __repr__(self):
        return (
            f"<wwtp_configuration.utils.Tag id:{self.id} units:{self.units} "
            f"tag_type:{self.tag_type} source_unit_id:{self.source_unit_id} "
            f"dest_unit_id:{self.dest_unit_id} totalized:{self.totalized} "
            f"contents:{self.contents}>\n"
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
        )
