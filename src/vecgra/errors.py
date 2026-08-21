"""Exceptions raised by the Vecgra Python package."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path


class VecgraError(Exception):
    """Base exception for this package."""


class GraphValidationError(VecgraError, ValueError):
    """A graph cannot be represented by Vecgra's JSONL importer."""


class DuplicateNodeError(GraphValidationError):
    """Two nodes use the same external ID."""

    def __init__(self, external_id: str | int) -> None:
        super().__init__(f"duplicate node id {external_id!r}")
        self.external_id = external_id


class MissingEndpointError(GraphValidationError):
    """An edge refers to a node that is not in the graph."""

    def __init__(self, endpoint: str | int, edge_index: int) -> None:
        super().__init__(f"edge {edge_index} refers to missing node {endpoint!r}")
        self.endpoint = endpoint
        self.edge_index = edge_index


class VectorValidationError(GraphValidationError):
    """A vector has an invalid dimension or component."""


class JsonlValidationError(GraphValidationError):
    """A JSONL record is invalid."""

    def __init__(self, path: Path, line: int, message: str) -> None:
        super().__init__(f"{path}:{line}: {message}")
        self.path = path
        self.line = line


class VecgraCommandError(VecgraError):
    """The Vecgra executable was missing, timed out, or returned an error."""

    def __init__(
        self,
        command: Sequence[str],
        returncode: int | None,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        rendered = " ".join(command)
        if returncode is None:
            message = f"could not run {rendered!r}"
        else:
            message = f"{rendered!r} exited with status {returncode}"
        detail = stderr.strip() or stdout.strip()
        if detail:
            message = f"{message}: {detail}"
        super().__init__(message)
        self.command = tuple(command)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
