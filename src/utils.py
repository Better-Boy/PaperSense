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
import os
import re
import tempfile
from typing import Any, Dict, List, Optional

import pymupdf
import requests
import string
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
    
    logger.debug(f"Building VALUES clause for {len(records)} records with columns: {columns}")
    
    values = []
    for i, record in enumerate(records):
        logger.debug(f"Processing record {i+1}/{len(records)}")
        escaped_values = []
        
        for col in columns:
            # Properly escape SQL values and handle None values
            value = record[col]
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            if value is None:
                escaped_values.append("NULL")
            else:
                # Escape quotes in the value
                escaped_values.append(f'"{value}"')
        values.append(f"({', '.join(escaped_values)})")
    
    logger.debug(f"Successfully built VALUES clause with {len(values)} value sets")
    return ', '.join(values)

def escape_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
        
    # Remove control characters except common ones
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

    translator = str.maketrans('', '', string.punctuation)
    text = text.strip().translate(translator)
        
    return text

def build_insert_query(table: str, columns: List[str], values: str) -> str:
    """
    Build SQL INSERT query.
    
    Args:
        table: Target table name
        columns: List of column names
        values: VALUES clause string
        
    Returns:
        Complete SQL INSERT statement
        
    Raises:
        ValueError: If table name or columns are empty
    """
    if not table or not columns:
        logger.error("Cannot build INSERT query: table name and columns cannot be empty")
        raise ValueError("Table name and columns cannot be empty")
    
    logger.debug(f"Building INSERT query for table '{table}' with {len(columns)} columns")
    
    columns_str = ', '.join(columns)
    query = f"INSERT INTO {table} ({columns_str}) VALUES {values};"
    
    logger.debug(f"Generated INSERT query (length: {len(query)} characters)")
    return query


def chunk_text(text: str, chunk_size: int = 2000, chunk_overlap: int = 300) -> List[Dict[str, Any]]:
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
    
    logger.info(f"Chunking text of length {len(text)} characters with chunk_size={chunk_size}, overlap={chunk_overlap}")
    
    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
        
        docs = text_splitter.create_documents([text])
        chunks = []
        
        for i, doc in enumerate(docs):
            chunks.append({"text": doc.page_content})
            logger.debug(f"Created chunk {i+1}: {len(doc.page_content)} characters")
        
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
        metadata_cols = ', '.join([f"'{col}'" for col in config.kb.METADATA_COLUMNS])
        content_cols = ', '.join([f"'{col}'" for col in config.kb.CONTENT_COLUMNS])
        
        logger.debug(f"Metadata columns: {config.kb.METADATA_COLUMNS}")
        logger.debug(f"Content columns: {config.kb.CONTENT_COLUMNS}")
        logger.debug(f"Using embedding model: {config.kb.EMBEDDING_MODEL}")
        logger.debug(f"Using reranking model: {config.kb.RERANKING_MODEL}")
        
        storage = ""
        if config.kb_storage.ENABLE_PG_VECTOR:
            pg_vec_table = config.kb_storage.PG_VECTOR_TABLE
            if name != config.kb.NAME:
                pg_vec_table = f"vec_table_{name.replace("_kb", "")}"
            storage = f"storage = {config.kb_storage.PG_VECTOR_DATABASE}.{pg_vec_table},"
        
        query = f"""
            CREATE KNOWLEDGE_BASE IF NOT EXISTS {name}
            USING
                {storage}
                embedding_model = {{
                    "provider": "openai",
                    "model_name": "{config.kb.EMBEDDING_MODEL}",
                    "api_key": "{config.kb.OPENAI_API_KEY}"
                }},
                reranking_model = {{
                    "provider": "openai", 
                    "model_name": "{config.kb.RERANKING_MODEL}",
                    "api_key": "{config.kb.OPENAI_API_KEY}"
                }},
                content_columns = [{content_cols}],
                metadata_columns = [{metadata_cols}];
            """
        
        logger.info(f"Successfully built CREATE KNOWLEDGE_BASE query for '{name}'")
        return query
        
    except KeyError as e:
        logger.error(f"Missing required config value for knowledge base creation: {e}")
        raise KnowledgeBaseError(f"Missing required config value: {e}")


def get_metadata(paper_id: str, meta_df, primary_category: str) -> Dict[str, Any]:
    """
    Extract metadata for a specific paper.
    
    Args:
        paper_id: Unique identifier for the paper
        meta_df: DataFrame containing metadata
        primary_category: Primary category classification
        
    Returns:
        Dictionary containing paper metadata
        
    Raises:
        ValueError: If paper_id is not found in dataframe
    """
    logger.debug(f"Extracting metadata for paper '{paper_id}' with primary_category '{primary_category}'")
    
    if paper_id not in meta_df["id"].values:
        logger.error(f"Paper ID '{paper_id}' not found in metadata dataframe")
        raise ValueError(f"Paper ID {paper_id} not found in metadata")
    
    try:
        row = meta_df[meta_df["id"] == paper_id]
        
        metadata = {
            "article_id": paper_id,
            "authors": row.authors.values[0],
            "categories": ", ".join(row.categories.values[0].split()),
            "published_year": row.update_date.values[0][:4],
            "primary_category": primary_category,
            "summary": row.abstract.values[0],
            "title": row.title.values[0]
        }
        
        logger.debug(f"Successfully extracted metadata for paper '{paper_id}': title='{metadata['title'][:50]}...'")
        return metadata
        
    except (IndexError, KeyError) as e:
        logger.error(f"Error extracting metadata for paper '{paper_id}': {e}")
        raise


