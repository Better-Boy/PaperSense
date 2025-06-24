"""MindsDB server connection and query execution module."""

import logging
from typing import List, Dict, Any, Optional, Union

import mindsdb_sdk
import requests

from .. import config_loader as config


logger = logging.getLogger(__name__)


class MDBConnectionError(Exception):
    """Raised when MindsDB connection fails."""
    pass


class MDBQueryError(Exception):
    """Raised when MindsDB query execution fails."""
    pass


class MDBServer:
    """MindsDB server client for executing queries and managing agents.
    
    This class provides a high-level interface for connecting to MindsDB,
    executing queries, and retrieving agent information.
    
    Attributes:
        client: The MindsDB SDK client instance.
    """
    
    def __init__(self) -> None:
        """Initialize the MDBServer with a connection to MindsDB."""
        self.client = self._connect()
        
    def _connect(self) -> mindsdb_sdk.server.Server:
        """Establish connection to MindsDB server.
        
        Returns:
            Connected MindsDB client instance.
            
        Raises:
            MDBConnectionError: If connection configuration is missing or invalid.
        """
        host = config.mdb_infra.MINDSDB_HOST
        port = config.mdb_infra.MINDSDB_PORT

        if not host or not port:
            raise MDBConnectionError(
                "MindsDB host and port must be configured in config.yaml"
            )
            
        connection_url = f"http://{host}:{port}"
        logger.info(f"Connecting to MindsDB at {connection_url}")
        
        try:
            return mindsdb_sdk.connect(connection_url)
        except Exception as e:
            raise MDBConnectionError(f"Failed to connect to MindsDB: {e}") from e
    
    def disconnect(self) -> None:
        """Disconnect from MindsDB server."""
        if self.client:
            logger.info("Disconnecting from MindsDB")
            self.client = None

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SQL query on MindsDB.
        
        Args:
            query: SQL query string to execute.
            
        Returns:
            List of dictionaries containing query results.
            
        Raises:
            MDBQueryError: If query execution fails.
            ValueError: If query parameter is empty or invalid.
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
            
        if not self.client:
            raise MDBQueryError("No active connection to MindsDB")
            
        try:
            logger.debug(f"Executing query: {query}")
            result = self.client.query(query)
            data = result.fetch()
            
            if hasattr(data, 'to_dict'):
                return data.to_dict('records')
            elif isinstance(data, list):
                return data
            else:
                return []
                
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise MDBQueryError(f"Failed to execute query: {e}") from e
    
    def get_agents(self) -> List[str]:
        """Retrieve list of available agent names from MindsDB.
        
        Returns:
            List of agent names. Returns empty list if retrieval fails.
        """
        if not self.client:
            logger.warning("No active connection to MindsDB")
            return []
            
        try:
            agents_url = f"{self.client.api.url}/api/projects/mindsdb/agents"
            logger.debug(f"Fetching agents from: {agents_url}")
            
            response = requests.get(agents_url, timeout=10)
            response.raise_for_status()
            
            agents_data = response.json()
            if not isinstance(agents_data, list):
                logger.warning("Unexpected agents data format")
                return []
                
            return [agent["name"] for agent in agents_data if "name" in agent]
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch agents via HTTP: {e}")
            return []
        except (KeyError, TypeError, ValueError) as e:
            logger.error(f"Failed to parse agents response: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching agents: {e}")
            return []

    def is_connected(self) -> bool:
        """Check if client is connected to MindsDB.
        
        Returns:
            True if connected, False otherwise.
        """
        return self.client is not None
        
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.disconnect()