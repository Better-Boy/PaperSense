"""
ArXiv paper processing pipeline for knowledge base integration.

This module provides functionality to download, process, and store ArXiv papers
in a knowledge base system.
"""

import logging
from typing import List, Dict, Any, Optional

import arxiv

from . import utils, config_loader as config, psql
from .mindsdb import mdb_server, knowledge_base

# Constants
MAX_CHUNKS_TO_PROCESS = 10
CHUNK_SIZE = 600
KB_NAME_SUFFIX = "_kb"

logger = logging.getLogger(__name__)


class ArxivProcessingError(Exception):
    """Custom exception for ArXiv processing errors."""
    pass


class ArxivProcessPipeline:
    """
    Pipeline for processing ArXiv papers and storing them in knowledge bases.
    
    This class handles downloading ArXiv papers, extracting text, chunking content,
    and storing the processed data in both a main knowledge base and a paper-specific
    knowledge base.
    """

    def __init__(self, arxiv_id: str, knowledge_base: knowledge_base.KnowledgeBase, 
                 postgres_client: psql.PostgresHandler) -> None:
        """
        Initialize the ArXiv processing pipeline.
        
        Args:
            arxiv_id: The ArXiv paper ID (e.g., "2301.12345")
            knowledge_base: Knowledge base instance for storing processed data
            postgres_client: PostgreSQL client for database operations
            
        Raises:
            ValueError: If arxiv_id is empty or invalid
        """
        if not arxiv_id or not isinstance(arxiv_id, str):
            raise ValueError("arxiv_id must be a non-empty string")
            
        self.arxiv_id = arxiv_id
        self._knowledge_base = knowledge_base
        self._postgres_client = postgres_client
        self._arxiv_client = arxiv.Client()

    def add_to_main_knowledge_base(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Add processed chunks to the main knowledge base.
        
        Args:
            chunks: List of text chunks with metadata to be stored
            
        Raises:
            ArxivProcessingError: If insertion fails
        """
        try:
            main_kb_name = config.kb.NAME
            self._knowledge_base.insert(main_kb_name, chunks, MAX_CHUNKS_TO_PROCESS)
            logger.info(f"Added {len(chunks)} chunks to main knowledge base")
        except Exception as e:
            raise ArxivProcessingError(f"Failed to add chunks to main KB: {e}") from e

    def get_paper_metadata(self) -> Dict[str, str]:
        """
        Retrieve metadata for the ArXiv paper.
        
        Returns:
            Dictionary containing paper metadata including authors, summary,
            categories, publication year, primary category, title, and article ID
            
        Raises:
            ArxivProcessingError: If paper metadata cannot be retrieved
        """
        try:
            search = arxiv.Search(id_list=[self.arxiv_id])
            paper = next(self._arxiv_client.results(search))
            
            metadata = {
                "authors": ", ".join(author.name for author in paper.authors),
                "summary": paper.summary or "",
                "categories": ", ".join(paper.categories) if paper.categories else "",
                "published_year": str(paper.published.year) if paper.published else "",
                "primary_category": paper.primary_category or "",
                "title": paper.title or "",
                "article_id": self.arxiv_id
            }
            
            logger.info(f"Retrieved metadata for paper: {metadata['title']}")
            return metadata
            
        except StopIteration:
            raise ArxivProcessingError(f"Paper with ID {self.arxiv_id} not found")
        except Exception as e:
            raise ArxivProcessingError(f"Failed to retrieve metadata: {e}") from e

    def create_paper_knowledge_base(self) -> None:
        """
        Create a dedicated knowledge base for this paper.
        
        Raises:
            ArxivProcessingError: If knowledge base creation fails
        """
        try:
            kb_name = utils.generate_kb_name(self.arxiv_id)
            self._knowledge_base.create(kb_name)
            logger.info(f"Created knowledge base: {kb_name}")
        except Exception as e:
            raise ArxivProcessingError(f"Failed to create paper KB: {e}")

    def _download_and_extract_text(self) -> str:
        """
        Download the paper PDF and extract text content.
        
        Returns:
            Extracted text content from the PDF
            
        Raises:
            ArxivProcessingError: If download or text extraction fails
        """
        pdf_url = f"https://arxiv.org/pdf/{self.arxiv_id}"
        pdf_filename = f"{self.arxiv_id}.pdf"
        
        try:
            file_path = utils.download_file_to_temp_dir(pdf_url, pdf_filename)
            text_content = utils.extract_text_from_pdf(file_path)
            utils.delete_file(file_path)
            
            logger.info(f"Successfully extracted text from {pdf_filename}")
            return text_content
            
        except Exception as e:
            raise ArxivProcessingError(f"Failed to download/extract PDF: {e}") from e

    def _prepare_full_text(self, text_content: str, metadata: Dict[str, str]) -> str:
        """
        Prepare the full text by combining metadata and content.
        
        Args:
            text_content: Extracted text from the PDF
            metadata: Paper metadata dictionary
            
        Returns:
            Combined text with title, summary, and content
        """
        title = metadata.get("title", "")
        summary = metadata.get("summary", "")
        
        full_text = "\n".join([title, summary, text_content])
        # Remove null bytes that can cause issues
        full_text = full_text.replace("\x00", "")
        
        return full_text

    def _process_and_chunk_text(self, full_text: str, 
                               metadata: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Process and chunk the text content.
        
        Args:
            full_text: Complete text content to be chunked
            metadata: Paper metadata to be added to each chunk
            
        Returns:
            List of text chunks with metadata
        """
        chunks = utils.chunk_text(full_text, CHUNK_SIZE)
        
        # Add metadata to each chunk
        for chunk in chunks:
            chunk.update(metadata)
        
        logger.info(f"Created {len(chunks)} chunks")
        return chunks

    def _store_in_postgres(self, full_text: str, metadata: Dict[str, str]) -> None:
        """
        Store the complete text and metadata in PostgreSQL.
        
        Args:
            full_text: Complete text content
            metadata: Paper metadata
            
        Raises:
            ArxivProcessingError: If database insertion fails
        """
        try:
            row_data = {"text": full_text, **metadata}
            self._postgres_client.insert_article(row_data)
            logger.info("Successfully stored paper data in PostgreSQL")
        except Exception as e:
            raise ArxivProcessingError(f"Failed to store in PostgreSQL: {e}") from e

    def _store_in_paper_kb(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Store chunks in the paper-specific knowledge base.
        
        Args:
            chunks: List of text chunks with metadata
            
        Raises:
            ArxivProcessingError: If knowledge base insertion fails
        """
        try:
            kb_name = utils.generate_kb_name(self.arxiv_id)
            self._knowledge_base.insert(kb_name, chunks, MAX_CHUNKS_TO_PROCESS)
            logger.info(f"Stored {len(chunks)} chunks in paper KB: {kb_name}")
        except Exception as e:
            raise ArxivProcessingError(f"Failed to store in paper KB: {e}") from e

    def process(self) -> None:
        """
        Execute the complete ArXiv paper processing pipeline.
        
        This method orchestrates the entire process:
        1. Downloads and extracts text from the PDF
        2. Retrieves paper metadata
        3. Processes and chunks the text
        4. Stores data in the main knowledge base
        5. Stores data in PostgreSQL
        6. Creates and populates a paper-specific knowledge base
        
        Raises:
            ArxivProcessingError: If any step in the pipeline fails
        """
        try:
            logger.info(f"Starting processing pipeline for ArXiv ID: {self.arxiv_id}")
            
            # Step 1: Download and extract text
            text_content = self._download_and_extract_text()
            
            # Step 2: Get metadata
            metadata = self.get_paper_metadata()
            
            # Step 3: Prepare full text
            full_text = self._prepare_full_text(text_content, metadata)
            
            # Step 4: Process and chunk text
            chunks = self._process_and_chunk_text(full_text, metadata)
            
            # Step 5: Store in main knowledge base
            self.add_to_main_knowledge_base(chunks)
            
            # Step 6: Store in PostgreSQL
            self._store_in_postgres(full_text, metadata)
            
            # Step 7: Create and populate paper-specific knowledge base
            self.create_paper_knowledge_base()
            self._store_in_paper_kb(chunks)
            
            logger.info(f"Successfully completed processing for ArXiv ID: {self.arxiv_id}")
            
        except ArxivProcessingError:
            logger.error(f"Processing failed for ArXiv ID: {self.arxiv_id}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing ArXiv ID {self.arxiv_id}: {e}")
            raise ArxivProcessingError(f"Unexpected error in processing pipeline: {e}") from e

    # Deprecated method - kept for backward compatibility
    def start(self) -> None:
        """
        Legacy method for starting the pipeline.
        
        Deprecated: Use process() instead.
        """
        import warnings
        warnings.warn(
            "start() is deprecated, use process() instead",
            DeprecationWarning,
            stacklevel=2
        )
        self.process()