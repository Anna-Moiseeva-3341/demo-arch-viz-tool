from .rules import EXPLICIT, INFERRED, RULES

def _merge_props(target, props):
    for key, value in props.items():
        if isinstance(value, list) and isinstance(target.get(key), list):
            target[key] += [v for v in value if v not in target[key]]
        else:
            target[key] = value

def _add_provenance(element, rule, source):
    if rule not in RULES:
        raise KeyError(f"Неизвестное правило {rule}: добавьте его в rules.py")
    entry = {"rule": rule, "source": source}
    if entry not in element["provenance"]:
        element["provenance"].append(entry)

def _summary(element):
    rules = sorted({p["rule"] for p in element["provenance"]})
    explicit = any(RULES[r][1] == EXPLICIT for r in rules)
    return {
        "rules": rules,
        "confidence": EXPLICIT if explicit else INFERRED,
        "provenance": element["provenance"],
    }

class Graph:
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.warnings = []
        self.unresolved = []

    def add_node(self, node_id, node_type, rule, source, **props):
        node = self.nodes.setdefault(node_id, {"type": node_type, "props": {}, "provenance": []})
        if node["type"] != node_type:
            self.warn(f"узел {node_id}: правило {rule} дает тип {node_type}, а уже есть {node['type']}")
            return
        _merge_props(node["props"], props)
        _add_provenance(node, rule, source)

    def add_edge(self, edge_type, src, dst, rule, source, **props):
        edge = self.edges.setdefault((edge_type, src, dst), {"props": {}, "provenance": []})
        _merge_props(edge["props"], props)
        _add_provenance(edge, rule, source)

    def warn(self, message):
        self.warnings.append(message)

    def add_unresolved(self, **fact):
        if fact not in self.unresolved:
            self.unresolved.append(fact)

    def to_dict(self, schema_version, application, rules_enabled):
        warnings = list(self.warnings)
        for edge_type, src, dst in self.edges:
            if src not in self.nodes or dst not in self.nodes:
                warnings.append(f"связь {src} -[{edge_type}]-> {dst} ссылается на несуществующий узел")
        return {
            "schema_version": schema_version,
            "application": application,
            "rules_enabled": sorted(rules_enabled),
            "nodes": [
                {"id": node_id, "type": n["type"], **n["props"], **_summary(n)}
                for node_id, n in sorted(self.nodes.items())
            ],
            "edges": [
                {"type": t, "from": s, "to": d, **e["props"], **_summary(e)}
                for (t, s, d), e in sorted(self.edges.items())
            ],
            "warnings": warnings,
            "unresolved": self.unresolved,
        }