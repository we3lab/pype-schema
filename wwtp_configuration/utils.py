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
    if units.lower() == "mgd":
        return u.MGD
    elif units == "cubic meters" or units == "m3":
        return u.m**3
    elif units == "horsepower" or units == "hp":
        return u.hp
    elif units.lower() == "scfm":
        return u.ft**3 / u.min
    elif units == "cubic feet" or units == "ft3":
        return u.ft**3
    elif units.lower() == "gpm":
        return u.gal / u.min
    elif (
        units.lower() == "gal"
        or units.lower() == "gallon"
        or units.lower() == "gallons"
    ):
        return u.gal
    elif units.lower() == "gpd":
        return u.gal / u.day
    elif units.replace(" ", "") == "m/s" or units.replace(" ", "") == "meter/s":
        return u.m / u.s
    elif units.lower() == "kwh":
        return u.kW * u.hr
    elif units.lower() == "kw":
        return u.kW
    elif units == "meters" or units == "m":
        return u.m
    elif units == "inches" or units == "in" or units == "inch":
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
