import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network
from matplotlib.lines import Line2D

color_map = {
    "Electricity": "yellow",
    "UntreatedSewage": "brown",
    "TreatedSewage": "blue",
    "WasteActivatedSludge": "black",
    "PrimarySludge": "black",
    "SludgeBlend": "black",
    "Biogas": "green"
}

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
        try:
            color = color_map[connection.contents.name]
        except KeyError:
            color = "red"

        g.add_edge(connection.source.id, connection.sink.id, color=color, label=id)

    custom_lines = [Line2D([0], [0], color="black", lw=4),
                    Line2D([0], [0], color="brown", lw=4),
                    Line2D([0], [0], color="blue", lw=4),
                    Line2D([0], [0], color="yellow", lw=4),
                    Line2D([0], [0], color="green", lw=4)]
    fig, ax = plt.subplots()
    ax.legend(custom_lines, ["Sludge", "Untreated Sewage", "Treated Sewage", "Electricity", "Biogas"])

    if pyvis:
        nt = Network("500px", "500px")
        nt.from_nx(g)
        nt.show(network.id + ".html")
    else:
        edges = g.edges()
        colors = [g[u][v]["color"] for u,v in edges]
        nx.draw(g, with_labels=True, edge_color=colors)
        plt.axis('off')
        axis = plt.gca()
        axis.set_xlim([1.2*x for x in axis.get_xlim()])
        axis.set_ylim([1.2*y for y in axis.get_ylim()])
        plt.tight_layout()
        plt.show()
        plt.savefig(network.id + ".png")
