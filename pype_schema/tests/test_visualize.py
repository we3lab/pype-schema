import os
import pytest
from pype_schema.parse_json import JSONParser
from pype_schema.visualize import draw_graph

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# set skip_all_tests = True to focus on single test
skip_all_tests = False


@pytest.mark.skipif(skip_all_tests, reason="Exclude all tests")
@pytest.mark.parametrize(
    "json_path, node_id, pyvis, outpath",
    [
        ("../data/wrrf_sample.json", None, False, None),
        ("../data/wrrf_sample.json", "WWTP", False, None),
        ("../data/wrrf_sample.json", "RecycledWaterFacility", False, None),
        ("../data/wrrf_sample.json", None, True, None),
        ("../data/wrrf_sample.json", "WWTP", True, None),
        ("../data/wrrf_sample.json", "RecycledWaterFacility", True, "wrrf.html"),
        ("../data/wrrf_sample.json", "RecycledWaterFacility", False, "wrrf.png"),
    ],
)
def test_draw_graph(json_path, node_id, pyvis, outpath):
    parser = JSONParser(json_path)
    graph = parser.initialize_network()
    if node_id is None:
        draw_graph(graph, pyvis, output_file=outpath)
    else:
        draw_graph(graph.get_node(node_id), pyvis, output_file=outpath)
