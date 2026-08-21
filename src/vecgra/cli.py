"""Command-line entry point for Python validation and Vecgra CLI calls."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from .client import VecgraClient
from .errors import VecgraError
from .io import load_jsonl


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vecgra-python")
    parser.add_argument("--binary", default="vecgra", help="path to the vecgra executable")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="validate node and edge JSONL")
    _add_graph_files(validate, include_database=False)

    import_command = commands.add_parser("import", help="validate and import JSONL")
    _add_graph_files(import_command, include_database=True)
    import_command.add_argument("--encoding", choices=("f16", "f32"), default="f16")

    stats = commands.add_parser("stats", help="print database stats as JSON")
    stats.add_argument("database", type=Path)

    check = commands.add_parser("check", help="check a database and print JSON")
    check.add_argument("database", type=Path)

    query = commands.add_parser("query", help="run a focused read-only Cypher query")
    query.add_argument("database", type=Path)
    query.add_argument("cypher")
    return parser


def _add_graph_files(parser: argparse.ArgumentParser, *, include_database: bool) -> None:
    parser.add_argument("nodes", type=Path)
    parser.add_argument("edges", type=Path)
    if include_database:
        parser.add_argument("database", type=Path)
    parser.add_argument("dimension", type=int)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the `vecgra-python` command."""

    arguments = _parser().parse_args(argv)
    client = VecgraClient(binary=arguments.binary)
    try:
        if arguments.command == "validate":
            graph = load_jsonl(arguments.nodes, arguments.edges, arguments.dimension)
            print(json.dumps({"nodes": len(graph.nodes), "edges": len(graph.edges)}))
        elif arguments.command == "import":
            load_jsonl(arguments.nodes, arguments.edges, arguments.dimension)
            result = client.import_jsonl(
                arguments.nodes,
                arguments.edges,
                arguments.database,
                arguments.dimension,
                arguments.encoding,
            )
            print(result.model_dump_json())
        elif arguments.command == "stats":
            print(client.stats(arguments.database).model_dump_json())
        elif arguments.command == "check":
            print(client.check(arguments.database).model_dump_json())
        elif arguments.command == "query":
            print("\n".join(client.query(arguments.database, arguments.cypher)))
        else:
            raise AssertionError(f"unhandled command {arguments.command!r}")
    except (OSError, ValueError, ValidationError, VecgraError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
