# -*- coding: utf-8 -*-

"""Unit test package for pype_schema."""

import pickle
from pype_schema.tag import VirtualTag
from pype_schema.node import Boiler, Cogeneration, Pump


def pickle_without_functions(network, outpath):
    """Pickle an PyPES model, converting lambda functions to string arguments

    Parameters
    ----------
    key : str
        Key to search

    outpath : str
        file path to save the pickled object
    """
    # make all the VirtualTag operations into strings
    all_tags = network.get_all_tags(virtual=True, recurse=True)
    vtags = [tag for tag in all_tags if isinstance(tag, VirtualTag)]

    for vtag in vtags:
        vtag.custom_operations = str(vtag.custom_operations)

    # set efficiency attribute to None
    boilers = network.select_objs(obj_type=Boiler, recurse=True)
    for boiler in boilers:
        boiler.set_thermal_efficiency(None)

    cogens = network.select_objs(obj_type=Cogeneration, recurse=True)
    for cogen in cogens:
        cogen.set_thermal_efficiency(None)
        cogen.set_electrical_efficiency(None)

    pumps = network.select_objs(obj_type=Pump, recurse=True)
    for pump in pumps:
        pump.set_pump_curve(None)

    # export pickled object
    with open(outpath, "wb") as pickle_file:
        pickle.dump(network, pickle_file)
