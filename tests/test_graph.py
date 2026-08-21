from __future__ import annotations

import json

import pytest

from vecgra import (
    DuplicateNodeError,
    Edge,
    Graph,
    GraphValidationError,
    MissingEndpointError,
    Node,
    VectorValidationError,
    load_jsonl,
)


def example_graph() -> Graph:
    graph = Graph(2)
    graph.add_node(
        Node(
            id="customer:ada",
            label="Customer",
            properties={"name": "Ada Lovelace", "active": True},
            vectors=[[1.0, 0.0]],
        )
    )
    graph.add_node(
        Node(
            id="product:keyboard",
            label="Product",
            properties={"price": 129.0},
            vectors=[[0.8, 0.2]],
        )
    )
    graph.add_edge(
        Edge(
            source="customer:ada",
            target="product:keyboard",
            label="PURCHASED",
            properties={"quantity": 1},
            vectors=[[0.9, 0.1]],
        )
    )
    return graph


def test_graph_writes_and_loads_compact_jsonl(tmp_path) -> None:  # type: ignore[no-untyped-def]
    graph = example_graph()
    nodes = tmp_path / "nodes.jsonl"
    edges = tmp_path / "edges.jsonl"

    graph.write_jsonl(nodes, edges)
    loaded = load_jsonl(nodes, edges, 2)

    assert loaded.nodes == graph.nodes
    assert loaded.edges == graph.edges
    first = json.loads(nodes.read_text().splitlines()[0])
    assert first["properties"]["name"] == "Ada Lovelace"


def test_graph_refuses_to_overwrite_jsonl(tmp_path) -> None:  # type: ignore[no-untyped-def]
    graph = example_graph()
    nodes = tmp_path / "nodes.jsonl"
    edges = tmp_path / "edges.jsonl"
    nodes.write_text("existing")

    with pytest.raises(FileExistsError):
        graph.write_jsonl(nodes, edges)

    assert nodes.read_text() == "existing"


def test_duplicate_node_ids_fail_on_add() -> None:
    graph = Graph(2)
    graph.add_node(Node(id="same", label="First"))

    with pytest.raises(DuplicateNodeError, match="duplicate node id"):
        graph.add_node(Node(id="same", label="Second"))


def test_missing_endpoints_fail_before_export() -> None:
    graph = Graph(2)
    graph.add_edge(Edge(source="missing", target="missing", label="SELF"))

    with pytest.raises(MissingEndpointError, match="missing node"):
        graph.validate()


@pytest.mark.parametrize("vector", [[1.0], [1.0, 0.0, 0.0]])
def test_vector_dimension_is_database_wide(vector: list[float]) -> None:
    graph = Graph(2)

    with pytest.raises(VectorValidationError, match="expected 2"):
        graph.add_node(Node(id="bad", label="Bad", vectors=[vector]))


def test_zero_cosine_vectors_are_rejected() -> None:
    graph = Graph(2)

    with pytest.raises(VectorValidationError, match="near-zero F32 norm"):
        graph.add_node(Node(id="bad", label="Bad", vectors=[[0.0, 0.0]]))


@pytest.mark.parametrize("vector", [[1e-8, 0.0], [2e19, 0.0]])
def test_cosine_norm_must_be_computable_in_f32(vector: list[float]) -> None:
    graph = Graph(2)

    with pytest.raises(VectorValidationError, match="F32 norm"):
        graph.add_node(Node(id="bad", label="Bad", vectors=[vector]))


@pytest.mark.parametrize("dimension", [0, -1, True, 2.5])
def test_dimension_must_be_a_positive_integer(dimension: object) -> None:
    with pytest.raises(GraphValidationError, match="positive integer"):
        Graph(dimension)  # type: ignore[arg-type]


def test_bad_jsonl_reports_file_and_line(tmp_path) -> None:  # type: ignore[no-untyped-def]
    nodes = tmp_path / "nodes.jsonl"
    edges = tmp_path / "edges.jsonl"
    nodes.write_text("\n{not json}\n")
    edges.write_text("")

    with pytest.raises(GraphValidationError, match=r"nodes\.jsonl:2"):
        load_jsonl(nodes, edges, 2)
