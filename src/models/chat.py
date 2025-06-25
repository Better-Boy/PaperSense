"""Chat-related Pydantic models."""

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """Request model for chat API endpoint.
    
    Validates chat requests including ArXiv paper ID format and query content.
    """
    
    arxiv_id: str = Field(
        ...,
        description="ArXiv paper ID in format YYMM.NNNNN or YYMM.NNNNNvX",
        example="2301.01234"
    )
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Question or query about the paper",
        example="What is the main contribution of this paper?"
    )

    @field_validator('arxiv_id')
    def validate_arxiv_id(cls, value: str) -> str:
        """Validate and clean ArXiv ID format.
        
        Args:
            value: Raw ArXiv ID string
            
        Returns:
            Cleaned ArXiv ID
            
        Raises:
            ValueError: If ArXiv ID is invalid
        """
        if not value or len(value.strip()) == 0:
            raise ValueError("ArXiv ID cannot be empty")
        
        cleaned_id = value.strip()
        
        # Additional validation for ArXiv ID format
        if not cleaned_id.replace('.', '').replace('v', '').isdigit():
            raise ValueError("ArXiv ID contains invalid characters")
            
        return cleaned_id

    @field_validator('query')
    def validate_query(cls, value: str) -> str:
        """Validate and clean query string.
        
        Args:
            value: Raw query string
            
        Returns:
            Cleaned query string
            
        Raises:
            ValueError: If query is invalid
        """
        if not value or len(value.strip()) == 0:
            raise ValueError("Query cannot be empty")
        
        cleaned_query = value.strip()
        
        # Check for potentially harmful content
        forbidden_patterns = ['<script', 'javascript:', 'data:']
        if any(pattern in cleaned_query.lower() for pattern in forbidden_patterns):
            raise ValueError("Query contains potentially harmful content")
            
        return cleaned_query

    class Config:
        """Pydantic configuration."""
        
        model_config = {
            "json_schema_extra": {
                "arxiv_id": "2301.01234",
                "query": "What is the main contribution of this paper?"
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat API endpoint.
    
    Contains the agent's response along with metadata about the conversation.
    """
    
    response: str = Field(
        ...,
        description="Agent's response to the query",
        example="The main contribution of this paper is..."
    )
    
    class Config:
        """Pydantic configuration."""
        
        model_config = {
            "json_schema_extra": {
                "response": "The main contribution of this paper is the development of a novel attention mechanism that improves transformer efficiency by 25%."
            }
        }