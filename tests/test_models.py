from __future__ import annotations

from typing import Literal

import pytest
from pydantic import ValidationError

from vecgra import EdgeModel, Node, NodeModel


class Product(NodeModel):
    label: Literal["Product"] = "Product"
    sku: str
    price: float


class Purchased(EdgeModel):
    label: Literal["PURCHASED"] = "PURCHASED"
    order_id: str
    quantity: int


def test_typed_node_fields_become_scalar_properties() -> None:
    product = Product(
        id="product:keyboard",
        sku="KB-01",
        price=129.0,
        vectors=[[1.0, 0.0]],
    )

    record = product.to_record()

    assert record.id == "product:keyboard"
    assert record.label == "Product"
    assert record.properties == {"sku": "KB-01", "price": 129.0}
    assert record.vectors == [[1.0, 0.0]]


def test_typed_edge_fields_become_scalar_properties() -> None:
    edge = Purchased(
        source="customer:ada",
        target="product:keyboard",
        order_id="order-1001",
        quantity=1,
    ).to_record()

    assert edge.label == "PURCHASED"
    assert edge.properties == {"order_id": "order-1001", "quantity": 1}


def test_typed_models_reject_nested_properties_during_conversion() -> None:
    class Nested(NodeModel):
        label: Literal["Nested"] = "Nested"
        metadata: dict[str, str]

    value = Nested(id="nested:1", metadata={"source": "test"})

    with pytest.raises(ValidationError, match=r"properties\.metadata"):
        value.to_record()


@pytest.mark.parametrize("external_id", [True, 1.5, None])
def test_external_ids_are_strict_strings_or_integers(external_id: object) -> None:
    with pytest.raises(ValidationError):
        Node(id=external_id, label="Example")


@pytest.mark.parametrize("component", [float("nan"), float("inf"), 3.5e38, True])
def test_vectors_reject_values_the_rust_importer_cannot_store(component: object) -> None:
    with pytest.raises(ValidationError):
        Node(id="example", label="Example", vectors=[[component]])
