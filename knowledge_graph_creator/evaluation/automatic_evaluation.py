from neo4j import GraphDatabase
import networkx as nx


# 1. Graph Topology Metrics
def compute_graph_metrics(driver):
    with driver.session() as session:
        # Total nodes and edges
        result = session.run(
            """
            MATCH (n:Paper)
            RETURN count(n) as nodes
        """
        )
        nodes = result.single()["nodes"]

        result = session.run(
            """
            MATCH ()-[r]->()
            RETURN count(r) as edges
        """
        )
        edges = result.single()["edges"]

        # Average degree
        avg_degree = (2 * edges) / nodes

        # Density
        density = (2 * edges) / (nodes * (nodes - 1))

        return {
            "nodes": nodes,
            "edges": edges,
            "avg_degree": avg_degree,
            "density": density,
        }


# 2. Citation Coverage Check
def check_citation_coverage(driver):
    with driver.session() as session:
        result = session.run(
            """
            MATCH (a:Paper)-[r]->(b:Paper)
            WHERE NOT EXISTS((a)-[:CITES]->(b))
            RETURN count(r) as orphan_rels,
                   count(r) * 1.0 / size([(a)-[r2]->(b2) | r2]) as orphan_ratio
        """
        )
        return result.single()


# 3. Temporal Consistency
def check_temporal_consistency(driver):
    with driver.session() as session:
        # Papers should not cite future papers
        result = session.run(
            """
            MATCH (a:Paper)-[r:CITES]->(b:Paper)
            WHERE a.year > b.year
            RETURN count(r) as violations
        """
        )
        violations = result.single()["violations"]

        total = session.run(
            """
            MATCH ()-[r]->()
            RETURN count(r) as total
        """
        ).single()["total"]

        return 1 - (violations / total)


if __name__ == "__main__":
    driver = GraphDatabase.driver(
        "bolt://localhost:9687", auth=("neo4j", "your_password")
    )
    print(check_temporal_consistency(driver))
    # print(check_citation_coverage(driver))
    print(check_temporal_consistency(driver))
