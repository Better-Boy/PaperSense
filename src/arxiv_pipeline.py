"""
ArXiv paper processing pipeline for knowledge base integration.

This module provides functionality to download, process, and store ArXiv papers
in a knowledge base system.
"""

from io import BytesIO
import logging
import re
import string
from typing import List, Dict, Any

import PyPDF2
import arxiv
import requests

from . import utils, config_loader as config, psql
from src.MindsDBMiddleware import knowledge_base

# Constants
MAX_CHUNKS_TO_PROCESS = 10
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

    def __init__(
        self,
        arxiv_id: str,
        knowledge_base: knowledge_base.KnowledgeBase,
        postgres_client: psql.PostgresHandler,
    ) -> None:
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
        self.kb_name = utils.generate_kb_name(arxiv_id)

        # Patterns for different types of equations and LaTeX commands
        self.equation_patterns = [
            # Display equations ($$...$$, \[...\], \begin{equation}...\end{equation})
            r'\$\$.*?\$\$',
            r'\\\[.*?\\\]',
            r'\\begin\{equation\*?\}.*?\\end\{equation\*?\}',
            r'\\begin\{align\*?\}.*?\\end\{align\*?\}',
            r'\\begin\{eqnarray\*?\}.*?\\end\{eqnarray\*?\}',
            r'\\begin\{gather\*?\}.*?\\end\{gather\*?\}',
            r'\\begin\{multline\*?\}.*?\\end\{multline\*?\}',
            r'\\begin\{split\}.*?\\end\{split\}',
            
            # Inline equations ($...$)
            r'\$[^$\n]+\$',
            
            # LaTeX math environments
            r'\\begin\{math\}.*?\\end\{math\}',
            r'\\begin\{displaymath\}.*?\\end\{displaymath\}',
            
            # Numbered equations
            r'\\begin\{equation\}.*?\\end\{equation\}',
            r'\\begin\{align\}.*?\\end\{align\}',
        ]
        
        # LaTeX commands to remove
        self.latex_commands = [
            r'\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})*',  # General LaTeX commands
            r'\\\\',  # Line breaks
            r'\\&',   # Alignment characters
            r'\{|\}', # Braces
            r'\\textbf\{([^}]+)\}',  # Bold text
            r'\\textit\{([^}]+)\}',  # Italic text
            r'\\emph\{([^}]+)\}',    # Emphasized text
            r'\\cite\{[^}]+\}',      # Citations
            r'\\ref\{[^}]+\}',       # References
            r'\\label\{[^}]+\}',     # Labels
        ]

    def add_to_main_knowledge_base(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Add processed chunks to the main knowledge base.

        Args:
            chunks: List of text chunks with metadata to be stored

        Raises:
            ArxivProcessingError: If insertion fails
        """
        try:
            main_kb_name = config.kb.name
            self._knowledge_base.insert(main_kb_name, chunks, MAX_CHUNKS_TO_PROCESS)
            logger.info(f"Added {len(chunks)} chunks to main knowledge base")
        except Exception as e:
            raise ArxivProcessingError(f"Failed to add chunks to main KB: {e}") from e

    def get_paper_metadata(self) -> Dict[str, str]:
        """
        Retrieve metadata for the ArXiv paper.

        Returns:
            Dictionary containing paper metadata including authors, abstract,
            categories, publication year, primary category, title, and article ID

        Raises:
            ArxivProcessingError: If paper metadata cannot be retrieved
        """
        try:
            search = arxiv.Search(id_list=[self.arxiv_id])
            paper = next(self._arxiv_client.results(search))

            metadata = {
                "authors": ", ".join(author.name for author in paper.authors),
                "abstract": paper.summary or "",
                "categories": ", ".join(paper.categories) if paper.categories else "",
                "published_year": str(paper.published.year) if paper.published else "",
                "primary_category": paper.primary_category or "",
                "title": paper.title or "",
                "article_id": self.arxiv_id,
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
            self._knowledge_base.create(self.kb_name)
            logger.info(f"Created knowledge base: {self.kb_name}")
        except Exception as e:
            raise ArxivProcessingError(f"Failed to create paper KB: {e}")
        
    def download_arxiv_pdf(self) -> BytesIO:
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
        url = f"https://arxiv.org/pdf/{self.arxiv_id}"

        if not url:
            logger.error("Cannot download file: URL cannot be empty")
            raise ValueError("URL cannot be empty")

        logger.info(f"Downloading file from URL: {url[:100]}...")

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            logger.info(
                f"Download successful, content length: {len(response.content)} bytes"
            )

            return BytesIO(response.content)

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {url}: {e}")
            raise e
        
    def extract_text_from_pdf(self, pdf_file: BytesIO) -> str:
        """Extract raw text from PDF file."""
        text = ""
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {e}")
        
        return text
    
    def remove_equations(self, text):
        """Remove mathematical equations from text."""
        # Remove equations (use DOTALL flag to match across newlines)
        for pattern in self.equation_patterns:
            text = re.sub(pattern, ' ', text, flags=re.DOTALL)
        
        return text
    
    def remove_latex_commands(self, text):
        """Remove LaTeX formatting commands."""
        for pattern in self.latex_commands:
            # For text formatting commands, keep the content
            if r'\{([^}]+)\}' in pattern:
                text = re.sub(pattern, r'\1', text)
            else:
                text = re.sub(pattern, ' ', text)
        
        return text
    

    def clean_text(self, text):
        """Clean up the text formatting."""
        # Remove extra whitespace and newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Multiple newlines
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces
        text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)  # Leading/trailing whitespace
        
        # Remove common LaTeX artifacts
        text = re.sub(r'\\[a-zA-Z]+\*?', '', text)  # Remaining LaTeX commands
        text = re.sub(r'[{}]', '', text)  # Remaining braces
        text = re.sub(r'\\\\', '', text)  # Remaining line breaks
        
        # Clean up punctuation spacing
        text = re.sub(r'\s+([.,;:])', r'\1', text)  # Space before punctuation
        text = re.sub(r'([.,;:])\s*\n', r'\1\n', text)  # Punctuation at line end
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)  # Remove control chars
        translator = str.maketrans("", "", string.punctuation)
        text = text.strip().translate(translator)

        return text.strip()
    
    def process_text(self, text):
        """Main processing pipeline."""
        print("Removing equations...")
        text = self.remove_equations(text)
        
        print("Removing LaTeX commands...")
        text = self.remove_latex_commands(text)
        
        print("Cleaning text...")
        text = self.clean_text(text)
        
        # Store processed text for parameterized queries
        self.processed_text = text
        
        return text

    def extract_from_arxiv(self) -> str:
        """
        Download the paper PDF and extract text content.

        Returns:
            Extracted text content from the PDF

        Raises:
            ArxivProcessingError: If download or text extraction fails
        """
        

        try:
            print(f"Downloading arXiv paper: {self.arxiv_id}")
            pdf_file = self.download_arxiv_pdf()
            
            print("Extracting text from PDF...")
            raw_text = self.extract_text_from_pdf(pdf_file)
            
            return self.process_text(raw_text)
        except Exception as e:
            raise ArxivProcessingError(f"Failed to download/extract PDF: {e}") from e

    def _prepare_full_text(self, text_content: str, metadata: Dict[str, str]) -> str:
        """
        Prepare the full text by combining metadata and content.

        Args:
            text_content: Extracted text from the PDF
            metadata: Paper metadata dictionary

        Returns:
            Combined text with title, abstract, and content
        """
        title = metadata.get("title", "")
        abstract = metadata.get("abstract", "")

        full_text = "\n".join([title, abstract, text_content])

        return full_text

    def _process_and_chunk_text(
        self, full_text: str, metadata: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Process and chunk the text content.

        Args:
            full_text: Complete text content to be chunked
            metadata: Paper metadata to be added to each chunk

        Returns:
            List of text chunks with metadata
        """
        chunks = utils.chunk_text(full_text, 1500, 300)

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
            self._knowledge_base.insert(self.kb_name, chunks, MAX_CHUNKS_TO_PROCESS)
            logger.info(f"Stored {len(chunks)} chunks in paper KB: {self.kb_name}")
        except Exception as e:
            raise ArxivProcessingError(f"Failed to store in paper KB: {e}") from e

    def create_index_on_kb(self) -> None:
        if config.kb_storage.enable_pg_vector:
            self._knowledge_base.create_index(self.kb_name)

    def process(self, create_paper_kb: bool, add_to_main_kb: bool) -> None:
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
            existing_paper_data = self._postgres_client.get_paper_from_psql(self.arxiv_id)

            if existing_paper_data:
                logger.info(f"Using existing data for {self.arxiv_id}")
                full_text = existing_paper_data["text"]

                del existing_paper_data["text"]

                metadata = dict(existing_paper_data)
            else:
                logger.info(
                    f"Starting processing pipeline for ArXiv ID: {self.arxiv_id}"
                )

                # Step 1: Download and extract text
                text_content = self.extract_from_arxiv()

                # Step 2: Get metadata
                metadata = self.get_paper_metadata()

                metadata["abstract"] = self.clean_text(metadata["abstract"])

                # Step 3: Prepare full text
                full_text = self._prepare_full_text(text_content, metadata)

                # Step 6: Store in PostgreSQL
                self._store_in_postgres(full_text, metadata)

            if create_paper_kb or add_to_main_kb:
                # Step 4: Process and chunk text
                chunks = self._process_and_chunk_text(full_text, metadata)

            if not existing_paper_data and add_to_main_kb:
                # Step 5: Store in main knowledge base
                self.add_to_main_knowledge_base(chunks)

            # Step 7: Create and populate paper-specific knowledge base
            if create_paper_kb:
                self.create_paper_knowledge_base()
                self._store_in_paper_kb(chunks)
                self.create_index_on_kb()

            logger.info(
                f"Successfully completed processing for ArXiv ID: {self.arxiv_id}"
            )

        except ArxivProcessingError:
            logger.error(f"Processing failed for ArXiv ID: {self.arxiv_id}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing ArXiv ID {self.arxiv_id}: {e}")
            raise ArxivProcessingError(
                f"Unexpected error in processing pipeline: {e}"
            ) from e
