from extractor.model import Graph

def test_edge_found_by_two_rules():
    g = Graph()
    g.add_node("a", "Service", "C1", "compose")
    g.add_node("b", "Service", "C1", "compose")
    g.add_edge("CALLS", "a", "b", "C5", "compose")
    g.add_edge("CALLS", "a", "b", "C4", "compose")
    edges = g.to_dict("0.1", "app", [])["edges"]
    assert len(edges) == 1
    assert edges[0]["rules"] == ["C4", "C5"]

def test_explicit_rule_explicit_element():
    g = Graph()
    g.add_edge("CALLS", "a", "b", "C5", "compose")
    assert g.to_dict("0.1", "app", [])["edges"][0]["confidence"] == "inferred"
    g.add_edge("CALLS", "a", "b", "C4", "compose")
    assert g.to_dict("0.1", "app", [])["edges"][0]["confidence"] == "explicit"

def test_list_props_merged():
    g = Graph()
    g.add_node("a", "Service", "C7", "compose", aliases=["x"])
    g.add_node("a", "Service", "C7", "compose", aliases=["x", "y"])
    assert g.to_dict("0.1", "app", [])["nodes"][0]["aliases"] == ["x", "y"]

def test_warning_edge():
    g = Graph()
    g.add_node("a", "Service", "C1", "compose")
    g.add_edge("STARTS_AFTER", "a", "missing", "C4", "compose")
    assert g.to_dict("0.1", "app", [])["warnings"]