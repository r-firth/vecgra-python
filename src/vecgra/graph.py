"""An in-memory graph dataset with Vecgra import validation."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from pathlib import Path

from .errors import (
    DuplicateNodeError,
    GraphValidationError,
    MissingEndpointError,
    VectorValidationError,
)
from .models import Edge, EdgeModel, ExternalId, Node, NodeModel

_F32_EPSILON = 1.1920928955078125e-7
_F32_MAX_SQRT = 1.844674352395373e19


class Graph:
    """Collect nodes and edges before writing or importing a Vecgra graph."""

    def __init__(self, dimension: int) -> None:
        if not isinstance(dimension, int) or isinstance(dimension, bool) or dimension <= 0:
            raise GraphValidationError("vector dimension must be a positive integer")
        self.dimension = dimension
        self._nodes: dict[ExternalId, Node] = {}
        self._edges: list[Edge] = []

    @property
    def nodes(self) -> tuple[Node, ...]:
        """Return nodes in insertion order."""

        return tuple(self._nodes.values())

    @property
    def edges(self) -> tuple[Edge, ...]:
        """Return edges in insertion order."""

        return tuple(self._edges)

    def add_node(self, node: Node | NodeModel) -> Node:
        """Validate and add one node."""

        record = node if isinstance(node, Node) else node.to_record()
        if record.id in self._nodes:
            raise DuplicateNodeError(record.id)
        self._validate_vectors(record.vectors, f"node {record.id!r}")
        self._nodes[record.id] = record
        return record

    def add_nodes(self, nodes: Iterable[Node | NodeModel]) -> None:
        """Add nodes in iteration order."""

        for node in nodes:
            self.add_node(node)

    def add_edge(self, edge: Edge | EdgeModel) -> Edge:
        """Validate and add one edge. Endpoint checks run before export."""

        record = edge if isinstance(edge, Edge) else edge.to_record()
        self._validate_vectors(record.vectors, f"edge {len(self._edges)}")
        self._edges.append(record)
        return record

    def add_edges(self, edges: Iterable[Edge | EdgeModel]) -> None:
        """Add edges in iteration order."""

        for edge in edges:
            self.add_edge(edge)

    def validate(self) -> None:
        """Check that every edge endpoint names an added node."""

        for index, edge in enumerate(self._edges):
            if edge.source not in self._nodes:
                raise MissingEndpointError(edge.source, index)
            if edge.target not in self._nodes:
                raise MissingEndpointError(edge.target, index)

    def write_jsonl(
        self,
        nodes_path: str | Path,
        edges_path: str | Path,
        *,
        overwrite: bool = False,
    ) -> tuple[Path, Path]:
        """Write compact Vecgra-compatible node and edge JSONL files."""

        self.validate()
        nodes_path = Path(nodes_path)
        edges_path = Path(edges_path)
        if nodes_path.absolute() == edges_path.absolute():
            raise GraphValidationError("node and edge JSONL paths must differ")
        if not overwrite:
            for path in (nodes_path, edges_path):
                if path.exists():
                    raise FileExistsError(path)

        nodes_path.parent.mkdir(parents=True, exist_ok=True)
        edges_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "w" if overwrite else "x"
        created_nodes = False
        try:
            with nodes_path.open(mode, encoding="utf-8", newline="\n") as output:
                created_nodes = True
                self._write_records(output, self.nodes)
            with edges_path.open(mode, encoding="utf-8", newline="\n") as output:
                self._write_records(output, self.edges)
        except Exception:
            if created_nodes and not overwrite:
                nodes_path.unlink(missing_ok=True)
            raise
        return nodes_path, edges_path

    def write_directory(
        self, directory: str | Path, *, overwrite: bool = False
    ) -> tuple[Path, Path]:
        """Write `nodes.jsonl` and `edges.jsonl` below a directory."""

        directory = Path(directory)
        return self.write_jsonl(
            directory / "nodes.jsonl",
            directory / "edges.jsonl",
            overwrite=overwrite,
        )

    def _validate_vectors(self, vectors: list[list[float]], owner: str) -> None:
        for index, vector in enumerate(vectors):
            if len(vector) != self.dimension:
                raise VectorValidationError(
                    f"{owner} vector {index} has dimension {len(vector)}, expected {self.dimension}"
                )
            norm = math.hypot(*vector)
            if norm <= _F32_EPSILON:
                raise VectorValidationError(f"{owner} vector {index} has a near-zero F32 norm")
            if norm > _F32_MAX_SQRT:
                raise VectorValidationError(f"{owner} vector {index} overflows its F32 norm")
            if not math.isfinite(norm):
                raise VectorValidationError(f"{owner} vector {index} has an invalid norm")

    @staticmethod
    def _write_records(output: object, records: Iterable[Node | Edge]) -> None:
        if not hasattr(output, "write"):
            raise TypeError("output must be writable")
        for record in records:
            encoded = json.dumps(
                record.model_dump(mode="json"),
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
            output.write(f"{encoded}\n")
