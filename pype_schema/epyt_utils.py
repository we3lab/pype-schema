from epyt import epanet
import json
import numpy as np

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


def epyt2pypes(inp_file, out_file, name):
    """Convert an EPANET input file to a PYPES JSON file

    Parameters
    ----------
    inp_file : str
        Path to the EPANET input file

    out_file : str
        Path to the PYPES JSON file
    """

    G = epanet(inp_file)

    node_ids = {}
    connection_ids = {}
    nodes = []
    connections = []

    for n in G.getNodeIndex():
        # Node type is one of: Junction, Reservoir, Tank
        if G.getNodeType(n) == "JUNCTION":
            node_obj = {
                "id": "Joint" + str(n),
                "type": "Joint",
                "contents": content_placeholder,
                "tags": {},
            }
            node_ids[n] = "Joint" + str(n)
        elif G.getNodeType(n) == "RESERVOIR":
            node_obj = {
                "id": "Reservoir" + str(n),
                "type": "Reservoir",
                "contents": content_placeholder,
                "levation (meters)": G.getNodeElevations(n),
                "tags": {},
            }
            node_ids[n] = "Reservoir" + str(n)
        elif G.getNodeType(n) == "TANK":
            node_obj = {
                "id": "Tank" + str(n),
                "type": "Tank",
                "contents": content_placeholder,
                "levation (meters)": G.getNodeElevations(n),
                "volume (cubic meters)": G.getNodeTankVolume(n),
                "tags": {},
            }
            node_ids[n] = "Tank" + str(n)
        else:
            raise ValueError(f"Node type {G.getNodeType(n)} not recognized")
        nodes.append(node_obj)

    for connection in G.getLinkIndex():
        # Link type is one of: Pipe, Pump, Valve
        if G.getLinkType(connection) == "PIPE":
            connection_obj = {
                "id": "Pipe" + str(connection),
                "type": "Pipe",
                "contents": content_placeholder,
                "source": node_ids[G.getLinkNodesIndex(connection)[0]],
                "destination": node_ids[G.getLinkNodesIndex(connection)[1]],
                "tags": {},
            }
            connection_ids[connection] = "Pipe" + str(connection)
        elif G.getLinkType(connection) == "PUMP":
            connection_obj = {
                "id": "Pipe" + str(connection),
                "type": "Pipe",
                "contents": content_placeholder,
                "source": node_ids[G.getLinkNodesIndex(connection)[0]],
                "destination": node_ids[G.getLinkNodesIndex(connection)[1]],
                "tags": {},
            }
            connection_ids[connection] = "Pipe" + str(connection)
        elif G.getLinkType(connection) == "RESERVOIR":
            connection_obj = {
                "id": "Pipe" + str(connection),
                "type": "Pipe",
                "contents": content_placeholder,
                "source": node_ids[G.getLinkNodesIndex(connection)[0]],
                "destination": node_ids[G.getLinkNodesIndex(connection)[1]],
                "tags": {},
            }
            connection_ids[connection] = "Pipe" + str(connection)
        else:
            raise ValueError(
                f"Connection type {G.getLinkType(connection)} not recognized"
            )
        connections.append(connection_obj)

    data = {
        "nodes": list(node_ids.values()),
        "connections": list(connection_ids.values()),
        "virtual_tags": {},
    }
    for node in nodes:
        temp_node = node.copy()
        temp_node.pop("id")
        data[node["id"]] = temp_node
    for connection in connections:
        temp_connection = connection.copy()
        temp_connection.pop("id")
        data[connection["id"]] = temp_connection

    with open(out_file, "w") as f:
        json.dump(data, f, indent=2, cls=NpEncoder)


if __name__ == "__main__":
    epyt2pypes(
        "data/WDS/EPANET Net 3.inp", "data/WDS/EPANET Net 3.json", name="EPANET Net 3"
    )
    print("EPANET to PYPES conversion complete.")
