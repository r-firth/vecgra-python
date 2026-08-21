"""Pydantic models for Vecgra node and edge records."""

from __future__ import annotations

from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StrictBool,
    StrictInt,
    StrictStr,
    field_validator,
)

ExternalId = StrictStr | StrictInt
JsonScalar = None | StrictBool | StrictInt | FiniteFloat | StrictStr

_F32_MAX = 3.4028234663852886e38


class _Element(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str = Field(min_length=1)
    vectors: list[list[FiniteFloat]] = Field(default_factory=list)

    @field_validator("vectors", mode="before")
    @classmethod
    def reject_boolean_vector_components(cls, value: Any) -> Any:
        if isinstance(value, (list, tuple)):
            for vector in value:
                if isinstance(vector, (list, tuple)) and any(
                    isinstance(component, bool) for component in vector
                ):
                    raise ValueError("vector components may not be booleans")
        return value

    @field_validator("vectors")
    @classmethod
    def require_f32_components(cls, vectors: list[list[float]]) -> list[list[float]]:
        for vector in vectors:
            if any(abs(component) > _F32_MAX for component in vector):
                raise ValueError("vector component is outside the finite F32 range")
        return vectors


class Node(_Element):
    """A dynamic Vecgra node record."""

    id: ExternalId
    properties: dict[StrictStr, JsonScalar] = Field(default_factory=dict)


class Edge(_Element):
    """A dynamic Vecgra directed edge record."""

    source: ExternalId
    target: ExternalId
    properties: dict[StrictStr, JsonScalar] = Field(default_factory=dict)


class NodeModel(_Element):
    """Base class whose subclass fields are serialized as node properties."""

    id: ExternalId

    def to_record(self) -> Node:
        values = self.model_dump(mode="python")
        external_id = values.pop("id")
        label = values.pop("label")
        vectors = values.pop("vectors")
        return Node(id=external_id, label=label, vectors=vectors, properties=values)


class EdgeModel(_Element):
    """Base class whose subclass fields are serialized as edge properties."""

    source: ExternalId
    target: ExternalId

    def to_record(self) -> Edge:
        values = self.model_dump(mode="python")
        source = values.pop("source")
        target = values.pop("target")
        label = values.pop("label")
        vectors = values.pop("vectors")
        return Edge(
            source=source,
            target=target,
            label=label,
            vectors=vectors,
            properties=values,
        )
