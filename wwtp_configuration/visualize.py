import networkx as nx

def draw_graph(network):
    """Draw all of the nodes and connections in the given network

    Parameters
    ----------
    network : Network
        `Network` object to draw
    """
    # create empty graph
    g = nx.Graph()

    # add list of nodes and edges to graph
    g.add_nodes_from(network.nodes.__iter__())
    # TODO: change color of connection based on contents
    for id, connection in network.connections.items():
        g.add_edge(connection.source.id, connection.sink.id, label=id)

    nx.draw(g, with_labels=True)
