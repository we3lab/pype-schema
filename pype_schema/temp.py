from enum import Enum, auto


class ExtendedEnum(Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))


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
    Heat = auto()
    Oil = auto()
    Grease = auto()
    Air = auto()


a = ContentsType._member_map_.items()
for k, v in a:
    print(k, end=", ")
