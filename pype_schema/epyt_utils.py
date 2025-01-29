import sys
import json
import numpy as np
from epyt import epanet

content_placeholder = "DrinkingWater"


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


def epyt2pypes(inp_file, out_file, add_nodes=False):
    """Convert an EPANET input file to a PYPES JSON file

    Parameters
    ----------
    inp_file : str
        Path to the EPANET input file

    out_file : str
        Path to the PYPES JSON file

    add_nodes : bool
        Whether to add additional nodes of Pumps
    """

    G = epanet(inp_file)

    node_ids = {}  # EPANET node index to PYPES node id
    nodes = {}
    connections = {}

    obj_counts = {
        "Joint": 0,
        "Tank": 0,
        "Reservoir": 0,
        "Pipe": 0,
        "Pump": 0,
    }

    for n in G.getNodeIndex():
        # Node type is one of: Junction, Reservoir, Tank
        if G.getNodeType(n).upper() == "JUNCTION":
            id_str = "Joint" + str(obj_counts["Joint"] + 1)
            node_obj = {
                "id": id_str,
                "type": "Joint",
                "contents": content_placeholder,
                "tags": {},
            }
            node_ids[n] = id_str
            nodes[id_str] = node_obj
            obj_counts["Joint"] += 1

        elif G.getNodeType(n).upper() == "RESERVOIR":
            id_str = "Reservoir" + str(obj_counts["Reservoir"] + 1)
            node_obj = {
                "id": id_str,
                "type": "Reservoir",
                "contents": content_placeholder,
                "levation (meters)": G.getNodeElevations(n),
                "tags": {},
            }
            node_ids[n] = id_str
            nodes[id_str] = node_obj
            obj_counts["Reservoir"] += 1

        elif G.getNodeType(n).upper() == "TANK":
            id_str = "Tank" + str(obj_counts["Tank"] + 1)
            node_obj = {
                "id": id_str,
                "type": "Tank",
                "contents": content_placeholder,
                "levation (meters)": G.getNodeElevations(n),
                "volume (cubic meters)": G.getNodeTankVolume(n),
                "tags": {},
            }
            node_ids[n] = id_str
            nodes[id_str] = node_obj
            obj_counts["Tank"] += 1

        else:
            raise ValueError(f"Node type {G.getNodeType(n)} not recognized")

    for connection in G.getLinkIndex():
        if add_nodes:
            # Link type is one of: Pipe, Pump, Valve
            if G.getLinkType(connection).upper() == "PIPE":
                connection_obj = {
                    "id": "Pipe" + str(obj_counts["Pipe"]),
                    "type": "Pipe",
                    "contents": content_placeholder,
                    "source": node_ids[G.getLinkNodesIndex(connection)[0]],
                    "destination": node_ids[G.getLinkNodesIndex(connection)[1]],
                    "tags": {},
                }
                connections["Pipe" + str(obj_counts["Pipe"])] = connection_obj
                obj_counts["Pipe"] += 1

            elif G.getLinkType(connection).upper() == "PUMP":
                pump_obj1 = {
                    "id": "Pump" + str(obj_counts["Pump"]),
                    "type": "Pump",
                    "contents": content_placeholder,
                    "tags": {},
                }
                nodes["Pump" + str(obj_counts["Pump"])] = pump_obj1
                obj_counts["Pump"] += 1

                connection_obj = {
                    "id": "Pipe" + str(obj_counts["Pipe"]),
                    "type": "Pipe",
                    "contents": content_placeholder,
                    "source": node_ids[G.getLinkNodesIndex(connection)[0]],
                    "destination": "Pump" + str(obj_counts["Pump"]),
                    "tags": {},
                }
                connections["Pipe" + str(obj_counts["Pipe"])] = connection_obj
                obj_counts["Pipe"] += 1

                connection_obj = {
                    "id": "Pipe" + str(obj_counts["Pipe"]),
                    "type": "Pipe",
                    "contents": content_placeholder,
                    "source": "Pump" + str(obj_counts["Pump"]),
                    "destination": node_ids[G.getLinkNodesIndex(connection)[1]],
                    "tags": {},
                }
                connections["Pipe" + str(obj_counts["Pipe"])] = connection_obj
                obj_counts["Pipe"] += 1

            elif G.getLinkType(connection).upper() == "VALVE":
                raise NotImplementedError("Valves not yet supported in PyPES")
                # TODO: create Valve object
                # then seperate valve into multiple pipes and a valve
                # Assign the first node to source, and the other nodes to destination
                # sources = []
                # destinations = []
                # for i, linknode in enumerate(G.getLinkNodesIndex(connection)):
                #     if i == 0:
                #         sources.append(node_ids[linknode])
                #     else:
                #         destinations.append(node_ids[linknode])

                # joint_obj = {
                #     "id": "Joint" + str(obj_counts["Joint"]),
                #     "type": "Joint",
                #     "contents": content_placeholder,
                #     "tags": {},
                # }
                # nodes["Joint" + str(obj_counts["Joint"])] = joint_obj
                # obj_counts["Joint"] += 1

                # for source in sources:
                #     connection_obj = {
                #         "id": "Pipe" + str(obj_counts["Pipe"]),
                #         "type": "Pipe",
                #         "contents": content_placeholder,
                #         "source": source,
                #         "destination": "Joint" + str(obj_counts["Joint"] - 1),
                #         "tags": {},
                #     }
                #     connections["Pipe" + str(obj_counts["Pipe"])] = connection_obj
                #     obj_counts["Pipe"] += 1

                # for destination in destinations:
                #     connection_obj = {
                #         "id": "Pipe" + str(obj_counts["Pipe"]),
                #         "type": "Pipe",
                #         "contents": content_placeholder,
                #         "source": "Joint" + str(obj_counts["Joint"] - 1),
                #         "destination": destination,
                #         "tags": {},
                #     }
                #     connections["Pipe" + str(obj_counts["Pipe"])] = connection_obj
                #     obj_counts["Pipe"] += 1

            else:
                raise ValueError(
                    f"Connection type {G.getLinkType(connection)} not recognized"
                )
        else:
            type_str = G.getLinkType(connection).upper()
            type_str = type_str[0].upper() + type_str[1:].lower()
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
    args = sys.argv[1:]
    epyt2pypes(args[0], args[1])
    print("EPANET to PYPES conversion from {} to {} complete".format(args[0], args[1]))
