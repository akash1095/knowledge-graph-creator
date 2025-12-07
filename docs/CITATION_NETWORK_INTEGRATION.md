# Citation Network Integration Guide

## Overview

This guide explains how to integrate citation and reference data for each paper you add to the knowledge graph. The Semantic Scholar API provides rich citation network data that can significantly enhance your knowledge graph.

## Architecture

### Data Flow

```
PDF Paper
    ↓
Extract References → Add to DB
    ↓
For Each Paper:
    ├── Fetch Citations (papers that cite this paper)
    │   └── Add citing papers + create CITES relationships
    └── Fetch References (papers this paper cites)
        └── Add referenced papers + create CITES relationships
```

### Graph Schema

```cypher
# Nodes
(:Paper {paper_id, title, year, citation_count, ...})
(:Author {author_id, name})
(:Venue {venue_id, name, type})

# Relationships
(Paper)-[:CITES]->(Paper)           # Citation relationship
(Paper)-[:AUTHORED_BY]->(Author)    # Authorship
(Paper)-[:PUBLISHED_IN]->(Venue)    # Publication venue
```

## Implementation Approaches

### Approach 1: Same Logic (Recommended) ✅

**Use the same `Paper` nodes and `CITES` relationships for all papers.**

**Advantages:**
- Creates a unified, interconnected knowledge graph
- Enables powerful graph queries (e.g., find citation chains, influential papers)
- Avoids data duplication
- Leverages Neo4j's graph capabilities

**Use Cases:**
- Building comprehensive citation networks
- Analyzing research impact and influence
- Finding related work and research trends
- Identifying key papers in a field

**Example:**
```python
from knowledge_graph_creator.orchestrator import PDFToKnowledgeGraphOrchestrator
from knowledge_graph_creator.extractors.reference_details import ReferenceDetails

orchestrator = PDFToKnowledgeGraphOrchestrator(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password",
    ss_api_key="your_api_key"
)

parent_paper = ReferenceDetails(
    id_=0,
    title="Your Paper Title",
    authors="Authors",
    publish="Venue",
    year="2023",
    page_or_volume=""
)

# Build extended citation network
stats, unsuccessful = orchestrator.process_pdf_to_graph_with_network(
    pdf_path="data/paper.pdf",
    parent_paper=parent_paper,
    reference_pages=list(range(32, 42)),
    max_papers=10,
    include_citations=True,      # Add papers that cite each paper
    include_references=True,     # Add papers referenced by each paper
    max_citations_per_paper=50,  # Limit citations per paper
    max_references_per_paper=50  # Limit references per paper
)

print(f"Total papers: {stats['total_papers']}")
print(f"Total relationships: {stats['total_relationships']}")
```

### Approach 2: Separate Storage (Alternative)

**Store citation/reference metadata separately from the main graph.**

**Advantages:**
- Clearer separation of concerns
- Can track metadata about citations (e.g., context, importance)
- Easier to manage different data sources

**Disadvantages:**
- More complex queries
- Data duplication
- Loses graph connectivity benefits

**Implementation (if needed):**
You could add properties to the `CITES` relationship or create separate metadata nodes:

```cypher
# Option A: Add properties to CITES relationship
(Paper)-[:CITES {
    source: "semantic_scholar",
    is_influential: true,
    context: "background"
}]->(Paper)

# Option B: Create separate citation metadata nodes
(Paper)-[:HAS_CITATION_METADATA]->(CitationMetadata {
    citing_papers: [...],
    citation_count: 100,
    influential_citations: 10
})
```

## API Methods

### SemanticScholarClient

#### `get_paper_citations(paper_id, limit, offset)`
Fetch papers that cite the given paper.

**Parameters:**
- `paper_id`: Semantic Scholar paper ID
- `limit`: Maximum number of citations (max 1000)
- `offset`: Pagination offset

**Returns:**
```python
{
    "data": [
        {
            "citingPaper": {
                "paperId": "...",
                "title": "...",
                "year": 2023,
                # ... full paper data
            }
        }
    ],
    "offset": 0,
    "next": 100
}
```

#### `get_paper_references(paper_id, limit, offset)`
Fetch papers referenced by the given paper.

**Parameters:**
- `paper_id`: Semantic Scholar paper ID
- `limit`: Maximum number of references (max 1000)
- `offset`: Pagination offset

