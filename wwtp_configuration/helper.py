from enum import Enum, auto


class ContentsType(Enum):
    """Parent class to represent any possible contents,
    whether they are solid, liquid, or gas"""
    pass


class WaterType(ContentsType):
    """Enum to represent wastewater, drinking water, and recycled water."""
    UntreatedSewage = auto()
    TreatedSewage = auto()
    Drinking = auto()
    PotableReuse = auto()
    NonpotableReuse = auto()


class GasType(ContentsType):
    """Enum to represent biogas and natural gas, or a blend of the two."""
    Biogas = auto()
    NaturalGas = auto()
    GasBlend = auto()


class SolidsType(ContentsType):
    """Enum to represent fats, oils, and greases (FOG), primary sludge,
    waste activated sludge (WAS), and scum."""
    FatOilGrease = auto()
    PrimarySludge = auto()
    WasteActivatedSludge = auto()
    Scum = auto()
    FoodWaste = auto()
    SludgeBlend = auto()


class EnergyGenType(ContentsType):
    """Enum to represent energy generation data"""
    Gross = auto()
    Net = auto()
    Grid = auto()


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
    InfluentFlow = auto()
    EffluentFlow = auto()
    EnergyConsumption = auto()
    EnergyGeneration = auto()
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

    contents : ContentsType
        Contents moving through the node

    units : str
        Units represented as a string. E.g., `MGD` or `cubic meters`

    tag_type : TagType
        Type of data saved under the tag. E.g., `InfluentFlow` or `RunTime`

    unit_id : int or str
        integer representing unit number, or `total` if a totalized data point
        across all units of the process

    Attributes
    ----------
    id : str
        Tag ID

    contents : ContentsType
        Contents moving through the node

    units : str
        Units represented as a string. E.g., `MGD` or `cubic meters`

    tag_type : TagType
        Type of data saved under the tag. E.g., `InfluentFlow` or `RunTime`

    unit_id : int or str
        integer representing unit number, or `total` if a totalized data point
        across all units of the process
    """

    def __init__(self, id, contents, units, tag_type, unit_id):
        self.id = id
        self.contents = contents
        self.tag_type = tag_type
        self.unit_id = unit_id
        self.units = units