def add_metadata_to_chunks(
    paper_id: str, 
    chunks: List[Dict[str, Any]], 
    meta_df, 
    primary_category: str
) -> List[Dict[str, Any]]:
    """
    Add metadata information to text chunks.
    
    Args:
        paper_id: Unique identifier for the paper
        chunks: List of text chunks to enhance
        meta_df: DataFrame containing metadata
        primary_category: Primary category classification
        
    Returns:
        List of chunks with added metadata
    """
    logger.info(f"Adding metadata to {len(chunks)} chunks for paper '{paper_id}'")
    
    try:
        metadata = get_metadata(paper_id, meta_df, primary_category)
        
        for i, chunk in enumerate(chunks):
            chunk.update(metadata)
            logger.debug(f"Added metadata to chunk {i+1}/{len(chunks)}")
        
        logger.info(f"Successfully added metadata to all {len(chunks)} chunks for paper '{paper_id}'")
        return chunks
        
    except (ValueError, IndexError, KeyError) as e:
        logger.error(f"Exception processing paper '{paper_id}': {e}")
        return []


def build_search_query(
    query: str, 
    metadata: Optional[Dict[str, Any]] = None, 
    limit: int = 10, 
    relevance_threshold: float = 0.5
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
    
    logger.info(f"Building search query with limit={limit}, threshold={relevance_threshold}")
    logger.debug(f"Search query: '{query[:100]}...' (truncated)")
    if metadata:
        logger.debug(f"Metadata filters: {metadata}")
    
    # Escape single quotes in query
    escaped_query = query.replace("'", "''")
    search_query = f"SELECT * from {config.kb.NAME} where content = '{escaped_query}'"
    
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
                "summary": metadata.get("summary", ""),
                "relevance": round(result["relevance"], 3)
            }
            
            seen_articles.add(article_id)
            cleaned_results.append(cleaned_result)
            logger.debug(f"Processed result {i+1}/{len(results_list)}: {article_id}")
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error processing result {i+1}/{len(results_list)}: {e}")
            skipped_count += 1
            continue

    logger.info(f"Transformation complete: {len(cleaned_results)} valid results, {skipped_count} skipped")
    return cleaned_results


def download_file_to_temp_dir(url: str, filename: str) -> Optional[str]:
    """
    Download file from URL to temporary directory.
    
    Args:
        url: URL to download from
        filename: Name for the downloaded file
        
    Returns:
        Path to downloaded file or None if download failed
        
    Raises:
        FileProcessingError: If download fails
    """
    if not url or not filename:
        logger.error("Cannot download file: URL and filename cannot be empty")
        raise ValueError("URL and filename cannot be empty")
    
    logger.info(f"Downloading file '{filename}' from URL: {url[:100]}...")
    
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, filename)
    
    logger.debug(f"Target file path: {file_path}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        logger.debug(f"Download successful, content length: {len(response.content)} bytes")

        with open(file_path, 'wb') as f:
            f.write(response.content)

        logger.info(f"File saved successfully to: {file_path}")
        return file_path

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download file '{filename}': {e}")
        raise FileProcessingError(f"Failed to download file: {e}")


def delete_file(file_path: str) -> None:
    """
    Delete file if it exists.
    
    Args:
        file_path: Path to file to delete
    """
    if not file_path:
        logger.debug("No file path provided for deletion")
        return
        
    if not os.path.exists(file_path):
        logger.debug(f"File does not exist, nothing to delete: {file_path}")
        return
        
    try:
        os.remove(file_path)
        logger.info(f"Successfully deleted file: {file_path}")
    except OSError as e:
        logger.error(f"Error deleting file '{file_path}': {e}")


def build_create_agent_query(name: str, knowledge_bases: List[str], tables: List[str]) -> str:
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
    
    kb_list = ', '.join([f"'{kb}'" for kb in knowledge_bases])
    table_list = ', '.join([f"'{table}'" for table in tables])
    
    query = f"""
    CREATE AGENT IF NOT EXISTS {name}
    USING
        model = '{config.agent.OPENAI_MODEL}',
        openai_api_key = '{config.kb.OPENAI_API_KEY}',
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


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text content from PDF file.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Extracted text content
        
    Raises:
        FileProcessingError: If PDF processing fails
        FileNotFoundError: If file doesn't exist
    """
    if not os.path.exists(file_path):
        logger.error(f"PDF file not found: {file_path}")
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    
    logger.info(f"Extracting text from PDF: {file_path}")
    
    try:
        doc = pymupdf.open(file_path)
        text_content = ""
        page_count = len(doc)
        
        logger.debug(f"PDF has {page_count} pages")
        
        for page_num, page in enumerate(doc, 1):
            page_text = clean_text(page.get_text())
            text_content += page_text
            logger.debug(f"Processed page {page_num}/{page_count}: {len(page_text)} characters")
            
        doc.close()
        
        logger.info(f"Successfully extracted {len(text_content)} characters from PDF")
        return text_content
        
    except Exception as e:
        logger.error(f"Failed to extract text from PDF '{file_path}': {e}")
        raise FileProcessingError(f"Failed to extract text from PDF: {e}")


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


def clean_text(text: str) -> str:
    """
    Clean text by removing short lines and normalizing whitespace.
    
    Args:
        text: Input text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        logger.debug("Empty text provided for cleaning")
        return ""
    
    original_length = len(text)
    
    # Remove lines shorter than 10 characters and strip whitespace
    cleaned_lines = [
        line.strip().encode('ascii', 'ignore').decode('ascii')
        for line in text.splitlines() 
        if len(line.strip()) >= 10
    ]
    
    cleaned_text = '\n'.join(cleaned_lines)
    
    logger.debug(f"Text cleaning: {original_length} -> {len(cleaned_text)} characters, "
                f"{len(text.splitlines())} -> {len(cleaned_lines)} lines")
    
    return cleaned_text