**Returns:**
```python
{
    "data": [
        {
            "citedPaper": {
                "paperId": "...",
                "title": "...",
                "year": 2020,
                # ... full paper data
            }
        }
    ],
    "offset": 0,
    "next": 100
}
```

### AcademicGraphBuilder

#### `add_paper_with_citation_network(...)`
Build an extended knowledge graph with citation network.

**Parameters:**
- `parent_paper`: Parent paper details
- `references`: List of references from PDF
- `max_papers`: Max papers from PDF to process
- `include_citations`: Whether to fetch citing papers
- `include_references`: Whether to fetch referenced papers
- `max_citations_per_paper`: Max citations per paper
- `max_references_per_paper`: Max references per paper
- `rate_limit_delay`: Delay between API calls (seconds)

**Returns:**
```python
(
    {
        "parent_papers": 1,
        "pdf_references": 10,
        "citations_added": 50,
        "references_added": 100,
        "total_papers": 161,
        "total_relationships": 160
    },
    [unsuccessful_papers]
)
```

## Usage Examples

### Example 1: Build Complete Citation Network

```python
stats, unsuccessful = orchestrator.process_pdf_to_graph_with_network(
    pdf_path="data/paper.pdf",
    parent_paper=parent_paper,
    reference_pages=list(range(32, 42)),
    max_papers=None,  # Process all references
    include_citations=True,
    include_references=True,
    max_citations_per_paper=100,
    max_references_per_paper=100
)
```

### Example 2: Citations Only (Forward Citations)

```python
stats, unsuccessful = orchestrator.process_pdf_to_graph_with_network(
    pdf_path="data/paper.pdf",
    parent_paper=parent_paper,
    reference_pages=list(range(32, 42)),
    max_papers=10,
    include_citations=True,   # Include citing papers
    include_references=False, # Skip references
    max_citations_per_paper=50,
    max_references_per_paper=0
)
```

### Example 3: References Only (Backward Citations)

```python
stats, unsuccessful = orchestrator.process_pdf_to_graph_with_network(
    pdf_path="data/paper.pdf",
    parent_paper=parent_paper,
    reference_pages=list(range(32, 42)),
    max_papers=10,
    include_citations=False,  # Skip citing papers
    include_references=True,  # Include references
    max_citations_per_paper=0,
    max_references_per_paper=50
)
```

## Querying the Citation Network

### Find Papers That Cite a Specific Paper

```cypher
MATCH (citing:Paper)-[:CITES]->(cited:Paper {paper_id: "your_paper_id"})
RETURN citing.title, citing.year, citing.citation_count
ORDER BY citing.citation_count DESC
LIMIT 10
```

### Find Citation Chains

```cypher
MATCH path = (p1:Paper)-[:CITES*1..3]->(p2:Paper {paper_id: "target_paper_id"})
RETURN path
LIMIT 10
```

### Find Most Influential Papers

```cypher
MATCH (p:Paper)
RETURN p.title, p.year, p.citation_count
ORDER BY p.citation_count DESC
LIMIT 20
```

### Find Co-Citation Networks

```cypher
MATCH (p1:Paper)-[:CITES]->(cited:Paper)<-[:CITES]-(p2:Paper)
WHERE p1 <> p2
RETURN p1.title, p2.title, cited.title, count(*) as co_citations
ORDER BY co_citations DESC
LIMIT 10
```

## Best Practices

1. **Rate Limiting**: Use appropriate delays between API calls (default: 1 second)
2. **Limit Network Size**: Set reasonable limits for citations/references per paper
3. **Incremental Building**: Start small and expand gradually
4. **Monitor API Usage**: Semantic Scholar has rate limits
5. **Handle Errors**: Some papers may not have citation data available

## Performance Considerations

- **API Calls**: Each paper requires 1-3 API calls (paper data, citations, references)
- **Database Operations**: Use MERGE to avoid duplicates
- **Network Size**: Can grow exponentially (limit with max_citations/references parameters)
- **Processing Time**: Expect ~1-2 seconds per paper with rate limiting

## Troubleshooting

### Issue: Too many API calls
**Solution**: Reduce `max_citations_per_paper` and `max_references_per_paper`

### Issue: Graph too large
**Solution**: Set `max_papers` to limit PDF references processed

### Issue: Rate limit errors
**Solution**: Increase `rate_limit_delay` parameter

### Issue: Missing citation data
**Solution**: Some papers may not have citation data in Semantic Scholar

