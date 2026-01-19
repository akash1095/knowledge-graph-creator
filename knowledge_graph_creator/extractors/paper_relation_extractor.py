import json
import time
from typing import Dict, List, Optional

from loguru import logger
from neo4j import GraphDatabase
from pydantic import ValidationError

from knowledge_graph_creator.llm.llm_inference import LLMInference
from knowledge_graph_creator.llm.prompts import EXTRACT_PROMPT
from knowledge_graph_creator.llm.schema import RelationshipAnalysis


class PaperRelationExtractor:
    """
    Extract semantic relations from citation triplets using LLM.
    """

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        llm_client: LLMInference,
        min_delay: int = 1,
    ):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.llm_client = llm_client
        self.min_delay = min_delay  # seconds between calls

    def close(self):
        """Close database connection."""
        self.driver.close()

    def get_non_processed_triplets(
        self,
        min_citation_count: int = 0,
        head_min_year: int = 2022,
        tail_min_year: int = 2022,
    ) -> List[Dict]:
        """Extract citation triplets that have not been processed yet."""
        query = """
        MATCH (tail:Paper)-[:CITES]->(head:Paper)
        WHERE head.abstract IS NOT NULL 
          AND tail.abstract IS NOT NULL 
          AND head.citation_count >= $min_citation_count
          AND head.year >= $head_min_year 
          AND tail.year >= $tail_min_year
        
          AND NOT EXISTS {
              MATCH (tail)-[r]-(head)
              WHERE type(r) IN [
                'ACHIEVES','ADAPTS_FROM','AUTHORED_BY','CHALLENGES',
                'ENABLES','EXTENDS','OUTPERFORMS','REQUIRES','VALIDATES',
                'CONTRADICTS','SOLVES'
                ]
            }     
        
        RETURN tail.paper_id AS tail_id,
               tail.title AS tail_title,
               tail.abstract AS tail_abstract,
               head.paper_id AS head_id,
               head.title AS head_title,
               head.abstract AS head_abstract
        ORDER BY head.citation_count DESC

        """
        with self.driver.session() as session:
            result = session.run(
                query,
                min_citation_count=min_citation_count,
                head_min_year=head_min_year,
                tail_min_year=tail_min_year,
            )
            return [dict(record) for record in result]

    def get_all_triplets(
        self,
        min_citation_count: int = 0,
        head_min_year: int = 2022,
        tail_min_year: int = 2022,
    ) -> List[Dict]:
        """Extract all citation triplets with valid abstracts."""
        query = """
        MATCH (tail:Paper)-[:CITES]->(head:Paper)
        WHERE head.abstract IS NOT NULL 
          AND tail.abstract IS NOT NULL 
          AND head.citation_count >= $min_citation_count
          AND head.year >= $head_min_year 
          AND tail.year >= $tail_min_year
        RETURN tail.paper_id AS tail_id,
               tail.title AS tail_title,
               tail.abstract AS tail_abstract,
               head.paper_id AS head_id,
               head.title AS head_title,
               head.abstract AS head_abstract
        ORDER BY head.citation_count DESC
        """
        with self.driver.session() as session:
            result = session.run(
                query,
                min_citation_count=min_citation_count,
                head_min_year=head_min_year,
                tail_min_year=tail_min_year,
            )
            return [dict(record) for record in result]

    def extract_relation_with_structured_llm(
        self,
        citing_paper: Dict,
        cited_paper: Dict,
        schema: type = RelationshipAnalysis,
        max_retries: int = 2,
    ) -> Optional[RelationshipAnalysis]:
        """
        Extract relation between citing and cited paper using LLM.
        Includes retry logic for validation errors.
        """
        prompt = EXTRACT_PROMPT.format(
            source_title=citing_paper.get("title", "N/A"),
            source_abstract=citing_paper.get("abstract", "N/A"),
            target_title=cited_paper.get("title", "N/A"),
            target_abstract=cited_paper.get("abstract", "N/A"),
        )

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = self.llm_client.structured_invoke(
                    prompt=prompt,
                    schema=schema,
                )
                if not isinstance(response, RelationshipAnalysis):
                    logger.error(f"{response}")
                return response
            except (ValidationError, json.JSONDecodeError) as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}")
                if attempt < max_retries:
                    prompt = f"{prompt}\n\nIMPORTANT: Return valid JSON matching the exact schema."
            except Exception as e:
                logger.error(f"LLM extraction failed: {e}")
                return None

        logger.error(f"All retries exhausted: {last_error}")
        return None

    def save_relationships(
        self,
        citing_id: str,
        cited_id: str,
        analysis: RelationshipAnalysis,
    ):
        """Save extracted relationships to database without duplication."""
        if not analysis.relationships:
            return

        for rel in analysis.relationships:
            relation_label = rel.type.upper().replace("-", "_").replace(" ", "_")
            query = f"""
            MATCH (citing:Paper {{paper_id: $citing_id}})
            MATCH (cited:Paper {{paper_id: $cited_id}})
            MERGE (citing)-[r:{relation_label}]->(cited)
            ON CREATE SET 
                r.confidence = $confidence,
                r.evidence = $evidence,
                r.explanation = $explanation,
                r.extracted_by = 'llm',
                r.created_at = datetime()
            ON MATCH SET
                r.confidence = CASE WHEN $confidence = 'high' THEN $confidence ELSE r.confidence END,
                r.updated_at = datetime()
            """
            with self.driver.session() as session:
                session.run(
                    query,
                    citing_id=citing_id,
                    cited_id=cited_id,
                    confidence=rel.confidence,
                    evidence=rel.evidence,
                    explanation=rel.explanation,
                )

    def process_all_triplets(
        self,
        min_citation_count: int = 0,
        head_min_year: int = 2022,
        tail_min_year: int = 2022,
    ) -> List[Dict]:
        """Process all triplets and extract semantic relations."""
        triplets = self.get_all_triplets(
            min_citation_count, head_min_year, tail_min_year
        )
        logger.info(f"Found {len(triplets)} triplets to process")

        results = []
        for idx, triplet in enumerate(triplets):
            citing_paper = {
                "title": triplet["tail_title"],
                "abstract": triplet["tail_abstract"],
            }
            cited_paper = {
                "title": triplet["head_title"],
                "abstract": triplet["head_abstract"],
            }

            logger.info(
                f"Processing {idx + 1}/{len(triplets)}: {triplet['tail_id']} -> {triplet['head_id']}"
            )

            analysis = self.extract_relation_with_structured_llm(
                citing_paper, cited_paper
            )

            if analysis and analysis.relationships:
                self.save_relationships(
                    triplet["tail_id"], triplet["head_id"], analysis
                )
                results.append(
                    {
                        "citing_id": triplet["tail_id"],
                        "cited_id": triplet["head_id"],
                        "relationships": [
                            r.model_dump() for r in analysis.relationships
                        ],
                    }
                )

            # Rate limiting for Groq API
            time.sleep(self.min_delay)

        logger.info(f"Extracted relationships for {len(results)} triplets")
        return results
