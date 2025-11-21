# Knowledge Graph Creator

A Python tool for building academic knowledge graphs from research papers. Extract references from PDFs and
automatically create a Neo4j knowledge graph using the Semantic Scholar API.

## 📋 Overview

This tool processes academic papers (PDFs), extracts their references, and builds a knowledge graph in Neo4j that
captures:

- Papers and their metadata (title, authors, year, venue, citations)
- Citation relationships between papers
- Author information and co-authorship networks
- Publication venues

## 🏗️ Repository Structure

knowledge_graph_creator/
├── knowledge_graph_creator/ # Main package
│ ├── __init__.py
│ ├── main.py # Simple entry point
│ ├── cli.py # CLI interface using Click
│ ├── orchestrator.py # Pipeline orchestration
│ ├── academic_graph_builder.py # Knowledge graph construction
│ ├── semantic_scholar_client.py # Semantic Scholar API client
│ │
│ ├── db_neo4j/ # Neo4j database layer
│ │ ├── __init__.py
│ │ └── academic_graph.py # Neo4j operations
│ │
│ ├── doc_extractor/ # PDF text extraction
│ │ ├── __init__.py
│ │ ├── base.py
│ │ └── pdf_extractor.py # PyMuPDF-based extractor
│ │
│ ├── extractors/ # Reference parsing
│ │ ├── __init__.py
│ │ ├── reference_extractor.py # Extract reference text
│ │ └── reference_details.py # Parse reference details
│ │
│ └── patterns.py # Reference patterns
│
├── data/ # PDF files (gitignored)
├── experiments/ # Research notebooks
├── tests/ # Unit tests
├── .env.example # Environment variables template
├── requirements.txt # Python dependencies
└── README.md # This file

### Prerequisites

- Python 3.10+
- Neo4j database (4.4+ or 5.x)
- Semantic Scholar API key (optional but recommended)

### Installation

1. **Clone the repository:**

```bash
git clone https://github.com/yourusername/knowledge_graph_creator.git
cd knowledge_graph_creator
```

2. **Install dependencies:**

```bash
pip install -r requirements.txt
```

3. **Set up environment variables:**

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
SS_API_KEY=your_semantic_scholar_api_key
```

4. **Start Neo4j:**

```bash
# If using Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:latest
```

## 📖 Usage

### Command Line Interface (CLI)

Process a PDF and build a knowledge graph:

```bash
python -m knowledge_graph_creator.cli \
  data/paper.pdf \
  --title "Your Paper Title" \
  --authors "First Author, Second Author" \
  --year "2023" \
  --venue "Conference/Journal Name" \
  --pages "32-42" \
  --max-papers 100
```

**Options:**

- `pdf_path`: Path to the PDF file (required)
- `--title`: Title of the parent paper (required)
- `--authors`: Authors of the paper (required)
- `--year`: Publication year (required)
- `--venue`: Publication venue (required)
- `--pages`: Reference pages (e.g., "32-42" or "32,33,34") (required)
- `--max-papers`: Maximum number of references to process (optional)

### Programmatic Usage

```python
from knowledge_graph_creator.main import build_knowledge_graph

build_knowledge_graph(
    pdf_path="data/paper.pdf",
    parent_title="Knowledge Graph Embedding: A Survey",
    parent_authors="John Doe, Jane Smith",
    parent_year="2023",
    parent_venue="ACM Computing Surveys",
    reference_pages=[32, 33, 34, 35, 36, 37, 38, 39, 40, 41],
    max_papers=100
)
```

### Python API

```python
from knowledge_graph_creator.orchestrator import PDFToKnowledgeGraphOrchestrator
from knowledge_graph_creator.extractors.reference_details import ReferenceDetails

# Initialize orchestrator
orchestrator = PDFToKnowledgeGraphOrchestrator(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="your_password",
    ss_api_key="your_api_key"
)

# Create parent paper
parent_paper = ReferenceDetails(
    id_=0,
    title="Your Paper Title",
    authors="Authors",
    publish="Venue",
    year="2023",
    page_or_volume=""
)

