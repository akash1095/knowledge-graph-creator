from typing import List

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
    ):
        self.pdf_reader = PyMuPDFReader()
        self.reference_extractor = ReferenceExtractor(ReferencePattern.BRACKETED_NUMBER)
        self.details_extractor = ReferenceDetailsExtractor()
        self.graph_builder = AcademicGraphBuilder(
            uri=neo4j_uri, user=neo4j_user, password=neo4j_password, api_key=ss_api_key
        )

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
