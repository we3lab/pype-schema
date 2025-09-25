import sys
import json
import warnings
import numpy as np
from epyt import epanet


class NpEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy types"""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)


def epyt2pypes(
    inp_file,
    out_file,
    add_nodes=False,
    use_name_as_id=False,
    content_placeholder="DrinkingWater",
):
    """Convert an EPANET input file to a PYPES JSON file

    Parameters
    ----------
    inp_file : str
        Path to the EPANET input file

    out_file : str
        Path to the PYPES JSON file

    add_nodes : bool
        Whether to add additional nodes of Pumps

    use_name_as_id : bool
        Whether to use the node name as the node id.
        False by default, and ignored if `add_nodes` is True

    Returns
    -------
    dict
        dictionary of `Node`, `Connection`, and `VirtualTag` objects
        with keys "nodes", "connections", and "virtual_tags"
    """

    if add_nodes and use_name_as_id:
        warnings.warn("use_name_as_id is ignored if add_nodes is True")

    G = epanet(inp_file)

    node_ids = {}  # EPANET node index to PYPES node id
    nodes = {}
    connections = {}

    obj_counts = {
        "Junction": 0,
        "Tank": 0,
        "Reservoir": 0,
        "Pipe": 0,
        "Pump": 0,
        "Valve": 0,
    }

    for n in G.getNodeIndex():
        node_type = G.getNodeType(n).upper()
        elevation = G.getNodeElevations(n)
        if isinstance(elevation, np.ndarray):
            elevation = float(elevation.flat[0])
        # Node type is one of: Junction, Reservoir, Tank
        if node_type == "JUNCTION":
            if use_name_as_id and not add_nodes:
                id_str = G.getNodeNameID(n)
            else:
                id_str = "Junction" + str(obj_counts["Junction"] + 1)
            node_obj = {
                "id": id_str,
                "type": "Junction",
                "contents": content_placeholder,
                "tags": {},
            }
            node_ids[n] = id_str
            nodes[id_str] = node_obj
            obj_counts["Junction"] += 1
        elif node_type == "RESERVOIR":
            if use_name_as_id and not add_nodes:
                id_str = G.getNodeNameID(n)
            else:
                id_str = "Reservoir" + str(obj_counts["Reservoir"] + 1)
            node_obj = {
                "id": id_str,
                "type": "Reservoir",
                "contents": content_placeholder,
                "elevation (meters)": elevation,
                "tags": {},
            }
            node_ids[n] = id_str
            nodes[id_str] = node_obj
            obj_counts["Reservoir"] += 1
        elif node_type == "TANK":
            volume = G.getNodeTankMaximumWaterVolume(n)
            if isinstance(volume, np.ndarray):
                volume = float(volume.flat[0])
            if use_name_as_id and not add_nodes:
                id_str = G.getNodeNameID(n)
            else:
                id_str = "Tank" + str(obj_counts["Tank"] + 1)
            node_obj = {
                "id": id_str,
                "type": "Tank",
                "contents": content_placeholder,
                "elevation (meters)": elevation,
                "volume (cubic meters)": volume,
                "tags": {},
            }
            node_ids[n] = id_str
            nodes[id_str] = node_obj
            obj_counts["Tank"] += 1
        else:
            raise ValueError(f"Node type {node_type} not recognized")

    for connection in G.getLinkIndex():
        if add_nodes:
            conn_type = G.getLinkType(connection).upper()
            # Link type is one of: Pipe, Pump, Valve
            if conn_type == "PIPE":
                connection_obj = {
                    "id": "Pipe" + str(obj_counts["Pipe"] + 1),
                    "type": "Pipe",
                    "contents": content_placeholder,
                    "source": node_ids[G.getLinkNodesIndex(connection)[0]],
                    "destination": node_ids[G.getLinkNodesIndex(connection)[1]],
                    "tags": {},
                }
                connections["Pipe" + str(obj_counts["Pipe"] + 1)] = connection_obj
                obj_counts["Pipe"] += 1
            elif conn_type == "PUMP":
                pump_obj1 = {
                    "id": "Pump" + str(obj_counts["Pump"] + 1),
                    "type": "Pump",
                    "contents": content_placeholder,
                    "tags": {},
                }
                nodes["Pump" + str(obj_counts["Pump"] + 1)] = pump_obj1

                connection_obj = {
                    "id": "Pipe" + str(obj_counts["Pipe"] + 1),
                    "type": "Pipe",
                    "contents": content_placeholder,
                    "source": node_ids[G.getLinkNodesIndex(connection)[0]],
                    "destination": "Pump" + str(obj_counts["Pump"] + 1),
                    "tags": {},
                }
                connections["Pipe" + str(obj_counts["Pipe"] + 1)] = connection_obj
                obj_counts["Pipe"] += 1

                connection_obj = {
                    "id": "Pipe" + str(obj_counts["Pipe"] + 1),
                    "type": "Pipe",
                    "contents": content_placeholder,
                    "source": "Pump" + str(obj_counts["Pump"] + 1),
                    "destination": node_ids[G.getLinkNodesIndex(connection)[1]],
                    "tags": {},
                }
                connections["Pipe" + str(obj_counts["Pipe"] + 1)] = connection_obj
                obj_counts["Pipe"] += 1
                # wait to increment pump count until all pipes are set up correctly
                obj_counts["Pump"] += 1
            # TODO: change PRV to VALVE_TYPE_LIST to support multiple valve types
            elif conn_type in ["PRV"]:
                # Separate valve into multiple pipes and a valve
                # Assign the first node to source, and the other nodes to destination
                sources = []
                destinations = []
                for i, linknode in enumerate(G.getLinkNodesIndex(connection)):
                    if i == 0:
                        sources.append(node_ids[linknode])
                    else:
                        destinations.append(node_ids[linknode])

                valve_obj = {
                    "id": "Valve" + str(obj_counts["Valve"] + 1),
                    "type": "PRV",
                    "contents": content_placeholder,
                    "tags": {},
                }
                nodes["Valve" + str(obj_counts["Valve"] + 1)] = valve_obj

                for source in sources:
                    connection_obj = {
                        "id": "Pipe" + str(obj_counts["Pipe"] + 1),
                        "type": "Pipe",
                        "contents": content_placeholder,
                        "source": source,
                        "destination": "Valve" + str(obj_counts["Valve"] + 1),
                        "tags": {},
                    }
                    connections["Pipe" + str(obj_counts["Pipe"] + 1)] = connection_obj
                    obj_counts["Pipe"] += 1

                for destination in destinations:
                    connection_obj = {
                        "id": "Pipe" + str(obj_counts["Pipe"] + 1),
                        "type": "Pipe",
                        "contents": content_placeholder,
                        "source": "Valve" + str(obj_counts["Valve"] + 1),
                        "destination": destination,
                        "tags": {},
                    }
                    connections["Pipe" + str(obj_counts["Pipe"] + 1)] = connection_obj
                    obj_counts["Pipe"] += 1
                # wait to increment valve count until all pipes are set up correctly
                obj_counts["Valve"] += 1
            else:
                raise ValueError(f"Connection type {conn_type} not recognized")
        else:
            type_str = G.getLinkType(connection).upper()
            # TODO: change this to VALVE_TYPE_LIST to support multiple valve types
            if type_str in ["PRV"]:
                type_str = "Valve"
            else:
                type_str = type_str[0].upper() + type_str[1:].lower()
            if use_name_as_id:
                id_str = G.getLinkNameID(connection)
            else:
                id_str = type_str + str(connection)
            connection_obj = {
                "id": id_str,
                "type": "Pipe",
                "contents": content_placeholder,
                "source": node_ids[G.getLinkNodesIndex(connection)[0]],
                "destination": node_ids[G.getLinkNodesIndex(connection)[1]],
                "tags": {},
            }
            connections[id_str] = connection_obj
            obj_counts[type_str] += 1

    data = {
        "nodes": list(nodes.keys()),
        "connections": list(connections.keys()),
        "virtual_tags": {},
    }
    for node_name, node_obj in nodes.items():
        temp_node = node_obj.copy()
        temp_node.pop("id")
        data[node_name] = temp_node
    for connection_name, connection_obj in connections.items():
        temp_connection = connection_obj.copy()
        temp_connection.pop("id")
        data[connection_name] = temp_connection

    with open(out_file, "w") as f:
        json.dump(data, f, indent=2, cls=NpEncoder)

    return data


if __name__ == "__main__":
    # TODO: add flags to command line argument
    args = sys.argv[1:]
    epyt2pypes(args[0], args[1])
    print("EPANET to PYPES conversion from {} to {} complete".format(args[0], args[1]))
