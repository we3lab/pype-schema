import os
import pytest
import pickle
from wwtp_configuration.parse_json import JSONParser
from wwtp_configuration.visualize import draw_graph

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, expected",
    [
        ("../data/svcw.json", None),
        ("../data/svcw.json", "SVCW"),
    ],
)
def test_create_network(json_path, expected):
    parser = JSONParser(json_path)
    graph = parser.initialize_network()
    if node_id is None:
        result = draw_graph(graph)
    else:
        result = draw_graph(graph.get_node(node_id))
    assert result == expected
