import os

from dotenv import load_dotenv

from knowledge_graph_creator.extractors.reference_details import ReferenceDetails
from knowledge_graph_creator.orchestrator import PDFToKnowledgeGraphOrchestrator


def build_knowledge_graph(
    pdf_path: str,
    parent_title: str,
    parent_authors: str,
    parent_year: str,
    parent_venue: str,
    reference_pages: list[int],
    max_papers: int = None,
):
    """
    Build a knowledge graph from a PDF paper.

    Args:
        pdf_path: Path to the PDF file
        parent_title: Title of the parent paper
        parent_authors: Authors of the parent paper
        parent_year: Publication year
        parent_venue: Publication venue
        reference_pages: List of page numbers with references
        max_papers: Maximum number of papers to process
    """
    load_dotenv()

    # Create parent paper details
    parent_paper = ReferenceDetails(
        id_=0,
        title=parent_title,
        authors=parent_authors,
        publish=parent_venue,
        year=parent_year,
        page_or_volume="",
    )

    # Initialize orchestrator
    orchestrator = PDFToKnowledgeGraphOrchestrator(
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD"),
        ss_api_key=os.getenv("SS_API_KEY"),
    )

    # Process PDF and build graph
    print(f"Processing PDF: {pdf_path}")
    print(f"Parent paper: {parent_title}")
    print(f"Reference pages: {reference_pages}")

    successful, unsuccessful = orchestrator.process_pdf_to_graph(
        pdf_path=pdf_path,
        parent_paper=parent_paper,
        reference_pages=reference_pages,
        max_papers=max_papers,
    )

    # Print results
    print(f"\n✓ Successfully added: {len(successful)} papers")
    print(f"✗ Failed to add: {len(unsuccessful)} papers")

    if unsuccessful:
        print("\nFailed papers:")
        for ref in unsuccessful[:10]:  # Show first 10
            print(f"  - {ref.title}")


if __name__ == "__main__":
    build_knowledge_graph(
        pdf_path="data/3643806.pdf",
        parent_title="Knowledge Graph Embedding: A Survey from the Perspective of Representation Spaces",
        parent_authors="Jiahang Cao",
        parent_year="2022",
        parent_venue="ACM Computing Surveys",
        reference_pages=list(range(32, 42)),
        max_papers=100,
    )
