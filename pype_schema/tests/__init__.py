# -*- coding: utf-8 -*-

"""Unit test package for pype_schema."""

import pickle
from pype_schema.tag import VirtualTag, Tag
from pype_schema.node import Boiler, Cogeneration, Pump, Network


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
    if isinstance(network, Network):
        all_tags = network.get_all_tags(virtual=True, recurse=True)
    else:
        all_tags = network.tags
    vtags = [tag for tag in all_tags if isinstance(tag, VirtualTag)]

    for vtag in vtags:
        vtag.custom_operations = str(vtag.custom_operations)

    try:
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
    except AttributeError:
        pass

    # export pickled object
    with open(outpath, "wb") as pickle_file:
        pickle.dump(network, pickle_file)


def generate_tag_to_var_map(network):
    """Simple example of generating a mapping from
    rom tag IDs to variable names, renaming variables linking
    objects in the network
    (used to generate mapping json file for tests)

    Parameters
    ----------
    network : Network
        The network to generate the mapping for

    Returns
    -------
    dict
        Dictionary mapping tag IDs to variable names
    """
    tag_to_var_map = {}
    for tag in network.get_all_tags(recurse=True):
        if isinstance(tag, VirtualTag):  # keep network name for virtual tags
            tag_to_var_map[tag.id] = tag.id
        elif isinstance(tag, Tag):  # rename for other tags
            parent = network.get_parent_from_tag(tag)
            if hasattr(parent, "id"):
                source_id = parent.id
            else:
                source_id = "Unknown"

            contents_type = tag.contents.name if tag.contents is not None else "None"
            variable_type = tag.tag_type.name

            tag_to_var_map[tag.id] = f"{source_id}_{contents_type}_{variable_type}"
    return tag_to_var_map
