import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network
from matplotlib.lines import Line2D

color_map = {
    "Electricity": "yellow",
    "UntreatedSewage": "saddlebrown",
    "PrimaryEffluent": "saddlebrown",
    "SecondaryEffluent": "saddlebrown",
    "TertiaryEffluent": "saddlebrown",
    "TreatedSewage": "green",
    "WasteActivatedSludge": "black",
    "PrimarySludge": "black",
    "TWAS": "black",
    "TPS": "black",
    "Scum": "black",
    "SludgeBlend": "black",
    "ThickenedSludgeBlend": "black",
    "Biogas": "red",
    "GasBlend": "red",
    "NaturalGas": "gray",
    "Seawater": "aqua",
    "Brine": "aqua",
    "SurfaceWater": "cornflowerblue",
    "Groundwater": "cornflowerblue",
    "Stormwater": "cornflowerblue",
    "NonpotableReuse": "purple",
    "DrinkingWater": "blue",
    "PotableReuse": "blue",
    "FatOilGrease": "orange",
    "FoodWaste": "orange",
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
    g = nx.MultiDiGraph()

    # add list of nodes and edges to graph
    g.add_nodes_from(network.nodes.__iter__())
    for id, connection in network.connections.items():
        try:
            color = color_map[connection.contents.name]
        except KeyError:
            color = "red"

        g.add_edge(
            connection.source.id, connection.destination.id, color=color, label=id
        )

        if connection.bidirectional:
            g.add_edge(
                connection.destination.id, connection.source.id, color=color, label=id
            )

    colors = [
        "black",
        "saddlebrown",
        "green",
        "yellow",
        "red",
        "gray",
        "cornflowerblue",
        "aqua",
        "purple",
        "blue",
        "orange",
    ]
    labels = [
        "Sludge/Scum",
        "Untreated Sewage",
        "Treated Sewage",
        "Electricity",
        "Biogas",
        "Natural Gas",
        "Freshwater",
        "Saline Water",
        "Non-potable Reuse",
        "Drinking Water",
        "FOG/Food Waste",
    ]
    font_colors = [
        "white",
        "white",
        "black",
        "black",
        "black",
        "black",
        "black",
        "black",
        "black",
        "white",
        "black",
    ]

    if pyvis:
        nt = Network("500px", "500px", directed=True)

        # create legend based on https://github.com/WestHealth/pyvis/issues/50
        num_legend_nodes = len(colors)
        num_actual_nodes = len(g.nodes())
        step = 50
        x = -300
        y = -250
        legend_nodes = [
            (
                num_actual_nodes + legend_node,
                {
                    "color": colors[legend_node],
                    "label": labels[legend_node],
                    "size": 30,
                    "physics": False,
                    "x": x,
                    "y": f"{y + legend_node*step}px",
                    "shape": "box",
                    "font": {"size": 12, "color": font_colors[legend_node]},
                },
            )
            for legend_node in range(num_legend_nodes)
        ]
        g.add_nodes_from(legend_nodes)

        nt.from_nx(g)
        nt.show(network.id + ".html")
    else:
        # create legend
        custom_lines = []
        for color in colors:
            custom_lines.append(Line2D([0], [0], color=color, lw=4))
        fig, ax = plt.subplots()
        ax.legend(custom_lines, labels)

        edge_colors = []
        edges = g.edges()
        node_to_node = [g[u][v] for u, v in edges]
        for edge_dict in node_to_node:
            for _, edge in edge_dict.items():
                edge_colors.append(edge["color"])

        # TODO: don't draw multiple connections on top of one another
        nx.draw(g, with_labels=True, edge_color=edge_colors)

        plt.axis("off")
        axis = plt.gca()
        axis.set_xlim([1.2 * x for x in axis.get_xlim()])
        axis.set_ylim([1.2 * y for y in axis.get_ylim()])
        plt.tight_layout()
        plt.savefig(network.id + ".png")
