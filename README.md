# Vecgra for Python

Typed Python records and a small client for
[Vecgra](https://github.com/r-firth/vecgra), the embedded graph and vector
database.

This package does two concrete jobs:

- validates nodes, edges, properties, external IDs, and vectors with Pydantic;
- invokes the `vecgra` CLI without a shell to import JSONL and run read queries.

It is not a native binding and it does not start a database server. The `.vg`
file remains owned by the Rust engine.

## Install

Install the Python package and make sure the `vecgra` binary is on `PATH`:

```sh
pip install https://github.com/r-firth/vecgra-python/releases/download/v0.1.0/vecgra-0.1.0-py3-none-any.whl
vecgra --version
```

Vecgra currently ships as a Rust source release. Build the binary with
`cargo build --release -p vecgra-cli`, then pass its path to `VecgraClient` if
it is not installed globally.

## Typed models

Subclass `NodeModel` or `EdgeModel` when your application has a known schema.
Every field declared by the subclass becomes a scalar graph property.

```python
from typing import Literal

from vecgra import EdgeModel, Graph, NodeModel, VecgraClient


class Customer(NodeModel):
    label: Literal["Customer"] = "Customer"
    name: str
    active: bool


class Product(NodeModel):
    label: Literal["Product"] = "Product"
    name: str
    sku: str
    price: float


class Purchased(EdgeModel):
    label: Literal["PURCHASED"] = "PURCHASED"
    order_id: str
    quantity: int


graph = Graph(dimension=4)
graph.add_node(
    Customer(
        id="customer:ada",
        name="Ada Lovelace",
        active=True,
        vectors=[[1.0, 0.2, 0.0, 0.0]],
    )
)
graph.add_node(
    Product(
        id="product:keyboard",
        name="Mechanical keyboard",
        sku="KB-01",
        price=129.0,
        vectors=[[0.8, 0.4, 0.0, 0.0]],
    )
)
graph.add_edge(
    Purchased(
        source="customer:ada",
        target="product:keyboard",
        order_id="order-1001",
        quantity=1,
        vectors=[[0.9, 0.3, 0.0, 0.0]],
    )
)

client = VecgraClient(binary="vecgra")
result = client.import_graph(graph, "customer-orders.vg")
print(result.nodes, result.edges, result.vectors)

for row in client.query(
    "customer-orders.vg",
    "MATCH (c:Customer)-[r:PURCHASED]->(p:Product) RETURN c,r,p LIMIT 10",
):
    print(row)
```

`Graph` catches duplicate node IDs, missing edge endpoints, nested property
values, non-finite numbers, cosine vector norms the Rust engine rejects, values
outside the F32 range, and vectors with the wrong dimension before it invokes
Vecgra.

## Dynamic records

Use `Node` and `Edge` when labels and properties come from data rather than
Python classes:

```python
from vecgra import Edge, Graph, Node

graph = Graph(dimension=768)
graph.add_node(
    Node(
        id="document:1",
        label="Document",
        properties={"title": "Example", "published": True},
        vectors=[embedding],
    )
)
graph.add_edge(
    Edge(
        source="document:1",
        target="document:1",
        label="REFERENCES",
        properties={"confidence": 0.9},
    )
)
graph.write_jsonl("nodes.jsonl", "edges.jsonl")
```

Properties may be `None`, booleans, integers, floats, or strings. Nodes and
edges may each have zero, one, or many vectors.

## Existing JSONL

Validate existing files in Python:

```python
from vecgra import load_jsonl

graph = load_jsonl("nodes.jsonl", "edges.jsonl", dimension=768)
```

Or use the included command:

```sh
vecgra-python validate nodes.jsonl edges.jsonl 768
vecgra-python import nodes.jsonl edges.jsonl graph.vg 768
vecgra-python stats graph.vg
vecgra-python query graph.vg \
  'MATCH (a:Document)-[r:REFERENCES]->(b:Document) RETURN a,r,b LIMIT 10'
```

## Cypher boundary

`VecgraClient.query` supports the same focused, read-only one-hop Cypher subset
as the Rust CLI. Vecgra does not currently implement `CREATE`, `MERGE`, `SET`,
`DELETE`, Bolt, or a network server. Use typed records or JSONL to ingest data.

## Development

```sh
python -m pip install -e '.[dev]'
ruff check .
ruff format --check .
mypy
pytest
python -m build
python -m twine check dist/*
```

The package is licensed under Apache-2.0.
