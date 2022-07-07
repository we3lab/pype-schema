from enum import Enum, auto


class ContentsType(Enum):
    """Parent class to represent any possible contents,
    whether they are solid, liquid, or gas"""
    pass


class WaterType(ContentsType):
    """Enum to represent wastewater, drinking water, and recycled water."""
    Waste = auto()
    Drinking = auto()
    Recycled = auto()


class GasType(ContentsType):
    """Enum to represent biogas and natural gas, or a blend of the two."""
    Biogas = auto()
    Natural = auto()
    Blend = auto()


class SolidsType(ContentsType):
    """Enum to represent fats, oils, and greases (FOG), thickened primary sludge (TPS),
    thickened waste activated sludge (TWAS), and scum."""
    FOG = auto()
    TPS = auto()
    TWAS = auto()
    Scum = auto()


class PumpType(Enum):
    """Enum to represent constant vs. variable drive pumps"""
    Constant = auto()
    VFD = auto()


class DigesterType(Enum):
    """Enum to represent types of digesters"""
    Aerobic = auto()
    Anaerobic = auto()
