"""Search-related Pydantic models."""

from pydantic import BaseModel, Field, validator
from typing import List, Optional


class SearchFilters(BaseModel):
    """Model for search filter parameters."""
    
    category: Optional[str] = Field(
        None,
        max_length=50,
        description="Paper category filter (e.g., 'cs', 'math')",
        example="cs.AI"
    )
    year: Optional[int] = Field(
        None,
        ge=1991,
        le=2030,
        description="Publication year filter",
        example=2023
    )
    
    @validator('category')
    def validate_category(cls, value: Optional[str]) -> Optional[str]:
        """Validate category format.
        
        Args:
            value: Category string
            
        Returns:
            Cleaned category string or None
        """
        if value is None:
            return None
            
        cleaned = value.strip()
        if not cleaned:
            return None
            
        # Basic validation for ArXiv category format
        if '.' in cleaned and len(cleaned.split('.')) == 2:
            subject, subcat = cleaned.split('.')
            if len(subject) >= 2 and len(subcat) >= 1:
                return cleaned.lower()
        
        return cleaned.lower()


class PaperResult(BaseModel):
    """Model for individual paper search result."""
    
    article_id: str = Field(
        ...,
        description="ArXiv paper ID",
        example="2301.01234"
    )
    title: str = Field(
        ...,
        description="Paper title",
        example="Attention Is All You Need"
    )
    authors: str = Field(
        ...,
        description="Paper authors",
        example="Ashish Vaswani, Noam Shazeer"
    )
    summary: str = Field(
        ...,
        description="Paper abstract",
        example="The dominant sequence transduction models..."
    )
    categories: str = Field(
        ...,
        description="ArXiv categories",
        example=["cs.CL", "cs.AI"]
    )
    published_year: str = Field(
        ...,
        description="Publication year",
        example="2017"
    )
    relevance: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Relevance score (0-1)",
        example=0.95
    )


class SearchResponse(BaseModel):
    """Response model for search API endpoint.
    
    Contains search results along with metadata about the search operation.
    """
    
    results: List[PaperResult] = Field(
        default_factory=list,
        description="List of paper search results"
    )
    
    class Config:
        """Pydantic configuration."""
        
        model_config = {
            "json_schema_extra": {
                "results": [
                    {
                        "arxiv_id": "1706.03762",
                        "title": "Attention Is All You Need",
                        "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
                        "summary": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
                        "categories": ["cs.CL", "cs.AI"],
                        "published_year": "2017",
                        "relevance": 0.95
                    }
                ]
            }
        }


class SearchRequest(BaseModel):
    """Request model for search API endpoint."""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Search query string",
        example="attention mechanism transformer"
    )
    filters: Optional[SearchFilters] = Field(
        None,
        description="Optional search filters"
    )
    
    @validator('query')
    def validate_query(cls, value: str) -> str:
        """Validate and clean search query.
        
        Args:
            value: Raw query string
            
        Returns:
            Cleaned query string
            
        Raises:
            ValueError: If query is invalid
        """
        if not value or len(value.strip()) == 0:
            raise ValueError("Search query cannot be empty")
        
        cleaned_query = value.strip()
        
        # Check for potentially harmful content
        forbidden_patterns = ['<script', 'javascript:', 'data:', 'DROP TABLE']
        if any(pattern in cleaned_query.lower() for pattern in forbidden_patterns):
            raise ValueError("Query contains potentially harmful content")
            
        return cleaned_query
    
    class Config:
        """Pydantic configuration."""
        
        model_config = {
            "json_schema_extra": {
                "query": "attention mechanism transformer",
                "filters": {
                    "category": "cs.ai",
                    "year": 2017
                }
            }
        }