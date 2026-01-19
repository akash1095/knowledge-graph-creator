import time
from typing import Dict, List, Optional, Tuple

from loguru import logger
from tqdm import tqdm

from knowledge_graph_creator.db_neo4j.academic_graph import AcademicKnowledgeGraph
from knowledge_graph_creator.extractors.reference_details import ReferenceDetails
from knowledge_graph_creator.semantic_scholar_client import SemanticScholarClient


class AcademicGraphBuilder:
    """Builds an academic knowledge graph from paper references."""

    def __init__(self, uri: str, user: str, password: str, api_key: str = None):
        self.kg = AcademicKnowledgeGraph(uri=uri, user=user, password=password)
        self.ss_client: SemanticScholarClient = SemanticScholarClient(api_key=api_key)

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

    def add_paper_with_citation_network(
        self,
        parent_paper: ReferenceDetails,
        references: List[ReferenceDetails],
        max_papers: int = None,
        include_citations: bool = True,
        max_citations_per_paper: int = 100,
        rate_limit_delay: float = 1.0,
    ) -> Tuple[Dict[str, int], List[ReferenceDetails]]:
        """
        Add a parent paper and its references with extended citation network.

        For each paper added, optionally fetch and add papers that cite it,
        creating a comprehensive citation network.

        Args:
            parent_paper: The parent paper details
            references: List of reference paper details from PDF
            max_papers: Maximum number of papers from PDF references to add (None for all)
            include_citations: Whether to fetch and add citing papers for each paper
            max_citations_per_paper: Maximum number of citing papers to add per paper
            rate_limit_delay: Delay between API calls in seconds

        Returns:
            Tuple of (statistics_dict, unsuccessful_additions)
            statistics_dict contains:
                - parent_papers: Number of parent papers added (1)
                - pdf_references: Number of references from PDF added
                - citations_added: Number of citing papers added
                - total_papers: Total papers added
                - total_relationships: Total citation relationships created
        """
        stats = {
            "parent_papers": 0,
            "pdf_references": 0,
            "citations_added": 0,
            "total_papers": 0,
            "total_relationships": 0,
        }
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
            stats["parent_papers"] = 1
            stats["total_papers"] = 1

            # Track all paper IDs to fetch citations for
            papers_to_process = [(parent_paper_id, "parent")]

            # Add referenced papers from PDF
            tqdm.write(f"\nAdding references from PDF...")
            for reference in tqdm(
                references, desc="PDF References", mininterval=0.1, dynamic_ncols=True
            ):
                paper_json = self.ss_client.get_paper_by_title(reference.title)

                if paper_json:
                    paper_id = self.kg.add_paper_from_json(
                        paper_json, return_paper_id=True
                    )
                    self.kg.add_citation_relationship(
                        citing_paper_id=parent_paper_id, cited_paper_id=paper_id
                    )
                    stats["pdf_references"] += 1
                    stats["total_papers"] += 1
                    stats["total_relationships"] += 1

                    # Add to processing queue for citation fetching
                    papers_to_process.append((paper_id, reference.title))

                    if max_papers and stats["pdf_references"] >= max_papers:
                        break
                else:
                    tqdm.write(f"Paper not found: {reference.title}")
                    unsuccessful_additions.append(reference)

                time.sleep(rate_limit_delay)

            # Fetch and add citing papers for each paper
            if include_citations and max_citations_per_paper > 0:
                tqdm.write(f"\nFetching citation networks...")
                for paper_id, paper_title in tqdm(
                    papers_to_process,
                    desc="Citation Networks",
                    mininterval=0.1,
                    dynamic_ncols=True,
                ):
                    citations_response = self.ss_client.get_paper_citations(
                        paper_id=paper_id, limit=max_citations_per_paper
                    )

                    if citations_response and citations_response.get("data"):
                        for citation_item in citations_response["data"]:
                            citing_paper = citation_item.get("citingPaper")
                            if citing_paper:
                                citing_paper_id = self.kg.add_paper_from_json(
                                    citing_paper, return_paper_id=True
                                )
                                self.kg.add_citation_relationship(
                                    citing_paper_id=citing_paper_id,
                                    cited_paper_id=paper_id,
                                )
                                stats["citations_added"] += 1
                                stats["total_papers"] += 1
                                stats["total_relationships"] += 1

                            time.sleep(rate_limit_delay)

                    time.sleep(rate_limit_delay)

        finally:
            self.kg.close()

        return stats, unsuccessful_additions

    def add_paper_with_citation_network_from_api(
        self,
        parent_paper_details: dict,
        paper_to_process: List[dict],
        include_citations: bool = True,
        max_citations_per_paper: int = 50,
        rate_limit_delay: float = 1.0,
        publication_year: Optional[str] = None,
    ) -> Tuple[dict, List[dict]]:
        """
        Build knowledge graph using Semantic Scholar API response data.

        publication_year: Filter references by publication year, e.g., 2022:2023
        """
        stats = {
            "parent_papers": 0,
            "pdf_references": 0,
            "citations_added": 0,
            "total_papers": 0,
            "total_relationships": 0,
        }
        unsuccessful = []

        parent_paper_id = parent_paper_details.get("paperId")
        if parent_paper_id:
            tqdm.write(
                f"Adding parent paper: {parent_paper_details.get('title', 'Unknown')}"
            )
            self.kg.add_paper_from_json(parent_paper_details)
            stats["parent_papers"] = 1
            stats["total_papers"] += 1

        references_to_process = paper_to_process

        tqdm.write(f"\nProcessing {len(references_to_process)} references...")
        for ref in tqdm(
            references_to_process,
            desc="Adding references",
            colour="green",
            mininterval=0.1,
            dynamic_ncols=True,
        ):
            #Note is written only for citation, not for reference, i need to alter code to support both
            cited_paper = ref.get("citingPaper", {}) or ref.get("citedPaper", {})
            cited_paper_id = cited_paper.get("paperId")

            if not cited_paper_id:
                unsuccessful.append(ref)
                continue

            try:
                self.kg.add_paper_from_json(cited_paper)
                self.kg.add_citation_relationship(
                    citing_paper_id=cited_paper_id,
                    cited_paper_id=parent_paper_id,
                )
                stats["pdf_references"] += 1
                stats["total_papers"] += 1
                stats["total_relationships"] += 1

                if include_citations:
                    time.sleep(rate_limit_delay)
                    citations = self.ss_client.get_paper_citations(
                        paper_id=cited_paper_id,
                        limit=max_citations_per_paper,
                        publication_year=publication_year,
                    )

                    # if reference needed add here reference function.

                    citation_data = citations.get("data") or []
                    for citation in tqdm(
                        citation_data,
                        desc=f"Citations for {cited_paper_id[:8]}",
                        colour="green",
                        leave=False,
                        mininterval=0.1,
                    ):
                        citing_paper = citation.get("citingPaper", {})
                        citing_paper_id = citing_paper.get("paperId")
                        if citing_paper_id:
                            self.kg.add_paper_from_json(citing_paper)
                            self.kg.add_citation_relationship(
                                citing_paper_id=citing_paper_id,
                                cited_paper_id=cited_paper_id,
                            )
                            stats["citations_added"] += 1
                            stats["total_papers"] += 1
                            stats["total_relationships"] += 1

            except Exception as e:
                logger.error(f"Failed to add paper {cited_paper_id}: {e}")
                unsuccessful.append(ref)

        tqdm.write(
            f"\nCompleted: {stats['total_papers']} papers, {stats['total_relationships']} relationships"
        )
        return stats, unsuccessful
