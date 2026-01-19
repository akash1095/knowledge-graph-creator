"""
Knowledge Graph Evaluator Module (No Ground Truth)
Evaluates graph quality using intrinsic metrics
Integrated with Neo4j graph fetching
"""

from collections import defaultdict, Counter
from typing import Dict, List, Set, Any, Optional
import math
from neo4j import GraphDatabase


class Neo4jGraphFetcher:
    """Fetch knowledge graph from Neo4j database."""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def fetch_graph(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Fetch nodes and edges from Neo4j."""
        with self.driver.session() as session:
            edge_query = """
            MATCH (source)-[r]->(target)
            RETURN source.id AS source, target.id AS target,
                   type(r) AS rel_type, r.category AS category
            """
            if limit:
                edge_query += f" LIMIT {limit}"

            edges = []
            result = session.run(edge_query)
            for record in result:
                edges.append(
                    {
                        "source": record["source"],
                        "target": record["target"],
                        "category": record.get("category", "unknown"),
                        "type": record.get("rel_type", "unknown"),
                    }
                )

            node_query = "MATCH (n) RETURN n.id AS id"
            if limit:
                node_query += f" LIMIT {limit}"

            nodes = set()
            result = session.run(node_query)
            for record in result:
                nodes.add(record["id"])

            return {"nodes": nodes, "edges": edges}


class KnowledgeGraphEvaluator:
    """Evaluator for scientific knowledge graph quality without ground truth."""

    # 10-type taxonomy from relation_types.json
    TAXONOMY = {
        "semantic": [
            "Extends",  # Builds upon, generalizes prior work
            "Solves",  # Problem-solution relationship
            "Outperforms",  # Empirical superiority
            "Validates",  # Confirms findings from another work
            "Contradicts",  # Opposing findings/conclusions
            "Requires",  # Dependency/prerequisite
            "Enables",  # Makes new capability possible
            "Adapts-from",  # Cross-domain knowledge transfer
            "Achieves",  # Links method to quantitative outcomes
            "Challenges",  # Questions assumptions without contradicting
        ],
        "referential": [],  # All 10 types are semantic in your taxonomy
    }

    # Relation metadata for validation
    RELATION_PROPERTIES = {
        "Extends": {"temporal": True, "citation_expected": True},
        "Solves": {"temporal": False, "citation_expected": False},
        "Outperforms": {
            "temporal": True,
            "citation_expected": True,
            "requires_metric": True,
        },
        "Validates": {"temporal": True, "citation_expected": True},
        "Contradicts": {"temporal": False, "citation_expected": True},
        "Requires": {"temporal": False, "citation_expected": False},
        "Enables": {"temporal": True, "citation_expected": False},
        "Adapts-from": {
            "temporal": True,
            "citation_expected": True,
            "cross_domain": True,
        },
        "Achieves": {
            "temporal": False,
            "citation_expected": False,
            "requires_metric": True,
        },
        "Challenges": {"temporal": False, "citation_expected": True},
    }

    def __init__(
        self, graph: Dict[str, Any] = None, neo4j_config: Dict[str, str] = None
    ):
        """
        Initialize evaluator with graph data or Neo4j connection.

        Args:
            graph: Pre-loaded graph dict with 'nodes' and 'edges'
            neo4j_config: Dict with 'uri', 'user', 'password' for Neo4j connection
        """
        if neo4j_config:
            fetcher = Neo4jGraphFetcher(
                uri=neo4j_config["uri"],
                user=neo4j_config["user"],
                password=neo4j_config["password"],
            )
            try:
                self.graph = fetcher.fetch_graph(neo4j_config.get("limit"))
            finally:
                fetcher.close()
        elif graph:
            self.graph = graph
        else:
            raise ValueError("Provide either graph dict or neo4j_config")

        self.edges = self.graph.get("edges", [])
        self.nodes = self.graph.get("nodes", set())
        self._extract_nodes_from_edges()
        self.all_types = self.TAXONOMY["semantic"] + self.TAXONOMY["referential"]

    def _extract_nodes_from_edges(self):
        """Extract nodes from edges if not provided."""
        if not self.nodes:
            self.nodes = set()
            for e in self.edges:
                self.nodes.add(e["source"])
                self.nodes.add(e["target"])

    def calculate_identification_distribution(self) -> Dict[str, Any]:
        """Analyze relationship type distribution across semantic categories."""
        type_counts = Counter(e.get("type", "unknown") for e in self.edges)
        total = len(self.edges) if self.edges else 1

        # Group by newcomer benefit categories
        benefit_groups = {
            "learning_path": ["Extends", "Adapts-from"],
            "problem_solution": ["Solves", "Enables"],
            "reliability": ["Validates", "Contradicts", "Challenges"],
            "performance": ["Outperforms", "Achieves"],
            "prerequisites": ["Requires"],
        }

        group_distribution = {}
        for group, types in benefit_groups.items():
            count = sum(type_counts.get(t, 0) for t in types)
            group_distribution[group] = count / total

        # Calculate balance across benefit groups
        values = list(group_distribution.values())
        balance_score = 1 - (max(values) - min(values)) if values else 0

        return {
            "type_counts": dict(type_counts),
            "benefit_group_distribution": group_distribution,
            "balance_score": balance_score,
            "total_edges": len(self.edges),
        }

    def calculate_type_classification_quality(self) -> Dict[str, Any]:
        """Evaluate 10-type taxonomy coverage and distribution."""
        type_counts = Counter(e.get("type", "unknown") for e in self.edges)
        total = len(self.edges) if self.edges else 1

        # Coverage: proportion of taxonomy types used
        types_used = set(type_counts.keys()) & set(self.all_types)
        coverage = len(types_used) / len(self.all_types) if self.all_types else 0

        # Entropy: higher = more diverse type distribution
        valid_counts = [type_counts.get(t, 0) for t in self.all_types]
        total_valid = sum(valid_counts)
        if total_valid > 0:
            probs = [c / total_valid for c in valid_counts if c > 0]
            entropy = -sum(p * math.log2(p) for p in probs)
            max_entropy = math.log2(len(self.all_types))
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        else:
            normalized_entropy = 0

        # Validate types against taxonomy
        valid_edges = sum(1 for e in self.edges if e.get("type") in self.all_types)
        validity_rate = valid_edges / total if total > 0 else 0

        # Unknown/invalid types detected
        invalid_types = set(type_counts.keys()) - set(self.all_types)

        return {
            "type_distribution": {
                t: type_counts.get(t, 0) / total for t in self.all_types
            },
            "type_counts": {t: type_counts.get(t, 0) for t in self.all_types},
            "taxonomy_coverage": coverage,
            "diversity_score": normalized_entropy,
            "validity_rate": validity_rate,
            "types_used": list(types_used),
            "invalid_types": list(invalid_types),
            "taxonomy_size": len(self.all_types),
        }

    def calculate_graph_coverage(self) -> Dict[str, Any]:
        """Analyze graph structure and connectivity."""
        num_nodes = len(self.nodes)
        num_edges = len(self.edges)

        max_edges = num_nodes * (num_nodes - 1) if num_nodes > 1 else 1
        density = num_edges / max_edges if max_edges > 0 else 0

        out_degree = Counter(e["source"] for e in self.edges)
        in_degree = Counter(e["target"] for e in self.edges)

        avg_out = sum(out_degree.values()) / num_nodes if num_nodes > 0 else 0
        avg_in = sum(in_degree.values()) / num_nodes if num_nodes > 0 else 0

        connected_nodes = set(out_degree.keys()) | set(in_degree.keys())
        isolated = num_nodes - len(connected_nodes)

        annotated = sum(1 for e in self.edges if e.get("type") in self.all_types)
        annotation_rate = annotated / num_edges if num_edges > 0 else 0

        return {
            "num_nodes": num_nodes,
            "num_edges": num_edges,
            "density": density,
            "avg_out_degree": avg_out,
            "avg_in_degree": avg_in,
            "max_out_degree": max(out_degree.values()) if out_degree else 0,
            "max_in_degree": max(in_degree.values()) if in_degree else 0,
            "isolated_nodes": isolated,
            "connectivity_rate": (
                len(connected_nodes) / num_nodes if num_nodes > 0 else 0
            ),
            "annotation_completeness": annotation_rate,
        }

    def calculate_relationship_precision_heuristics(self) -> Dict[str, Any]:
        """Heuristic checks for relationship identification quality."""
        self_loops = sum(1 for e in self.edges if e["source"] == e["target"])

        edge_tuples = [(e["source"], e["target"], e.get("type")) for e in self.edges]
        duplicates = len(edge_tuples) - len(set(edge_tuples))

        edge_pairs = defaultdict(list)
        for e in self.edges:
            edge_pairs[(e["source"], e["target"])].append(e.get("type"))

        # Check for semantically contradictory relations on same edge
        contradictory_pairs = [
            ("Validates", "Contradicts"),
            ("Outperforms", "Requires"),
            ("Extends", "Contradicts"),
        ]
        semantic_conflicts = 0
        for (src, tgt), types in edge_pairs.items():
            type_set = set(types)
            for t1, t2 in contradictory_pairs:
                if t1 in type_set and t2 in type_set:
                    semantic_conflicts += 1

        # Bidirectional asymmetric check (Extends, Outperforms should be one-way)
        asymmetric_types = ["Extends", "Outperforms", "Validates", "Enables"]
        asymmetric_violations = 0
        for (src, tgt), types in edge_pairs.items():
            reverse_types = edge_pairs.get((tgt, src), [])
            for t in asymmetric_types:
                if t in types and t in reverse_types:
                    asymmetric_violations += 1

        total = max(1, len(self.edges))
        quality_score = 1.0
        quality_score -= (self_loops / total) * 0.2
        quality_score -= (duplicates / total) * 0.2
        quality_score -= (semantic_conflicts / total) * 0.3
        quality_score -= (asymmetric_violations / total) * 0.3
        quality_score = max(0, quality_score)

        return {
            "self_loops": self_loops,
            "duplicate_edges": duplicates,
            "semantic_conflicts": semantic_conflicts,
            "asymmetric_violations": asymmetric_violations,
            "heuristic_quality_score": quality_score,
        }

    def evaluate_all(self) -> Dict[str, Any]:
        """Run all evaluations."""
        return {
            "identification_distribution": self.calculate_identification_distribution(),
            "type_classification_quality": self.calculate_type_classification_quality(),
            "graph_coverage": self.calculate_graph_coverage(),
            "relationship_precision": self.calculate_relationship_precision_heuristics(),
        }


def quick_evaluate(graph: Dict = None, neo4j_config: Dict = None) -> Dict[str, Any]:
    """Quick evaluation from graph dict or Neo4j."""
    evaluator = KnowledgeGraphEvaluator(graph=graph, neo4j_config=neo4j_config)
    return evaluator.evaluate_all()


if __name__ == "__main__":
    # From Neo4j
    results = quick_evaluate(
        neo4j_config={
            "uri": "bolt://localhost:9687",
            "user": "neo4j",
            "password": "your_password",
            # "limit": 1000  # Fetch only 1000 edges
        }
    )
    print(results)

    # # Or from dict
    # results = quick_evaluate(graph={"edges": []
    # print(results)
