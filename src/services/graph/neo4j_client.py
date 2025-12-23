"""Wrapper simples para conexão com Neo4j."""

import os
from neo4j import GraphDatabase


class Neo4jClient:
    def __init__(self) -> None:
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self.driver.close()

    def run(self, query: str, parameters: dict | None = None):
        with self.driver.session() as session:
            return session.run(query, parameters or {})
