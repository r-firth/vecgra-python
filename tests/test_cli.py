from __future__ import annotations

import json
from pathlib import Path

from vecgra import Edge, Graph, Node
from vecgra.cli import main


def _fake_binary(tmp_path: Path) -> Path:
    binary = tmp_path / "vecgra"
    binary.write_text(
        """#!/usr/bin/env python3
import sys

command = sys.argv[1]
if command == "import-jsonl":
    print("nodes\\t2")
    print("edges\\t1")
    print("vectors\\t3")
elif command == "stats":
    print(f"path\\t{sys.argv[2]}")
    print("nodes\\t2")
    print("edges\\t1")
    print("symbols\\t4")
    print("vectors\\t3")
    print("transactions\\t1")
    print("dimension\\t2")
    print("similarity\\tCosine")
    print("vector_encoding\\tF16")
elif command == "check":
    print("status\\tok")
    print("nodes\\t2")
    print("edges\\t1")
    print("vectors\\t3")
    print("transactions\\t1")
    print("vector_bytes_verified\\t12")
    print("vector_checksum_blocks_verified\\t1")
    print("elapsed_ms\\t0.1")
elif command == "query":
    print("0:Thing A -[0:LINKS]-> 1:Thing B")
else:
    print(f"unknown command {command}", file=sys.stderr)
    raise SystemExit(1)
"""
    )
    binary.chmod(0o755)
    return binary


def _graph_files(tmp_path: Path) -> tuple[Path, Path]:
    graph = Graph(2)
    graph.add_node(Node(id="a", label="Thing", vectors=[[1.0, 0.0]]))
    graph.add_node(Node(id="b", label="Thing", vectors=[[0.8, 0.2]]))
    graph.add_edge(Edge(source="a", target="b", label="LINKS", vectors=[[0.9, 0.1]]))
    return graph.write_directory(tmp_path / "data")


def test_cli_validation_import_and_read_commands(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    binary = _fake_binary(tmp_path)
    nodes, edges = _graph_files(tmp_path)
    common = ["--binary", str(binary)]

    assert main([*common, "validate", str(nodes), str(edges), "2"]) == 0
    assert json.loads(capsys.readouterr().out) == {"nodes": 2, "edges": 1}

    database = tmp_path / "graph.vg"
    assert (
        main(
            [
                *common,
                "import",
                str(nodes),
                str(edges),
                str(database),
                "2",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == {"nodes": 2, "edges": 1, "vectors": 3}

    assert main([*common, "stats", str(database)]) == 0
    assert json.loads(capsys.readouterr().out)["dimension"] == 2

    assert main([*common, "check", str(database)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"

    assert main([*common, "query", str(database), "MATCH ..."]) == 0
    assert "LINKS" in capsys.readouterr().out


def test_cli_reports_validation_errors(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    nodes = tmp_path / "nodes.jsonl"
    edges = tmp_path / "edges.jsonl"
    nodes.write_text("not json\n")
    edges.write_text("")

    assert main(["validate", str(nodes), str(edges), "2"]) == 1
    assert "nodes.jsonl:1" in capsys.readouterr().err
