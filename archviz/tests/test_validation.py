import json
import subprocess
import sys
import textwrap
import pytest

from validation.compare import compare

TRUTH = {
    "nodes": [
        {"id": "gateway", "type": "Service", "expected_rules": ["C1"]},
        {"id": "db", "type": "Database", "expected_rules": ["C2"]},
        {"id": "api:gateway", "type": "API", "expected_rules": ["O1"]},
    ],
    "edges": [
        {"type": "CONNECTS_TO", "from": "gateway", "to": "db", "expected_rules": ["C5"]},
        {"type": "STARTS_AFTER", "from": "gateway", "to": "db", "expected_rules": ["C4"]},
        {"type": "EXPOSES", "from": "gateway", "to": "api:gateway", "expected_rules": ["O2"]},
    ],
    "must_not_exist": [
        {"node": "books", "reason": "алиас"},
        {"type": "EXPOSES", "from": "db", "reason": "у базы нет API"}
    ]
}

def model(nodes, edges, rules=("C1", "C2", "C4", "C5")):
    return {
        "rules_enabled": list(rules),
        "nodes": [{"id": i, "type": t} for i, t in nodes],
        "edges": [{"type": t, "from": a, "to": b} for t, a, b in edges],
    }

FULL_NODES = [("gateway", "Service"), ("db", "Database"), ("api:gateway", "API")]
FULL_EDGES = [("CONNECTS_TO", "gateway", "db"), ("STARTS_AFTER", "gateway", "db"), ("EXPOSES", "gateway", "api:gateway")]

def test_perfect_match():
    c = compare(TRUTH, model(FULL_NODES, FULL_EDGES, rules=("C1", "C2", "C4", "C5", "O1", "O2")))
    for s in (c.nodes, c.edges):
        assert (s.precision, s.recall, s.f1) == (1.0, 1.0, 1.0)
    assert not c.has_errors

def test_missing_extra_per_type():
    c = compare(TRUTH, model(FULL_NODES[:2], [FULL_EDGES[1], ("CALLS", "gateway", "db")]))
    assert c.edges.missing == {FULL_EDGES[0], FULL_EDGES[2]}
    assert c.edges.extra == {("CALLS", "gateway", "db")}
    assert c.edges.precision == 0.5
    assert c.edges.recall == pytest.approx(1 / 3)
    assert c.edge_types["STARTS_AFTER"].recall == 1.0
    assert c.edge_types["CALLS"].precision == 0.0
    assert c.edge_types["CALLS"].recall is None
    assert c.edge_types["EXPOSES"].precision is None

def test_missing_with_unimplemented_rule():
    c = compare(TRUTH, model(FULL_NODES[:2], FULL_EDGES[:2]))
    assert c.deferred == {("api:gateway", "API"), FULL_EDGES[2]}
    assert not c.has_errors

def test_missing_with_implemented_rule():
    c = compare(TRUTH, model(FULL_NODES[:2], FULL_EDGES[1:2]))
    assert c.missing_errors(c.edges) == {FULL_EDGES[0]}
    assert c.has_errors

def test_traps():
    c = compare(TRUTH, model(FULL_NODES + [("books", "Service"), ("extension", "ExternalSystem")], FULL_EDGES + [("EXPOSES", "db", "anything")]))
    assert [trap.get("node", trap.get("type")) for trap, _ in c.traps] == ["books", "EXPOSES"]
    assert c.traps[1][1] == ["db -[EXPOSES] -> anything"]

def test_edge_trap_without_type():
    truth = {"must_not_exist": [{"from": "users-db", "to": "users", "reason": "имя пользователя, а не адрес"}]}
    c = compare(truth, model([], [("CONNECTS_TO", "users-db", "users")]))
    assert c.traps[0][1] == ["users-db -[CONNECTS_TO] -> users"]

def test_wrong_type():
    c = compare(TRUTH, model([("gateway", "Service"), ("db", "Service")], []))
    assert c.retyped == [("db", "Database", "Service")]
    assert ("db", "Database") in c.nodes.missing and ("db", "Service") in c.nodes.extra

def test_cli(tmp_path):
    (tmp_path / "gt.yml").write_text(textwrap.dedent("""
        nodes:
            - {id: a, type: Service, expected_rules: [C1]}
        edges: []
    """), encoding="utf-8")
    (tmp_path / "model.json").write_text(json.dumps(model([("a", "Service")], [])), encoding="utf-8")
    report = tmp_path / "out" / "report.md"
    run = subprocess.run([sys.executable, "-m", "validation", str(tmp_path / "gt.yml"), str(tmp_path / "model.json"), "--report", str(report)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert "| Узлы | 1 | 1 | 1 | 1.00 | 1.00 | 1.00 |" in report.read_text(encoding="utf-8")