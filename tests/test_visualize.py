import os
import pytest
from wwtp_configuration.parse_json import JSONParser
from wwtp_configuration.visualize import draw_graph

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, node_id, pyvis",
    [
        ("../data/svcw.json", None, False),
        ("../data/svcw.json", None, True),
        ("../data/svcw.json", "SVCW", False),
        ("../data/svcw.json", "SVCW", True),
        ("../data/sb.json", None, True),
        ("../data/sb.json", "ElEstero", True),
        ("../data/sb.json", "RecycledWater", True),
    ],
)
def test_create_network(json_path, node_id, pyvis):
    parser = JSONParser(json_path)
    graph = parser.initialize_network()
    if node_id is None:
        draw_graph(graph, pyvis)
    else:
        draw_graph(graph.get_node(node_id), pyvis)
