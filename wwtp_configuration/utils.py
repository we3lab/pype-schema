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
        clean_units == "cubicfeet"
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
    elif clean_units == "gal" or clean_units == "gallon" or clean_units == "gallons":
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
        clean_units == "kwh"
        or clean_units == "kwhr"
        or clean_units == "kilowatthr"
        or clean_units == "hour*kilowatt"
        or clean_units == "kilowatt*hour"
        or clean_units == "kilowatthour"
    ):
        return u.kW * u.hr
    elif clean_units == "kw" or clean_units == "kilowatt":
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
