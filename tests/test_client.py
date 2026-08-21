from __future__ import annotations

import os
from pathlib import Path

import pytest

from vecgra import Edge, Graph, Node, VecgraClient, VecgraCommandError


def test_client_parses_version_stats_and_check(monkeypatch: pytest.MonkeyPatch) -> None:
    outputs = {
        ("vecgra", "--version"): "vecgra 0.1.1\n",
        ("vecgra", "stats", "graph.vg"): (
            "path\tgraph.vg\nnodes\t3\nedges\t2\nsymbols\t9\nvectors\t5\n"
            "transactions\t1\ndimension\t4\nsimilarity\tCosine\nvector_encoding\tF16\n"
        ),
        ("vecgra", "check", "graph.vg"): (
            "status\tok\nnodes\t3\nedges\t2\nvectors\t5\ntransactions\t1\n"
            "vector_bytes_verified\t40\nvector_checksum_blocks_verified\t1\n"
            "elapsed_ms\t0.066\n"
        ),
    }

    def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
        del kwargs
        return __import__("subprocess").CompletedProcess(command, 0, outputs[tuple(command)], "")

    monkeypatch.setattr("subprocess.run", fake_run)
    client = VecgraClient()

    assert client.version() == "0.1.1"
    assert client.stats("graph.vg").dimension == 4
    assert client.check("graph.vg").status == "ok"


def test_import_graph_uses_temporary_jsonl(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen: list[list[str]] = []

    def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
        del kwargs
        seen.append(command)
        assert Path(command[2]).read_text()
        assert Path(command[3]).read_text() == ""
        return __import__("subprocess").CompletedProcess(
            command, 0, "nodes\t1\nedges\t0\nvectors\t1\n", ""
        )

    monkeypatch.setattr("subprocess.run", fake_run)
    graph = Graph(2)
    graph.add_node(Node(id="one", label="Example", vectors=[[1.0, 0.0]]))

    result = VecgraClient().import_graph(graph, tmp_path / "graph.vg")

    assert (result.nodes, result.edges, result.vectors) == (1, 0, 1)
    assert seen[0][1] == "import-jsonl"


def test_command_failures_include_vecgra_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
        del kwargs
        return __import__("subprocess").CompletedProcess(command, 1, "", "error: bad graph\n")

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(VecgraCommandError, match="bad graph"):
        VecgraClient().stats("bad.vg")


@pytest.mark.skipif("VECGRA_TEST_BINARY" not in os.environ, reason="real Vecgra binary not set")
def test_real_vecgra_import_and_query(tmp_path: Path) -> None:
    graph = Graph(2)
    graph.add_node(Node(id="a", label="Thing", properties={"name": "A"}, vectors=[[1.0, 0.0]]))
    graph.add_node(Node(id="b", label="Thing", properties={"name": "B"}, vectors=[[0.8, 0.2]]))
    graph.add_edge(Edge(source="a", target="b", label="LINKS", vectors=[[0.9, 0.1]]))
    client = VecgraClient(binary=os.environ["VECGRA_TEST_BINARY"])
    database = tmp_path / "graph.vg"

    imported = client.import_graph(graph, database)
    rows = client.query(
        database,
        "MATCH (a:Thing)-[r:LINKS]->(b:Thing) RETURN a,r,b LIMIT 10",
    )

    assert (imported.nodes, imported.edges, imported.vectors) == (2, 1, 3)
    assert len(rows) == 1
    assert "LINKS" in rows[0]
