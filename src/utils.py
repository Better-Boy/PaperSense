"""
Utility functions for knowledge base and agent management.

This module provides functions for:
- Building SQL queries for knowledge base operations
- Processing text chunks and metadata
- Downloading and processing PDF files
- Creating and managing AI agents
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from . import config_loader as config

# Configure logger
logger = logging.getLogger(__name__)


class KnowledgeBaseError(Exception):
    """Custom exception for knowledge base operations."""

    pass


class FileProcessingError(Exception):
    """Custom exception for file processing operations."""

    pass


def build_values_clause(records: List[Dict[str, Any]], columns: List[str]) -> str:
    """
    Generate VALUES clause for SQL INSERT statement.

    Args:
        records: List of dictionaries containing record data
        columns: List of column names to include

    Returns:
        String representation of VALUES clause

    Raises:
        ValueError: If records or columns are empty
    """
    if not records or not columns:
        logger.error("Cannot build VALUES clause: records and columns cannot be empty")
        raise ValueError("Records and columns cannot be empty")

    logger.debug(
        f"Building VALUES clause for {len(records)} records with columns: {columns}"
    )

    values = []
    for i, record in enumerate(records):
        logger.debug(f"Processing record {i + 1}/{len(records)}")
        escaped_values = []
        for col in columns:
            # Properly escape SQL values and handle None values
            value = record[col]
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            if value is None:
                escaped_values.append("NULL")
            else:
                # Escape quotes in the value
                escaped_values.append(f'"{value}"')
        values.append(f"({', '.join(escaped_values)})")

    logger.debug(f"Successfully built VALUES clause with {len(values)} value sets")
    return ", ".join(values)


def escape_text(text: str) -> str:
    text = text.replace('\\', '\\\\')  # Escape backslashes first
    text = text.replace("'", "''")     # Escape single quotes
    text = text.replace('"', '""')     # Escape double quotes
    text = text.replace('\n', '\\n')   # Escape newlines
    text = text.replace('\r', '\\r')   # Escape carriage returns
    text = text.replace('\t', '\\t')   # Escape tabs
    text = text.replace('\0', '')   # Escape null bytes
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)  # Remove control chars
    return text


def build_insert_query(table: str, columns: List[str], values: str) -> str:
    """ Build SQL INSERT query. """
    if not table or not columns:
        logger.error(
            "Cannot build INSERT query: table name and columns cannot be empty"
        )
        raise ValueError("Table name and columns cannot be empty")

    logger.debug(
        f"Building INSERT query for table '{table}' with {len(columns)} columns"
    )

    columns_str = ", ".join(columns)
    query = f"INSERT INTO {table} ({columns_str}) VALUES {values};"

    logger.debug(f"Generated INSERT query (length: {len(query)} characters)")
    return query


def chunk_text(
    text: str, chunk_size: int = 1500, chunk_overlap: int = 300
) -> List[Dict[str, Any]]:
    """
    Split text into chunks using RecursiveCharacterTextSplitter.

    Args:
        text: Input text to be chunked
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of characters to overlap between chunks

    Returns:
        List of dictionaries containing chunked text

    Raises:
        ValueError: If text is empty or chunk_size is invalid
    """
    if not text.strip():
        logger.error("Cannot chunk text: input text is empty")
        raise ValueError("Text cannot be empty")
    if chunk_size <= 0:
        logger.error(f"Invalid chunk_size: {chunk_size}. Must be positive")
        raise ValueError("Chunk size must be positive")

    logger.info(
        f"Chunking text of length {len(text)} characters with chunk_size={chunk_size}, overlap={chunk_overlap}"
    )

    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

        docs = text_splitter.create_documents([text])
        chunks = []

        for i, doc in enumerate(docs):
            chunks.append({"text": doc.page_content})
            logger.debug(f"Created chunk {i + 1}: {len(doc.page_content)} characters")

        logger.info(f"Successfully created {len(chunks)} text chunks")
        return chunks

    except Exception as e:
        logger.error(f"Failed to chunk text: {e}")
        raise


def build_create_kb_query(name: str) -> str:
    """
    Build SQL query to create a knowledge base.

    Args:
        name: Name of the knowledge base

    Returns:
        SQL CREATE KNOWLEDGE_BASE statement

    Raises:
        ValueError: If name is empty
        KnowledgeBaseError: If required config values are missing
    """
    if not name:
        logger.error("Cannot create knowledge base: name cannot be empty")
        raise ValueError("Knowledge base name cannot be empty")

    logger.info(f"Building CREATE KNOWLEDGE_BASE query for '{name}'")

    try:
        metadata_cols = ", ".join([f"'{col}'" for col in config.kb.metadata_columns])
        content_cols = ", ".join([f"'{col}'" for col in config.kb.content_columns])

        logger.debug(f"Metadata columns: {config.kb.metadata_columns}")
        logger.debug(f"Content columns: {config.kb.content_columns}")
        logger.debug(f"Using embedding model: {config.kb.embedding_model}")
        logger.debug(f"Using reranking model: {config.kb.reranking_model}")

        storage = ""
        if config.kb_storage.enable_pg_vector:
            pg_vec_table = config.kb_storage.pg_vector_table
            if name != config.kb.name:
                pg_vec_table = f"vec_table_{name.replace('_kb', '')}"
            storage = (
                f"storage = {config.kb_storage.pg_vector_database}.{pg_vec_table},"
            )
        ollama_query = f"""
            CREATE KNOWLEDGE_BASE IF NOT EXISTS {name}
            USING
                {storage}
                embedding_model = {{
                    "provider": "ollama",
                    "model_name" : "nomic-embed-text",
                    "base_url":"http://localhost:11434"
                }},
                reranking_model = {{
                    "provider": "ollama",
                    "model_name": "llama3.2",
                    "base_url":"http://localhost:11434"
                }},
                content_columns = [{content_cols}],
                metadata_columns = [{metadata_cols}];
            """
        # openai_query = f"""
        #     CREATE KNOWLEDGE_BASE IF NOT EXISTS {name}
        #     USING
        #         {storage}
        #         embedding_model = {{
        #             "provider": "openai",
        #             "model_name": "{config.kb.embedding_model}",
        #             "api_key": "{config.app.openai_api_key}"
        #         }},
        #         reranking_model = {{
        #             "provider": "openai", 
        #             "model_name": "{config.kb.reranking_model}",
        #             "api_key": "{config.app.openai_api_key}"
        #         }},
        #         content_columns = [{content_cols}],
        #         metadata_columns = [{metadata_cols}];
        #     """

        logger.info(f"Successfully built CREATE KNOWLEDGE_BASE query for '{name}'")
        return ollama_query

    except KeyError as e:
        logger.error(f"Missing required config value for knowledge base creation: {e}")
        raise KnowledgeBaseError(f"Missing required config value: {e}")


