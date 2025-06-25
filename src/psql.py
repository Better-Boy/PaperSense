"""PostgreSQL database handler with connection pooling."""

import contextlib
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import psycopg2
import psycopg2.pool
from psycopg2 import Error as PostgresError
from psycopg2.extras import RealDictCursor

from . import config_loader as config

logger = logging.getLogger(__name__)


class PostgresConnectionError(Exception):
    """Custom exception for PostgreSQL connection errors."""
    pass


class PostgresQueryError(Exception):
    """Custom exception for PostgreSQL query errors."""
    pass


class PostgresHandler:
    """
    PostgreSQL database handler with connection pooling.
    
    Provides methods for database operations with proper connection management,
    error handling, and resource cleanup.
    """
    
    DEFAULT_MIN_CONNECTIONS = 1
    DEFAULT_MAX_CONNECTIONS = 10
    
    def __init__(
        self, 
        min_connections: int = DEFAULT_MIN_CONNECTIONS,
        max_connections: int = DEFAULT_MAX_CONNECTIONS
    ):
        """
        Initialize PostgreSQL handler with connection pool.
        
        Args:
            min_connections: Minimum number of connections in pool.
            max_connections: Maximum number of connections in pool.
            
        Raises:
            PostgresConnectionError: If connection pool creation fails.
        """
        self.min_connections = min_connections
        self.max_connections = max_connections
        self._pool: Optional[psycopg2.pool.SimpleConnectionPool] = None
        self._initialize_pool()
    
    def _initialize_pool(self) -> None:
        """Initialize the connection pool."""
        try:
            self._pool = self._create_connection_pool()
            logger.info(
                f"PostgreSQL connection pool initialized with "
                f"{self.min_connections}-{self.max_connections} connections"
            )
        except PostgresError as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise PostgresConnectionError(f"Failed to initialize connection pool: {e}")
    
    def _create_connection_pool(self) -> psycopg2.pool.SimpleConnectionPool:
        """
        Create PostgreSQL connection pool.
        
        Returns:
            Configured connection pool.
            
        Raises:
            PostgresError: If pool creation fails.
        """
        connection_params = self._build_connection_params()
        
        return psycopg2.pool.SimpleConnectionPool(
            minconn=self.min_connections,
            maxconn=self.max_connections,
            **connection_params
        )
    
    def _build_connection_params(self) -> Dict[str, Any]:
        """
        Build connection parameters from configuration.
        
        Returns:
            Dictionary of connection parameters.
        """
        return {
            "host": config.psql.host,
            "port": config.psql.port,
            "dbname": config.psql.database,
            "user": config.psql.user,
            "password": config.psql.password,
            "connect_timeout": 10
        }
    
    @property
    def pool(self) -> psycopg2.pool.SimpleConnectionPool:
        """Get the connection pool, initializing if necessary."""
        if self._pool is None:
            self._initialize_pool()
        return self._pool
    
    @contextlib.contextmanager
    def get_cursor(self, dict_cursor: bool = False):
        """
        Context manager for database cursor with automatic cleanup.
        
        Args:
            dict_cursor: If True, return RealDictCursor for dict-like row access.
            
        Yields:
            Database cursor.
            
        Raises:
            PostgresConnectionError: If unable to get connection from pool.
        """
        if self._pool is None:
            raise PostgresConnectionError("Connection pool not initialized")
            
        conn = None
        try:
            conn = self.pool.getconn()
            if conn is None:
                raise PostgresConnectionError("Unable to get connection from pool")
            
            cursor_factory = RealDictCursor if dict_cursor else None
            
            with conn:
                with conn.cursor(cursor_factory=cursor_factory) as cur:
                    yield cur
                    
        except PostgresError as e:
            if conn:
                conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise PostgresQueryError(f"Database operation failed: {e}")
        finally:
            if conn:
                self.pool.putconn(conn)
    
    def get_connection(self):
        """
        Get a connection from the pool.
        
        Note: Remember to return connection using return_connection().
        
        Returns:
            Database connection.
            
        Raises:
            PostgresConnectionError: If unable to get connection.
        """
        if self._pool is None:
            raise PostgresConnectionError("Connection pool not initialized")
            
        conn = self.pool.getconn()
        if conn is None:
            raise PostgresConnectionError("Unable to get connection from pool")
        return conn
    
    def return_connection(self, conn) -> None:
        """
        Return a connection to the pool.
        
        Args:
            conn: Database connection to return.
        """
        if self._pool and conn:
            self.pool.putconn(conn)
    
    def insert_article(self, article_data: Dict[str, Any]) -> None:
        """
        Insert an article into the database.
        
        Args:
            article_data: Dictionary containing article data.
            
        Raises:
            PostgresQueryError: If insert operation fails.
            ValueError: If required fields are missing.
        """
        required_fields = {
            'authors', 'categories', 'published_year', 'primary_category',
            'article_id', 'text', 'summary', 'title'
        }
        
        missing_fields = required_fields - set(article_data.keys())
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        # Get table name from config, with fallback
        table_name = getattr(config.psql, 'table_name', 'articles')
        
        insert_query = f"""
            INSERT INTO {table_name} (
                authors, categories, published_year, primary_category,
                article_id, text, summary, title
            ) VALUES (
                %(authors)s, %(categories)s, %(published_year)s, %(primary_category)s,
                %(article_id)s, %(text)s, %(summary)s, %(title)s
            )
        """
        
        try:
            with self.get_cursor() as cur:
                cur.execute(insert_query, article_data)
            logger.debug(f"Successfully inserted article: {article_data.get('article_id')}")
        except PostgresError as e:
            logger.error(f"Failed to insert article {article_data.get('article_id')}: {e}")
            raise PostgresQueryError(f"Failed to insert article: {e}")
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[Union[Dict[str, Any], Tuple]] = None,
        fetch_results: bool = False
    ) -> Optional[List[Tuple]]:
        """
        Execute a SQL query with optional parameters.
        
        Args:
            query: SQL query string.
            params: Query parameters (dict or tuple).
            fetch_results: Whether to fetch and return results.
            
        Returns:
            Query results if fetch_results is True, None otherwise.
            
        Raises:
            PostgresQueryError: If query execution fails.
        """
        try:
            with self.get_cursor(True) as cur:
                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)
                
                if fetch_results:
                    results = cur.fetchall()
                    logger.info(f"Query returned {len(results)} rows")
                    return results
                else:
                    logger.debug("Query executed successfully (no results returned)")
                    return None
                    
        except PostgresError as e:
            logger.error(f"Query execution failed: {e}")
            raise PostgresQueryError(f"Query execution failed: {e}")
    
    def test_connection(self) -> bool:
        """
        Test database connection.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            with self.get_cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                return result[0] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def close(self) -> None:
        """Close all connections in the pool."""
        if self._pool:
            self._pool.closeall()
            self._pool = None
            logger.info("PostgreSQL connection pool closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.close()
