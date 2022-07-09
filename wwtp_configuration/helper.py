from enum import Enum, auto


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
    WasteActivatedSludge = auto()
    Scum = auto()
    FoodWaste = auto()
    SludgeBlend = auto()


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
    GrossEnergyGeneration = auto()
    NetEnergyGeneration = auto()
    GridPurchase = auto()
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

    unit_id : int or str
        integer representing unit number, or `total` if a totalized data point
        across all units of the process

    contents : ContentsType
        Contents moving through the node

    Attributes
    ----------
    id : str
        Tag ID

    units : str
        Units represented as a string. E.g., `MGD` or `cubic meters`

    tag_type : TagType
        Type of data saved under the tag. E.g., `InfluentFlow` or `RunTime`

    unit_id : int or str
        integer representing unit number, or `total` if a totalized data point
        across all units of the process

    contents : ContentsType
        Contents moving through the node
    """

    def __init__(self, id, units, tag_type, unit_id, contents=None):
        self.id = id
        self.contents = contents
        self.tag_type = tag_type
        self.unit_id = unit_id
        self.units = units