def build_create_ai_table_query(name: str, prompt: dict) -> str:
    return f"""
            CREATE MODEL IF NOT EXISTS {name}
            PREDICT answer
            USING
                engine = 'openai',
                model_name = 'gpt-3.5-turbo',
                openai_api_key = '{config.app.openai_api_key}',
                prompt_template = '{prompt}';
            """

def build_ask_table_query(name: str, params: dict) -> str:
    return f"""
        SELECT answer FROM {name} WHERE title = '{params["title"]}' AND authors = '{params["authors"]}' AND abstract = '{params["abstract"]}' AND field = '{params["primary_category"]}';
    """

def build_search_query(
    name: str,
    query: str,
    metadata: Optional[Dict[str, Any]] = None,
    limit: int = 10,
    relevance_threshold: float = 0.5,
) -> str:
    """
    Build search query for knowledge base.

    Args:
        query: Search query string
        metadata: Optional metadata filters
        limit: Maximum number of results
        relevance_threshold: Minimum relevance score

    Returns:
        SQL search query string

    Raises:
        ValueError: If query is empty
    """
    if not query.strip():
        logger.error("Cannot build search query: query string is empty")
        raise ValueError("Query cannot be empty")

    logger.info(
        f"Building search query with limit={limit}, threshold={relevance_threshold}"
    )
    logger.debug(f"Search query: '{query[:100]}...' (truncated)")
    if metadata:
        logger.debug(f"Metadata filters: {metadata}")

    # Escape single quotes in query
    escaped_query = query.replace("'", "''")
    search_query = f"SELECT * from {name} where content = '{escaped_query}'"

    if metadata:
        search_query += " AND "
        conditions = []

        if "year" in metadata:
            conditions.append(f"published_year = '{metadata['year']}'")
            logger.debug(f"Added year filter: {metadata['year']}")
        if "category" in metadata:
            conditions.append(f"primary_category = '{metadata['category']}'")
            logger.debug(f"Added category filter: {metadata['category']}")

        search_query += " AND ".join(conditions)

    search_query += f" AND relevance >= {relevance_threshold} LIMIT {limit};"

    logger.debug(f"Generated search query (length: {len(search_query)} characters)")
    return search_query


