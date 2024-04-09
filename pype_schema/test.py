from pype_schema.parse_json import JSONParser
from pype_schema.visualize import draw_graph
import sys
from pype_schema.connection import Pipe

pyvis = False

filename1 = sys.argv[1]
filename2 = sys.argv[2]
filename3 = sys.argv[3]

parser1 = JSONParser(filename1)
sb_net = parser1.initialize_network(name="sb_desal")
parser2 = JSONParser(filename2)
MPDA = parser2.initialize_network(name="MPDA")
parser3 = JSONParser(filename2)
MPDB = parser3.initialize_network(name="MPDB")
parser4 = JSONParser(filename2)
MPDC = parser4.initialize_network(name="MPDC")
parser5 = JSONParser(filename3)
post = parser5.initialize_network(name="Post")

draw_graph(sb_net, pyvis, output_file="vis/sb_net.png")
# draw_graph(post, pyvis, output_file="vis/post.png")
merged_network = parser1.extend_node(
    MPDA, "MPDA", "data/MPD2sb_desal.json", verbose=True, inplace=True
)
# draw_graph(merged_network, pyvis, output_file="vis/merged1.png")
merged_network = parser1.extend_node(
    MPDB, "MPDB", "data/MPD2sb_desal.json", verbose=True, inplace=True
)
# draw_graph(merged_network, pyvis, output_file="vis/merged2.png")
merged_network = parser1.extend_node(
    MPDC, "MPDC", "data/MPD2sb_desal.json", verbose=True, inplace=True
)
merged_network = parser1.extend_node(
    post,
    "PostTreatment",
    "data/PostTreatment2sb_desal.json",
    verbose=True,
    inplace=True,
)
all_pipes = merged_network.get_list_of_type(Pipe)
for p in all_pipes:
    print(p.id, p.source.id, p.destination.id)
for n in merged_network.nodes:
    print(n)
draw_graph(merged_network, pyvis, output_file="vis/merged3.png")
