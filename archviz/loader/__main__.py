import argparse
import json
import os
import sys
from pathlib import Path

from neo4j import GraphDatabase

NODE_TYPES = {"Application", "Service", "Database", "MessageBroker", "Queue", "API", "Endpoint", "ExternalSystem"}
EDGE_TYPES = {"CONTAINS", "EXPOSES", "HAS_ENDPOINT", "CALLS", "CONNECTS_TO", "PUBLISHES_TO", "SUBSCRIBES_TO", "HOSTED_ON", "STARTS_AFTER"}
STRUCTURE_KEYS = {"id", "type", "from", "to"}

def checked(value, allowed, what):
    if value not in allowed:
        raise ValueError(f"Неизвестный {what}: {value}")
    return value

def to_neo4j_props(element, application):
    props = {"application": application}
    for key, value in element.items():
        if key in STRUCTURE_KEYS or value is None:
            continue
        nested = isinstance(value, dict) or (
            isinstance(value, list) and any(isinstance(v, (dict, list)) for v in value)
        )
        props[key] = json.dumps(value, ensure_ascii=False) if nested else value
    if "id" in element and "from" not in element:
        props.setdefault("name", element["id"])
    return props

def load(tx, model, clear):
    app = model["application"]
    if clear:
        tx.run("MATCH (n:Element {application: $app}) DETACH DELETE n", app=app)

    for node in model["nodes"]:
        label = checked(node["type"], NODE_TYPES, "тип узла")
        tx.run(
            f"MERGE (n:Element {{application: $app, id: $id}}) SET n:{label}, n += $props",
            app=app, id=node["id"], props=to_neo4j_props(node, app),
        )

    missing = []
    for edge in model["edges"]:
        rel = checked(edge["type"], EDGE_TYPES, "тип связи")
        record = tx.run(
            "MATCH (a:Element {application: $app, id: $src}) "
            "MATCH (b:Element {application: $app, id: $dst}) "
            f"MERGE (a)-[r:{rel}]->(b) SET r += $props "
            "RETURN count(r) AS loaded",
            app=app, src=edge["from"], dst=edge["to"], props=to_neo4j_props(edge, app),
        ).single()
        if record["loaded"] == 0:
            missing.append(f"{edge['from']} -[{rel}]-> {edge['to']}")
    return missing

def main():
    parser = argparse.ArgumentParser(prog="loader", description="Загрузка модели в Neo4j")
    parser.add_argument("model", type=Path)
    parser.add_argument("--uri", default="bolt://localhost:7687")
    parser.add_argument("--user", default="neo4j")
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD", "archviz-pass"))
    parser.add_argument("--keep", action="store_true", help="не удалять предыдущую загрузку приложения")
    args = parser.parse_args()

    model = json.loads(args.model.read_text(encoding="utf-8"))
    with GraphDatabase.driver(args.uri, auth=(args.user, args.password)) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            session.run("CREATE INDEX element_key IF NOT EXISTS FOR (n:Element) ON (n.application, n.id)")
            missing = session.execute_write(load, model, not args.keep)
        print(f"Загружено в Neo4j: приложение {model['application']}, "
              f"узлов {len(model['nodes'])}, связей {len(model['edges']) - len(missing)}")
        for edge in missing:
            print(f"ПРЕДУПРЕЖДЕНИЕ: связь не загружена, нет узла {edge}", file=sys.stderr)
        print("Откройте http://localhost:7474 и выполните желаемые запросы")
        return 0

if __name__ == "__main__":
    sys.exit(main())