def transform_results(results_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transform and clean search results.

    Args:
        results_list: Raw search results

    Returns:
        List of cleaned and deduplicated results
    """
    logger.info(f"Transforming {len(results_list)} search results")

    cleaned_results = []
    seen_articles = set()
    skipped_count = 0

    for i, result in enumerate(results_list):
        try:
            metadata = json.loads(result["metadata"])
            article_id = metadata["article_id"]

            # Skip duplicate articles
            if article_id in seen_articles:
                skipped_count += 1
                logger.debug(f"Skipping duplicate article: {article_id}")
                continue

            cleaned_result = {
                "article_id": article_id,
                "authors": metadata["authors"],
                "categories": metadata["categories"],
                "primary_category": metadata["primary_category"],
                "published_year": metadata["published_year"],
                "title": metadata.get("title", ""),
                "abstract": metadata.get("abstract", ""),
                "relevance": round(result["relevance"], 3),
            }

            seen_articles.add(article_id)
            cleaned_results.append(cleaned_result)
            logger.debug(f"Processed result {i + 1}/{len(results_list)}: {article_id}")

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error processing result {i + 1}/{len(results_list)}: {e}")
            skipped_count += 1
            continue

    logger.info(
        f"Transformation complete: {len(cleaned_results)} valid results, {skipped_count} skipped"
    )
    return cleaned_results


def build_create_agent_query(
    name: str, knowledge_bases: List[str], tables: List[str]
) -> str:
    """
    Build SQL query to create an AI agent.

    Args:
        name: Name of the agent
        knowledge_bases: List of knowledge base names to include
        tables: List of table names to include

    Returns:
        SQL CREATE AGENT statement

    Raises:
        ValueError: If name is empty
    """
    if not name:
        logger.error("Cannot create agent: name cannot be empty")
        raise ValueError("Agent name cannot be empty")

    logger.info(f"Building CREATE AGENT query for '{name}'")
    logger.debug(f"Knowledge bases: {knowledge_bases}")
    logger.debug(f"Tables: {tables}")

    kb_list = ", ".join([f"'{kb}'" for kb in knowledge_bases])
    table_list = ", ".join([f"'{table}'" for table in tables])

    query = f"""
    CREATE AGENT IF NOT EXISTS {name}
    USING
        model = '{config.agent.openai_model}',
        openai_api_key = '{config.app.openai_api_key}',
        include_knowledge_bases= [{kb_list}],
        include_tables=[{table_list}],
        prompt_template='
            mindsdb.{name} stores a research paper published on arxiv.
            Retrieve the most relevant text from the attached knowledge base. 
            If you are not sure of the answer, then promptly say "I am not sure"';
    """

    logger.info(f"Successfully built CREATE AGENT query for '{name}'")
    return query


def build_chat_agent_query(name: str, query: str) -> str:
    """
    Build query to chat with an AI agent.

    Args:
        name: Name of the agent
        query: Question to ask the agent

    Returns:
        SQL query to interact with agent

    Raises:
        ValueError: If name or query is empty
    """
    if not name or not query:
        logger.error("Cannot build chat query: agent name and query cannot be empty")
        raise ValueError("Agent name and query cannot be empty")

    logger.info(f"Building chat query for agent '{name}'")
    logger.debug(f"Query: '{query[:100]}...' (truncated)")

    # Escape double quotes in query
    escaped_query = query.replace('"', '""')
    chat_query = f'SELECT answer FROM {name} WHERE question = "{escaped_query}";'

    logger.debug(f"Generated chat query (length: {len(chat_query)} characters)")
    return chat_query


def generate_agent_name(paper_id: str) -> str:
    """
    Generate agent name from paper ID.

    Args:
        paper_id: Unique paper identifier

    Returns:
        Formatted agent name
    """
    agent_name = paper_id.replace(".", "_") + "_agent"
    logger.debug(f"Generated agent name '{agent_name}' from paper ID '{paper_id}'")
    return agent_name


def generate_kb_name(paper_id: str) -> str:
    """
    Generate knowledge base name from paper ID.

    Args:
        paper_id: Unique paper identifier

    Returns:
        Formatted knowledge base name
    """
    kb_name = paper_id.replace(".", "_") + "_kb"
    logger.debug(f"Generated KB name '{kb_name}' from paper ID '{paper_id}'")
    return kb_name
