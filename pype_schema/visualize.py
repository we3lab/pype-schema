import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network
from matplotlib.lines import Line2D
from collections import defaultdict

# flow contents to (edge color, text color) mapping
color_map = {
    "Electricity": ("yellow", "black"),
    "UntreatedSewage": ("saddlebrown", "white"),
    "PrimaryEffluent": ("saddlebrown", "white"),
    "SecondaryEffluent": ("saddlebrown", "white"),
    "TertiaryEffluent": ("saddlebrown", "white"),
    "TreatedSewage": ("green", "black"),
    "WasteActivatedSludge": ("black", "white"),
    "PrimarySludge": ("black", "white"),
    "TWAS": ("black", "white"),
    "TPS": ("black", "white"),
    "Scum": ("black", "white"),
    "SludgeBlend": ("black", "white"),
    "ThickenedSludgeBlend": ("black", "white"),
    "Biogas": ("red", "black"),
    "GasBlend": ("red", "black"),
    "NaturalGas": ("gray", "black"),
    "Seawater": ("aqua", "black"),
    "Brine": ("aqua", "black"),
    "SurfaceWater": ("cornflowerblue", "black"),
    "Groundwater": ("cornflowerblue", "black"),
    "Stormwater": ("cornflowerblue", "black"),
    "NonpotableReuse": ("purple", "black"),
    "DrinkingWater": ("blue", "white"),
    "PotableReuse": ("blue", "white"),
    "FatOilGrease": ("orange", "black"),
    "FoodWaste": ("orange", "black"),
}


def draw_graph(network, pyvis=False, output_file=None):
    """Draw all of the nodes and connections in the given network

    Parameters
    ----------
    network : Network
        `Network` object to draw

    pyvis : bool
        Whether to draw the graph with PyVis or Networkx.
        False (networkx) by default

    output_file : str
        Path to the desired output.
        Default is None, meaning the file will be saved as `networkd.id` + extension
    """
    # create empty graph
    g = nx.MultiDiGraph()

    # add list of nodes and edges to graph
    g.add_nodes_from(network.nodes.__iter__())

    flow_colors = defaultdict(str)
    font_colors = defaultdict(str)
    for id, connection in network.connections.items():
        try:
            flow_color = color_map[connection.contents.name][0]
            font_color = color_map[connection.contents.name][1]
        except KeyError:
            flow_color = "black"
            font_color = "white"

        flow_colors[connection.contents.name] = flow_color
        font_colors[connection.contents.name] = font_color

        g.add_edge(
            connection.source.id, connection.destination.id, color=flow_color, label=id
        )

        if connection.bidirectional:
            g.add_edge(
                connection.destination.id,
                connection.source.id,
                color=flow_color,
                label=id,
            )

    colors = list(flow_colors.values())
    labels = list(flow_colors.keys())
    if pyvis:
        nt = Network("500px", "500px", directed=True, notebook=False)

        # create legend based on https://github.com/WestHealth/pyvis/issues/50
        num_legend_nodes = len(flow_colors)
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
        if output_file:
            nt.show(output_file, notebook=False)
        else:
            nt.show(network.id + ".html", notebook=False)
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
        if output_file:
            plt.savefig(output_file)
        else:
            plt.savefig(network.id + ".png")
