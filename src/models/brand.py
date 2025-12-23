"""Representa uma marca/subsidiária."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Brand:
    name: str
    cnpjs: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    description: Optional[str] = None
    parent_company: Optional[str] = None
