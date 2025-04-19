"""
Knowledge Graph Layer for Turing-level Validator
- Uses Neo4j for production, NetworkX fallback for dev/test
- Models rules, dependencies, data schemas, and validation results
"""
from typing import Any, Dict, List, Optional
import os

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
import networkx as nx

class KnowledgeGraph:
    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        self.use_neo4j = NEO4J_AVAILABLE and uri is not None
        if self.use_neo4j:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
        else:
            self.graph = nx.MultiDiGraph()

    def add_rule(self, rule_id: str, rule_content: str, metadata: Optional[Dict[str, Any]] = None):
        if self.use_neo4j:
            with self.driver.session() as session:
                session.run("""
                    MERGE (r:Rule {id: $rule_id})
                    SET r.content = $rule_content, r.metadata = $metadata
                """, rule_id=rule_id, rule_content=rule_content, metadata=metadata or {})
        else:
            self.graph.add_node(rule_id, type="Rule", content=rule_content, **(metadata or {}))

    def add_dependency(self, from_id: str, to_id: str, dep_type: str = "depends_on"):
        if self.use_neo4j:
            with self.driver.session() as session:
                session.run("""
                    MATCH (a {id: $from_id}), (b {id: $to_id})
                    MERGE (a)-[r:%s]->(b)
                """ % dep_type.upper(), from_id=from_id, to_id=to_id)
        else:
            self.graph.add_edge(from_id, to_id, type=dep_type)

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        if self.use_neo4j:
            with self.driver.session() as session:
                result = session.run("MATCH (r:Rule {id: $rule_id}) RETURN r", rule_id=rule_id)
                record = result.single()
                return dict(record["r"]) if record else None
        else:
            return self.graph.nodes.get(rule_id, None)

    def get_dependencies(self, rule_id: str) -> List[str]:
        if self.use_neo4j:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (a:Rule {id: $rule_id})-[]->(b:Rule) RETURN b.id as dep_id
                """, rule_id=rule_id)
                return [record["dep_id"] for record in result]
        else:
            return list(self.graph.successors(rule_id))
