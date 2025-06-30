"""Pydantic configuration models for PaperSense application."""

from typing import List
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class MindsDBConfig(BaseModel):
    """MindsDB infrastructure configuration."""

    host: str = Field(default="localhost", description="MindsDB host address")
    port: int = Field(default=47334, description="MindsDB port number")


class AppConfig(BaseModel):
    """App settings configuration."""

    log_level: str = Field(default="INFO", description="Logging Level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Logging Format",
    )
    load_sample_data: bool = Field(default=False, description="Load sample data")
    sample_data_count: int = Field(
        default=50, description="Count of randomly sampled records inserted into KB"
    )
    openai_api_key: str = Field(default=None, description="Open AI api key")


class PostgresConfig(BaseModel):
    """PostgreSQL database configuration."""

    host: str = Field(default="localhost", description="PostgreSQL host address")
    port: int = Field(default=5432, description="PostgreSQL port number")
    user: str = Field(default="postgres", description="PostgreSQL username")
    password: str = Field(default="", description="PostgreSQL password")
    database: str = Field(default=None, description="PostgreSQL database name")
    table_name: str = Field(default=None, description="PostgreSQL table name")

    @validator("port")
    def validate_port(cls, v):
        """Validate port number is in valid range."""
        if not (1 <= v <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v


class StorageConfig(BaseModel):
    """KB storage config"""

    enable_pg_vector: bool = Field(
        default=None, description="Flag to enable or disable pyvector"
    )
    pg_vector_database: str = Field(
        default=None, description="pg vector db name to use"
    )
    pg_vector_table: str = Field(
        default=None, description="pg vector table name to use"
    )


class KnowledgeBaseConfig(BaseModel):
    """Knowledge base configuration."""

    name: str = Field(default=None, description="Knowledge base name")
    reranking_model: str = Field(default=None, description="Reranking model name")
    embedding_model: str = Field(default=None, description="Embedding model name")
    metadata_columns: List[str] = Field(
        default=[], description="List of metadata columns"
    )
    content_columns: List[str] = Field(
        default=[], description="List of content columns"
    )
    storage: StorageConfig = Field(default_factory=StorageConfig)


class AgentConfig(BaseModel):
    """Agent configuration."""

    openai_model: str = Field(default=None, description="AI model name")

class PaperSenseConfig(BaseSettings):
    """Main configuration model for PaperSense application."""

    mindsdb_infra: MindsDBConfig = Field(default_factory=MindsDBConfig)
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    knowledge_base: KnowledgeBaseConfig = Field(default_factory=KnowledgeBaseConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    app: AppConfig = Field(default_factory=AppConfig)
