"""Pydantic configuration models for PaperSense application."""

from typing import Optional, List
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class MindsDBConfig(BaseModel):
    """MindsDB infrastructure configuration."""
    
    MINDSDB_HOST: str = Field(default="localhost", description="MindsDB host address")
    MINDSDB_PORT: int = Field(default=47334, description="MindsDB port number")


class PostgresConfig(BaseModel):
    """PostgreSQL database configuration."""
    
    HOST: str = Field(default="localhost", description="PostgreSQL host address")
    PORT: int = Field(default=5432, description="PostgreSQL port number")
    USER: str = Field(default="postgres", description="PostgreSQL username")
    PASSWORD: str = Field(default="", description="PostgreSQL password")
    DATABASE: str = Field(default=None, description="PostgreSQL database name")
    TABLE_NAME: str = Field(default=None, description="PostgreSQL table name")
    
    @validator('PORT')
    def validate_port(cls, v):
        """Validate port number is in valid range."""
        if not (1 <= v <= 65535):
            raise ValueError('Port must be between 1 and 65535')
        return v


class KnowledgeBaseConfig(BaseModel):
    """Knowledge base configuration."""
    
    NAME: str = Field(default=None, description="Knowledge base name")
    RERANKING_MODEL: str = Field(default=None, description="Reranking model name")
    EMBEDDING_MODEL: str = Field(default=None, description="Embedding model name")
    METADATA_COLUMNS: List[str] = Field(default=[], description="List of metadata columns")
    CONTENT_COLUMNS: List[str] = Field(default=[], description="List of content columns")
    OPENAI_API_KEY: str = Field(default=None, description="Open AI api key")


class AgentConfig(BaseModel):
    """Agent configuration."""
    
    OPENAI_MODEL: str = Field(default=None, description="AI model name")

class PaperSenseConfig(BaseSettings):
    """Main configuration model for PaperSense application."""
    
    MINDSDB_INFRA: MindsDBConfig = Field(default_factory=MindsDBConfig)
    POSTGRES: PostgresConfig = Field(default_factory=PostgresConfig)
    KNOWLEDGE_BASE: KnowledgeBaseConfig = Field(default_factory=KnowledgeBaseConfig)
    AGENT: AgentConfig = Field(default_factory=AgentConfig)
    
    class Config:
        """Pydantic configuration."""
        env_file = '.env'
        env_file_encoding = 'utf-8'
        env_nested_delimiter = '__'
        case_sensitive = True
        
        # Allow extra fields for flexibility
        extra = 'allow'


__all__ = [
    'PaperSenseConfig',
    'MindsDBConfig',
    'PostgresConfig', 
    'KnowledgeBaseConfig',
    'AgentConfig'
]