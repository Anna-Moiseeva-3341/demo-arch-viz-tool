import argparse
import sys
import json
from collections import Counter
from pathlib import Path

from . import compose
from .model import Graph

SCHEMA_VERSION = "0.1"

def main():
    parser = argparse.ArgumentParser(prog="extractor", description="Извлечение архитектурной модели из артефактов проекта")
    parser.add_argument("project", type=Path, help="каталог анализируемого проекта")
    parser.add_argument("-o", "--output", type=Path, default=Path("out/model.json"))
    args = parser.parse_args()

    graph = Graph()
    info = compose.extract(args.project, graph)
    rules_enabled = compose.IMPLEMENTED_RULES

    model = graph.to_dict(SCHEMA_VERSION, info.application, rules_enabled)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8")

    nodes = Counter(n["type"] for n in model["nodes"])
    edges = Counter(e["type"] for e in model["edges"])
    print(f"Приложение: {model['application']}; правила: {', '.join(model['rules_enabled'])}")
    print(f"Узлов: {len(model['nodes'])} ({', '.join(f'{t} {c}' for t, c in sorted(nodes.items()))})")
    print(f"Связей: {len(model['edges'])} ({', '.join(f'{t} {c}' for t, c in sorted(edges.items()))})")
    for fact in model["unresolved"]:
        print(f"Не сопоставлен с компонентом: {fact['service']}.{fact['variable']} -> {fact['host']}")
    for warning in model["warnings"]:
        print(f"ПРЕДУПРЕЖДЕНИЕ: {warning}", file=sys.stderr)
    print(f"Модель записана в {args.output}")
    return 0

if __name__ == "__main__":
    sys.exit(main())