import json
import pytest
from loader.__main__ import checked, to_neo4j_props, NODE_TYPES

def test_nested_valued_to_json():
    node = {"id": "gateway", "type": "Service", "ports": ["8080:8000"], "rules": ["C1", "C6"], "provenance": [{"rule": "C1", "source": "docker-compose.yml"}]}
    props = to_neo4j_props(node, "library")
    assert props["ports"] == ["8080:8000"]
    assert props["rules"] == ["C1", "C6"]
    assert json.loads(props["provenance"])[0]["rule"] == "C1"
    assert props["application"] == "library"
    assert "id" not in props and "type" not in props

def test_name():
    assert to_neo4j_props({"id": "users", "type": "Service"}, "app")["name"] == "users"
    assert to_neo4j_props({"id": "api:users", "type": "API", "name": "Users API"}, "app")["name"] == "Users API"
    assert "name" not in to_neo4j_props({"type": "CALLS", "from": "a", "to": "b"}, "app")

def test_unknown_label():
    assert checked("Service", NODE_TYPES, "тип узла") == "Service"
    with pytest.raises(ValueError):
        checked("Service) DETACH DELETE (x", NODE_TYPES, "тип узла")