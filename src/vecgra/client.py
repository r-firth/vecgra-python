"""Subprocess client for the Vecgra command-line interface."""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .errors import VecgraCommandError
from .graph import Graph

VectorEncoding = Literal["f16", "f32"]


class _Result(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ImportResult(_Result):
    """Counts printed after a successful JSONL import."""

    nodes: int
    edges: int
    vectors: int


class DatabaseStats(_Result):
    """Logical and storage settings returned by `vecgra stats`."""

    path: Path
    nodes: int
    edges: int
    symbols: int
    vectors: int
    transactions: int
    dimension: int
    similarity: str
    vector_encoding: str


class CheckResult(_Result):
    """Integrity counts returned by `vecgra check`."""

    status: str
    nodes: int
    edges: int
    vectors: int
    transactions: int
    vector_bytes_verified: int
    vector_checksum_blocks_verified: int
    elapsed_ms: float


@dataclass(frozen=True, slots=True)
class VecgraClient:
    """Invoke a Vecgra binary without using a shell."""

    binary: str | os.PathLike[str] = "vecgra"
    timeout: float | None = None

    def version(self) -> str:
        """Return the Vecgra semantic version."""

        output = self.run("--version").strip()
        prefix = "vecgra "
        if not output.startswith(prefix):
            raise VecgraCommandError((os.fspath(self.binary), "--version"), 0, output)
        return output.removeprefix(prefix)

    def import_jsonl(
        self,
        nodes_path: str | Path,
        edges_path: str | Path,
        database_path: str | Path,
        dimension: int,
        encoding: VectorEncoding = "f16",
    ) -> ImportResult:
        """Create a new database from node and edge JSONL files."""

        if not isinstance(dimension, int) or isinstance(dimension, bool) or dimension <= 0:
            raise ValueError("vector dimension must be a positive integer")
        if encoding not in ("f16", "f32"):
            raise ValueError(f"unknown vector encoding {encoding!r}")
        output = self.run(
            "import-jsonl",
            os.fspath(nodes_path),
            os.fspath(edges_path),
            os.fspath(database_path),
            str(dimension),
            encoding,
        )
        return ImportResult.model_validate(self._parse_tab_output(output))

    def import_graph(
        self,
        graph: Graph,
        database_path: str | Path,
        encoding: VectorEncoding = "f16",
    ) -> ImportResult:
        """Validate a graph, write temporary JSONL, and create a database."""

        with tempfile.TemporaryDirectory(prefix="vecgra-python-") as directory:
            nodes, edges = graph.write_directory(directory)
            return self.import_jsonl(nodes, edges, database_path, graph.dimension, encoding)

    def stats(self, database_path: str | Path) -> DatabaseStats:
        """Return database counts and vector settings."""

        output = self.run("stats", os.fspath(database_path))
        return DatabaseStats.model_validate(self._parse_tab_output(output))

    def check(self, database_path: str | Path) -> CheckResult:
        """Run Vecgra's database integrity check."""

        output = self.run("check", os.fspath(database_path))
        return CheckResult.model_validate(self._parse_tab_output(output))

    def query(self, database_path: str | Path, cypher: str) -> tuple[str, ...]:
        """Run Vecgra's focused read-only Cypher query subset."""

        output = self.run("query", os.fspath(database_path), cypher)
        return tuple(line for line in output.splitlines() if line)

    def run(self, *arguments: str) -> str:
        """Run any Vecgra CLI command and return standard output."""

        command = [os.fspath(self.binary), *arguments]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as error:
            raise VecgraCommandError(command, None, stderr=str(error)) from error
        if completed.returncode != 0:
            raise VecgraCommandError(
                command,
                completed.returncode,
                completed.stdout,
                completed.stderr,
            )
        return completed.stdout

    @staticmethod
    def _parse_tab_output(output: str) -> dict[str, str]:
        values: dict[str, str] = {}
        for line in output.splitlines():
            key, separator, value = line.partition("\t")
            if not separator:
                raise ValueError(f"expected tab-delimited Vecgra output, got {line!r}")
            values[key] = value
        return values
