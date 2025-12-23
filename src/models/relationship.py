"""Relacionamentos usados no grafo."""

from dataclasses import dataclass


@dataclass
class Relationship:
    source: str
    target: str
    type: str
    confidence: float = 1.0
    metadata: dict | None = None