# Process PDF
successful, unsuccessful = orchestrator.process_pdf_to_graph(
    pdf_path="data/paper.pdf",
    parent_paper=parent_paper,
    reference_pages=list(range(32, 42)),
    max_papers=100
)

print(f"Successfully added: {len(successful)} papers")
print(f"Failed to add: {len(unsuccessful)} papers")
```

## 🔍 Features

### PDF Processing

- Extract text from PDF files using PyMuPDF
- Support for multi-page reference sections
- Flexible page selection

### Reference Extraction

- Pattern-based reference parsing (bracketed numbers, bullets, etc.)
- Automatic extraction of title, authors, year, and venue
- Handles various citation formats

### Knowledge Graph

- Neo4j-based storage
- Nodes: Papers, Authors, Venues
- Relationships: CITES, AUTHORED_BY, PUBLISHED_IN
- Rich metadata: citations, abstracts, fields of study

### API Integration

- Semantic Scholar API for paper metadata
- Automatic rate limiting
- Error handling and retry logic

## 📊 Knowledge Graph Schema

```cypher
# Nodes
(:Paper {paper_id, title, year, abstract, citation_count, ...})
(:Author {author_id, name})
(:Venue {venue_id, name, type})

# Relationships
(Paper)-[:CITES]->(Paper)
(Paper)-[:AUTHORED_BY {author_order}]->(Author)
(Paper)-[:PUBLISHED_IN]->(Venue)
```

## 🔧 Configuration

### Environment Variables

| Variable         | Description              | Default                 |
|------------------|--------------------------|-------------------------|
| `NEO4J_URI`      | Neo4j connection URI     | `bolt://localhost:7687` |
| `NEO4J_USER`     | Neo4j username           | `neo4j`                 |
| `NEO4J_PASSWORD` | Neo4j password           | -                       |
| `SS_API_KEY`     | Semantic Scholar API key | -                       |

### Reference Patterns

Supported reference patterns (configurable in `patterns.py`):

- Bracketed numbers: `[1]`, `[2]`, etc.
- Bullets: `•`, `·`
- Custom patterns via regex

## 🧪 Testing

Run tests:

```bash
pytest tests/
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a pull request

## 📝 Examples

### Query the Knowledge Graph

Find all papers by an author:

```python
from knowledge_graph_creator.db_neo4j.academic_graph import AcademicKnowledgeGraph

kg = AcademicKnowledgeGraph(uri="bolt://localhost:7687", user="neo4j", password="password")
papers = kg.get_author_papers(author_id="author_id_here")
# Find co-authors:
coauthors = kg.get_coauthors(author_id="author_id_here")
# Search papers by title:
kg.search_papers_by_title(search_term="knowledge graph", limit=10)
```

## 🐛 Troubleshooting

**Progress bar issues:**

- Use `tqdm.write()` instead of `print()` for stable output
- Adjust `mininterval` parameter for smoother updates

**API rate limits:**

- Set `rate_limit_delay` higher in `AcademicGraphBuilder`
- Use a Semantic Scholar API key for higher limits

**Neo4j connection errors:**

- Verify Neo4j is running: `docker ps` or check local service
- Check credentials in `.env` file
- Ensure ports 7474 and 7687 are not blocked

## 📄 License

See `LICENSE` file.

## 🙏 Acknowledgments

- [Semantic Scholar](https://www.semanticscholar.org/) for the API
- [Neo4j](https://neo4j.com/) for the graph database
- [PyMuPDF](https://pymupdf.readthedocs.io/) for PDF processing

## 📧 Contact

For questions or feedback, please open an issue on GitHub.

```

This README provides:
- Clear overview and purpose
- Detailed repository structure
- Step-by-step installation guide
- Multiple usage examples (CLI, programmatic, API)
- Configuration details
- Troubleshooting tips
- Contributing guidelines
- Complete feature list with schema documentation