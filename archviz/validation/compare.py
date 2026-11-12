from dataclasses import dataclass

def node_key(node):
    return node["id"], node["type"]

def edge_key(edge):
    return edge["type"], edge["from"], edge["to"]

def show_node(key):
    return f"{key[0]} ({key[1]})"

def show_edge(key):
    return f"{key[1]} -[{key[0]}] -> {key[2]}"

@dataclass
class Score:
    truth: set
    found: set

    @property
    def correct(self):
        return self.truth & self.found

    @property
    def missing(self):
        return self.truth - self.found

    @property
    def extra(self):
        return self.found - self.truth

    @property
    def precision(self):
        return len(self.correct) / len(self.found) if self.found else None
    
    @property
    def recall(self):
        return len(self.correct) / len(self.truth) if self.truth else None

    @property
    def f1(self):
        denominator = len(self.truth) + len(self.found)
        return 2 * len(self.correct) / denominator if denominator else None

def split_by_type(score, type_of):
    types = sorted({type_of(k) for k in score.truth | score.found})
    return {
        t: Score({k for k in score.truth if type_of(k) == t}, {k for k in score.found if type_of(k) == t}) for t in types
    }

@dataclass
class Comparison:
    nodes: Score
    edges: Score
    node_types: dict
    edge_types: dict
    deferred: set
    expected_rules: dict
    retyped: list
    traps: list

    def missing_errors(self, score):
        return score.missing - self.deferred

    @property
    def has_errors(self):
        return bool(self.traps or self.nodes.extra or self.edges.extra or self.missing_errors(self.nodes) or self.missing_errors(self.edges))

def check_traps(traps, found_nodes, found_edges):
    hits = []
    for trap in traps:
        if "node" in trap:
            matched = [show_node(k) for k in sorted(found_nodes) if k[0] == trap["node"]]
        else:
            matched = [show_edge(k) for k in sorted(found_edges) if all(trap[field] == value for field, value in zip(("type", "from", "to"), k) if field in trap)]
        if matched:
            hits.append((trap, matched))
    return hits

def compare(truth, model):
    truth_nodes = {node_key(n): n for n in truth.get("nodes", [])}
    truth_edges = {edge_key(e): e for e in truth.get("edges", [])}
    found_nodes = {node_key(n) for n in model.get("nodes", [])}
    found_edges = {edge_key(e) for e in model.get("edges", [])}

    nodes = Score(set(truth_nodes), found_nodes)
    edges = Score(set(truth_edges), found_edges)
    expected_rules = {k: v.get("expected_rules", []) for k, v in (truth_nodes | truth_edges).items()}

    deferred = set()
    if "rules_enabled" in model:
        enabled = set(model["rules_enabled"])
        deferred = {k for k in nodes.missing | edges.missing if expected_rules[k] and not enabled & set(expected_rules[k])}

    truth_types = {node_id: t for node_id, t in truth_nodes}
    retyped = sorted({(node_id, truth_types[node_id], t) for node_id, t in nodes.extra if node_id in truth_types and truth_types[node_id] != t})

    return Comparison(
        nodes=nodes,
        edges=edges,
        node_types=split_by_type(nodes, lambda k: k[1]),
        edge_types=split_by_type(edges, lambda k: k[0]),
        deferred=deferred,
        expected_rules=expected_rules,
        retyped=retyped,
        traps=check_traps(truth.get("must_not_exist", []), found_nodes, found_edges),
    )