import time
from typing import List, Literal, Optional

from loguru import logger

from knowledge_graph_creator.academic_graph_builder import AcademicGraphBuilder
from knowledge_graph_creator.doc_extractor.pdf_extractor import PyMuPDFReader
from knowledge_graph_creator.extractors.reference_details import (
    ReferenceDetails,
    ReferenceDetailsExtractor,
)
from knowledge_graph_creator.extractors.reference_extractor import ReferenceExtractor
from knowledge_graph_creator.patterns import ReferencePattern


class PDFToKnowledgeGraphOrchestrator:
    """Orchestrates the complete pipeline from PDF to Knowledge Graph."""

    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        ss_api_key: str = None,
        rate_limit_delay: float = 1.0,
    ):
        self.pdf_reader = PyMuPDFReader()
        self.reference_extractor = ReferenceExtractor(ReferencePattern.BRACKETED_NUMBER)
        self.details_extractor = ReferenceDetailsExtractor()
        self.graph_builder = AcademicGraphBuilder(
            uri=neo4j_uri, user=neo4j_user, password=neo4j_password, api_key=ss_api_key
        )
        self.rate_limit_delay = rate_limit_delay

    def process_pdf_to_graph(
        self,
        pdf_path: str,
        parent_paper: ReferenceDetails,
        reference_pages: List[int],
        max_papers: int = None,
    ):
        """
        Extract references from PDF and build knowledge graph.

        Args:
            pdf_path: Path to the PDF file
            parent_paper: Details of the parent paper
            reference_pages: List of page numbers containing references
            max_papers: Maximum number of papers to add to graph

        Returns:
            Tuple of (successful_additions, unsuccessful_additions)
        """
        # Step 1: Extract text from PDF pages
        pages = self.pdf_reader.to_list(path=pdf_path, select_pages=reference_pages)

        # Step 2: Extract references
        references = {}
        for page_text in pages:
            references.update(self.reference_extractor.extract(text=page_text))

        # Step 3: Parse reference details
        references_details = []
        for ref_id, ref_text in references.items():
            details = self.details_extractor.parse_with_regex(
                ref_id=ref_id, ref_text=ref_text
            )
            references_details.append(details)

        # Step 4: Build knowledge graph
        successful, unsuccessful = self.graph_builder.add_paper_with_citations(
            parent_paper=parent_paper,
            references=references_details,
            max_papers=max_papers,
        )

        return successful, unsuccessful

    def process_pdf_to_graph_with_network(
        self,
        pdf_path: str,
        parent_paper: ReferenceDetails,
        reference_pages: List[int],
        max_papers: int = None,
        include_citations: bool = True,
        max_citations_per_paper: int = 50,
    ):
        """
        Extract references from PDF and build extended knowledge graph with citation network.

        This method builds a comprehensive citation network by:
        1. Adding the parent paper
        2. Adding references from the PDF
        3. For each paper added, fetching and adding papers that cite it

        Args:
            pdf_path: Path to the PDF file
            parent_paper: Details of the parent paper
            reference_pages: List of page numbers containing references
            max_papers: Maximum number of papers from PDF references to add (None for all)
            include_citations: Whether to fetch and add citing papers for each paper
            max_citations_per_paper: Maximum number of citing papers to add per paper
            rate_limit_delay: Delay between API calls in seconds (default: 1.0)

        Returns:
            Tuple of (statistics_dict, unsuccessful_additions)
            statistics_dict contains:
                - parent_papers: Number of parent papers added (1)
                - pdf_references: Number of references from PDF added
                - citations_added: Number of citing papers added
                - total_papers: Total papers added
                - total_relationships: Total citation relationships created
        """
        # Step 1: Extract text from PDF pages
        pages = self.pdf_reader.to_list(path=pdf_path, select_pages=reference_pages)

        # Step 2: Extract references
        references = {}
        for page_text in pages:
            references.update(self.reference_extractor.extract(text=page_text))

        # Step 3: Parse reference details
        references_details = []
        for ref_id, ref_text in references.items():
            details = self.details_extractor.parse_with_regex(
                ref_id=ref_id, ref_text=ref_text
            )
            if details:  # Possible to get None
                references_details.append(details)

        # Step 4: Build knowledge graph with citation network
        stats, unsuccessful = self.graph_builder.add_paper_with_citation_network(
            parent_paper=parent_paper,
            references=references_details,
            max_papers=max_papers,
            include_citations=include_citations,
            max_citations_per_paper=max_citations_per_paper,
            rate_limit_delay=self.rate_limit_delay,
        )

        return stats, unsuccessful

    def get_parper_to_process(
        self,
        parent_paper_details,
        citation_network_type,
        max_citations_per_paper,
        publication_year,
    ):
        """
        Based On run type fetch paper to process


        """
        all_paper_to_process = []
        if citation_network_type == "references":
            # Step 2.1: Extract Reference from Parent Paper
            time.sleep(self.rate_limit_delay)
            parent_paper_references = self.graph_builder.ss_client.get_paper_references(
                paper_id=parent_paper_details["paperId"],
                limit=max_citations_per_paper,
                publication_year=publication_year,
            )
            logger.info(
                f"Number of Reference collections: {len(parent_paper_references['data'])}"
            )
            all_paper_to_process.extend(parent_paper_references["data"])

        elif citation_network_type == "citations":
            time.sleep(self.rate_limit_delay)
            # Step 2.2: Extract Citation from Parent Paper
            parent_paper_citations = self.graph_builder.ss_client.get_paper_citations(
                paper_id=parent_paper_details["paperId"],
                limit=max_citations_per_paper,
                publication_year=publication_year,
            )
            logger.info(
                f"Number of Citation collections: {len(parent_paper_citations['data'])}"
            )
            all_paper_to_process.extend(parent_paper_citations["data"])

        elif citation_network_type == "all":
            time.sleep(self.rate_limit_delay)
            parent_paper_references = self.graph_builder.ss_client.get_paper_references(
                paper_id=parent_paper_details["paperId"],
                limit=max_citations_per_paper,
                publication_year=publication_year,
            )
            all_paper_to_process.extend(parent_paper_references["data"])
            time.sleep(self.rate_limit_delay)
            parent_paper_citations = self.graph_builder.ss_client.get_paper_citations(
                paper_id=parent_paper_details["paperId"],
                limit=max_citations_per_paper,
                publication_year=publication_year,
            )
            all_paper_to_process.extend(parent_paper_citations["data"])
            logger.info(
                f"Number of Reference and Citation collections: {len(all_paper_to_process)}"
            )

        return all_paper_to_process


    def process_title_to_graph_with_network(
        self,
        parent_paper_title: str,
        include_citations: bool = True,
        max_citations_per_paper: int = 100,
        citation_network_type: Literal["references", "citations", "all"] = "citations",
        rate_limit_delay: float = 1.0,
        publication_year: Optional[str] = None,
    ):
        """
        Extract references using title search
        Args:
            parent_paper_title: Title of the parent paper
            include_citations: Whether to fetch and add citing papers for each paper
            max_citations_per_paper: Maximum number of citing papers to add per paper
            citation_network_type: Option fetch papers.
            rate_limit_delay: Delay between API calls in seconds (default: 1.0)
            publication_year: Filter by publication year. e.g 2023:2025

        If title did not match raise error.
        """

        # Step 1: Check paper exist in semantic scholar.
        parent_paper_details = self.graph_builder.ss_client.get_paper_by_title(
            title=parent_paper_title
        )
        if not parent_paper_details:
            raise ValueError(f"Parent paper title {parent_paper_title} was not found.")
        logger.info(
            f"""Parent paper Details: {parent_paper_details['paperId']} - {parent_paper_details.get("title", "")} - Primary Author -{parent_paper_details['authors'][0]['name']}"""
        )

        # Step 2: Extract Reference and Citation from Parent Paper
        paper_to_process = self.get_parper_to_process(
            parent_paper_details,
            citation_network_type,
            max_citations_per_paper,
            publication_year,
        )

        # Step 3: Build knowledge graph with citation network
        stats, unsuccessful = (
            self.graph_builder.add_paper_with_citation_network_from_api(
                parent_paper_details=parent_paper_details,
                paper_to_process=paper_to_process or [],
                include_citations=include_citations,
                max_citations_per_paper=max_citations_per_paper,
                rate_limit_delay=rate_limit_delay,
                publication_year=publication_year,
            )
        )

        return stats, unsuccessful
