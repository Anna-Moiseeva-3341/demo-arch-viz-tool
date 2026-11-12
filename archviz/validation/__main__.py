import argparse
import json
import sys
from pathlib import Path
import yaml

from .compare import compare
from .report import build_report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("truth", type=Path)
    parser.add_argument("model", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    truth = yaml.safe_load(args.truth.read_text(encoding="utf-8")) or {}
    model = json.loads(args.model.read_text(encoding="utf-8"))

    if truth.get("application") and truth["application"] != model.get("application"):
        print(f"Внимание: приложение в эталоне {truth['application']} ", f"в модели {model.get('application')}", file=sys.stderr)

    result = compare(truth, model)
    report = build_report(result, str(args.truth), str(args.model), model)
    print(report)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
    return 1 if result.has_errors else 0

if __name__ == "__main__":
    sys.exit(main())