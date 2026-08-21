"""Typed Python models and CLI integration for Vecgra."""

from .client import CheckResult, DatabaseStats, ImportResult, VecgraClient
from .errors import (
    DuplicateNodeError,
    GraphValidationError,
    JsonlValidationError,
    MissingEndpointError,
    VecgraCommandError,
    VecgraError,
    VectorValidationError,
)
from .graph import Graph
from .io import load_jsonl
from .models import Edge, EdgeModel, ExternalId, JsonScalar, Node, NodeModel

__all__ = [
    "CheckResult",
    "DatabaseStats",
    "DuplicateNodeError",
    "Edge",
    "EdgeModel",
    "ExternalId",
    "Graph",
    "GraphValidationError",
    "ImportResult",
    "JsonScalar",
    "JsonlValidationError",
    "MissingEndpointError",
    "Node",
    "NodeModel",
    "VecgraClient",
    "VecgraCommandError",
    "VecgraError",
    "VectorValidationError",
    "load_jsonl",
]

__version__ = "0.1.0"
