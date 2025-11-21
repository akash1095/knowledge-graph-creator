import click
from knowledge_graph_creator.main import build_knowledge_graph


def parse_pages(pages_str: str) -> list[int]:
    """Parse page numbers from string (e.g., '32-42' or '32,33,34')."""
    if "-" in pages_str:
        start, end = map(int, pages_str.split("-"))
        return list(range(start, end + 1))
    return [int(p.strip()) for p in pages_str.split(",")]


@click.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option("--title", required=True, help="Title of the parent paper")
@click.option("--authors", required=True, help="Authors of the parent paper")
@click.option("--year", required=True, help="Publication year")
@click.option("--venue", required=True, help="Publication venue (journal/conference)")
@click.option(
    "--pages", required=True, help="Reference pages (e.g., '32-42' or '32,33,34')"
)
@click.option(
    "--max-papers", type=int, default=None, help="Maximum number of papers to process"
)
def main(pdf_path, title, authors, year, venue, pages, max_papers):
    """Build academic knowledge graph from PDF papers."""

    reference_pages = parse_pages(pages)

    build_knowledge_graph(
        pdf_path=pdf_path,
        parent_title=title,
        parent_authors=authors,
        parent_year=year,
        parent_venue=venue,
        reference_pages=reference_pages,
        max_papers=max_papers,
    )


if __name__ == "__main__":
    main()
