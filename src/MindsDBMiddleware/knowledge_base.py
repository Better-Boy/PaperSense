"""Knowledge base management module for MDB operations."""

import logging
from typing import Any, Dict, List, Optional

from .. import config_loader as config, utils
from .manager import MindsDBManager


logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Manages knowledge base operations including creation, insertion, and search."""

    def __init__(self, mdb_server: MindsDBManager) -> None:
        """Initialize KnowledgeBase with MDB server connection.

        Args:
            mdb_server: MDBServer instance for database operations
        """
        self.conn = mdb_server

    def create(self, name: str) -> None:
        """Create a new knowledge base.

        Args:
            name: Name of the knowledge base to create

        Raises:
            Exception: If knowledge base creation fails
        """
        create_kb_query = utils.build_create_kb_query(name)
        self.conn.execute_query(create_kb_query)

    def create_index(self, name: str) -> None:
        if config.kb_storage.enable_pg_vector:
            logger.info(f"Creating index for knowledge base - {name}")
            create_index_kb_query = f"CREATE INDEX ON KNOWLEDGE_BASE {name};"
            self.conn.execute_query(create_index_kb_query)
            logger.info(f"Successfully created index for knowledge base - {name}")

    def list_knowledge_bases(self) -> List[str]:
        """List all available knowledge bases.

        Returns:
            List of knowledge base names, empty list if none found or on error
        """
        try:
            knowledge_bases = self.conn.client.knowledge_bases.list()
            return [kb.name for kb in knowledge_bases] if knowledge_bases else []
        except Exception as e:
            logger.error("Failed to list knowledge bases: %s", e)
            return []

    def insert_batch(self, name: str, batch_data: List[Dict[str, Any]]) -> bool:
        """Insert a batch of data into the knowledge base.

        Args:
            name: Knowledge base name
            batch_data: List of dictionaries containing data to insert

        Returns:
            True if insertion successful, False otherwise
        """
        columns = set(config.kb.content_columns + config.kb.metadata_columns)
        values_clause = utils.build_values_clause(batch_data, columns)
        query = utils.build_insert_query(name, columns, values_clause)
        try:
            self.conn.execute_query(query)
            return True
        except Exception as e:
            logger.error("Failed to insert batch: %s", e)
            return False

    def insert(
        self, name: str, data: List[Dict[str, Any]], batch_size: Optional[int] = None
    ) -> bool:
        """Insert data into knowledge base in batches.

        Args:
            name: Knowledge base name
            data: List of dictionaries containing data to insert
            batch_size: Size of each batch, defaults to 25 (max)

        Returns:
            True if all batches inserted successfully, False otherwise
        """
        if not data:
            return True

        # Set default batch size if not provided, ensure it doesn't exceed max
        if batch_size is None:
            batch_size = 25

        total_batches = (len(data) + batch_size - 1) // batch_size
        successful_batches = 0

        for i in range(0, len(data), batch_size):
            batch = data[i : i + batch_size]
            if self.insert_batch(name, batch):
                successful_batches += 1
            else:
                logger.error(
                    "Failed to insert batch %d/%d", i // batch_size + 1, total_batches
                )

        success_rate = successful_batches / total_batches
        logger.info(
            "Inserted %d/%d batches successfully (%.1f%%)",
            successful_batches,
            total_batches,
            success_rate * 100,
        )

        return successful_batches == total_batches

    def drop(self, name: str) -> bool:
        """Drop a knowledge base.

        Args:
            name: Knowledge base name to drop

        Returns:
            True if drop successful, False otherwise
        """
        try:
            self.conn.execute_query(f"DROP KNOWLEDGE BASE {name}")
            logger.info("Successfully dropped knowledge base: %s", name)
            return True
        except Exception as e:
            logger.error("Failed to drop knowledge base %s: %s", name, e)
            return False

    def search(
        self,
        name: str,
        query: str,
        metadata: Dict[str, Any],
        limit: int = 10,
        relevance_threshold: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """Search the knowledge base.

        Args:
            query: Search query string
            metadata: Metadata filters for search
            limit: Maximum number of results to return
            relevance_threshold: Minimum relevance score threshold

        Returns:
            List of search results, empty list if no results or on error
        """
        try:
            search_query = utils.build_search_query(
                name, query, metadata, limit, relevance_threshold
            )
            results = self.conn.execute_query(search_query)

            if results is None:
                return []

            return utils.transform_results(results)
        except Exception as e:
            logger.error("Search failed for query '%s': %s", query, e)
            return []
