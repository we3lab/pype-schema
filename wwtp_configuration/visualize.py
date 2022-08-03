import networkx as nx
from pyvis.network import Network

def draw_graph(network, pyvis=False):
    """Draw all of the nodes and connections in the given network

    Parameters
    ----------
    network : Network
        `Network` object to draw

    pyvis : bool
        Whether to draw the graph with PyVis or Networkx.
        False (networkx) by default
    """
    # create empty graph
    g = nx.Graph()

    # add list of nodes and edges to graph
    g.add_nodes_from(network.nodes.__iter__())
    # TODO: change color of connection based on contents
    for id, connection in network.connections.items():
        g.add_edge(connection.source.id, connection.sink.id, label=id)

    if pyvis:
        nt = Network('500px', '500px')
        nt.from_nx(g)
        nt.show("config.html")
    else:
        nx.draw(g, with_labels=True)
