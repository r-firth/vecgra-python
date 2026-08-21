"""Read Vecgra node and edge JSONL into validated Python models."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from .errors import JsonlValidationError
from .graph import Graph
from .models import Edge, Node

Record = TypeVar("Record", bound=BaseModel)


def load_jsonl(
    nodes_path: str | Path,
    edges_path: str | Path,
    dimension: int,
) -> Graph:
    """Load, validate, and return a graph from Vecgra-compatible JSONL."""

    graph = Graph(dimension)
    graph.add_nodes(_records(Path(nodes_path), Node))
    graph.add_edges(_records(Path(edges_path), Edge))
    graph.validate()
    return graph


def _records(path: Path, model: type[Record]) -> Iterator[Record]:
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
                yield model.model_validate(value)
            except (json.JSONDecodeError, ValidationError) as error:
                raise JsonlValidationError(path, line_number, str(error)) from error
