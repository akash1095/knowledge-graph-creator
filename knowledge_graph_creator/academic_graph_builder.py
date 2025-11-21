import time
from typing import List, Tuple

from tqdm import tqdm

from knowledge_graph_creator.db_neo4j.academic_graph import AcademicKnowledgeGraph
from knowledge_graph_creator.extractors.reference_details import ReferenceDetails
from knowledge_graph_creator.semantic_scholar_client import SemanticScholarClient


class AcademicGraphBuilder:
    """Builds an academic knowledge graph from paper references."""

    def __init__(self, uri: str, user: str, password: str, api_key: str = None):
        self.kg = AcademicKnowledgeGraph(uri=uri, user=user, password=password)
        self.ss_client = SemanticScholarClient(api_key=api_key)

    def add_paper_with_citations(
        self,
        parent_paper: ReferenceDetails,
        references: List[ReferenceDetails],
        max_papers: int = None,
        rate_limit_delay: float = 1.0,
    ) -> Tuple[List[ReferenceDetails], List[ReferenceDetails]]:
        """
        Add a parent paper and its citations to the knowledge graph.

        Args:
            parent_paper: The parent paper details
            references: List of reference paper details
            max_papers: Maximum number of papers to add (None for all)
            rate_limit_delay: Delay between API calls in seconds

        Returns:
            Tuple of (successful_additions, unsuccessful_additions)
        """
        successful_additions = []
        unsuccessful_additions = []

        try:
            # Add parent paper
            tqdm.write(f"Adding parent paper: {parent_paper.title}")
            parent_paper_json = self.ss_client.get_paper_by_title(parent_paper.title)

            if not parent_paper_json:
                raise ValueError(f"Parent paper not found: {parent_paper.title}")

            parent_paper_id = self.kg.add_paper_from_json(
                parent_paper_json, return_paper_id=True
            )

            # Add referenced papers
            for reference in tqdm(references, mininterval=0.1, dynamic_ncols=True):
                paper_json = self.ss_client.get_paper_by_title(reference.title)

                if paper_json:
                    paper_id = self.kg.add_paper_from_json(
                        paper_json, return_paper_id=True
                    )
                    self.kg.add_citation_relationship(
                        citing_paper_id=parent_paper_id, cited_paper_id=paper_id
                    )
                    successful_additions.append(reference)

                    if max_papers and len(successful_additions) >= max_papers:
                        break
                else:
                    tqdm.write(f"Paper not found: {reference.title}")
                    unsuccessful_additions.append(reference)

                time.sleep(rate_limit_delay)

        finally:
            self.kg.close()

        return successful_additions, unsuccessful_additions
