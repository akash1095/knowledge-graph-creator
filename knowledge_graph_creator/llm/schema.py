from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class Relationship(BaseModel):
    """Represents a single semantic relationship between two research papers."""

    type: str = Field(
        ...,
        description="The type of semantic relationship (e.g., Extends, Solves, Outperforms, Validates, Contradicts, Requires, Enables, Adapts-from, Achieves, Challenges)",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        ..., description="Confidence level of the identified relationship"
    )
    evidence: str = Field(
        ...,
        description="Specific text or reasoning from the abstracts supporting this relationship in 20 words",
    )
    explanation: str = Field(
        ...,
        description="Brief explanation of why this relationship exists between the papers in 20 words",
    )


class RelationshipAnalysis(BaseModel):
    """Complete analysis of semantic relationships between two research papers."""

    relationships: List[Relationship] = Field(
        default_factory=list,
        description="List of identified semantic relationships between the papers",
    )
    no_relationship_reason: Optional[str] = Field(
        default=None,
        description="Explanation for why no relationships were found, if applicable",
    )
