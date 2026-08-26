from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .ontology import OntologySearch
from .retrieval import ExampleRetriever
from .services import DDBotToolkit


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ddbot", description="DWIS domain tools for coding agents")
    parser.add_argument("--ontology", type=Path, help="override the bundled DWIS ontology")
    commands = parser.add_subparsers(dest="command", required=True)

    ontology = commands.add_parser("ontology", help="search ontology classes and properties")
    ontology.add_argument("query")
    ontology.add_argument("--kind", choices=("all", "class", "property"), default="all")
    ontology.add_argument("--limit", type=int, default=10)

    examples = commands.add_parser("examples", help="retrieve example DWIS configurations")
    examples.add_argument("query")
    examples.add_argument("--corpus", type=Path, help="example corpus JSONL to search")
    examples.add_argument("--limit", type=int, default=5)

    validate = commands.add_parser("validate", help="validate a DWIS DSL configuration")
    validate.add_argument("config", nargs="?", type=Path, help="file to validate; stdin when omitted")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "ontology":
            result = [
                match.to_dict()
                for match in OntologySearch(args.ontology).search(
                    args.query, kind=args.kind, limit=args.limit
                )
            ]
            payload: object = {"query": args.query, "matches": result}
            exit_code = 0
        elif args.command == "examples":
            result = [
                match.to_dict()
                for match in ExampleRetriever(args.corpus).search(args.query, limit=args.limit)
            ]
            payload = {"query": args.query, "matches": result}
            exit_code = 0
        else:
            config = args.config.read_text(encoding="utf-8") if args.config else sys.stdin.read()
            payload = DDBotToolkit(ontology=args.ontology).validate(config)
            exit_code = 0 if payload["valid"] else 1
    except (OSError, ValueError) as exc:
        payload = {"error": str(exc)}
        exit_code = 2
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return exit_code
