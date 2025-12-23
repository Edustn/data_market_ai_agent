"""Representa uma empresa no domínio do grafo."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Company:
    name: str
    revenue: Optional[float] = None
    sector: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    cnpjs: list[str] = field(default_factory=list)
    addresses: list[str] = field(default_factory=list)
    description: Optional[str] = None
    brands: list["Brand"] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    group: Optional[str] = None  # nome do grupo econômico ou holding
    meta: dict = field(default_factory=dict)  # atributos livres


# Evita import circular em tempo de tipo
from .brand import Brand  # noqa: E402  pylint: disable=wrong-import-position
