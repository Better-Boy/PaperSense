"""Agent management module for MindsDB operations.

This module provides functionality for creating, listing, and interacting
with MindsDB agents through a high-level interface.
"""

import logging
from typing import List, Optional

from .mdb_server import MDBServer
from .. import utils


logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Base exception for agent-related operations."""
    pass


class AgentCreationError(AgentError):
    """Raised when agent creation fails."""
    pass


class AgentChatError(AgentError):
    """Raised when agent chat interaction fails."""
    pass


class Agent:
    """MindsDB agent management interface.
    
    This class provides methods for creating agents, listing available agents,
    and chatting with existing agents through the MindsDB server connection.
    
    Attributes:
        connection: The MindsDB server connection instance.
    """
    
    def __init__(self, mdb_server: MDBServer) -> None:
        """Initialize the Agent with a MindsDB server connection.
        
        Args:
            mdb_server: An active MindsDB server connection instance.
            
        Raises:
            ValueError: If mdb_server is None or invalid.
        """
        if not mdb_server:
            raise ValueError("MindsDB server connection is required")
            
        if not mdb_server.is_connected():
            raise ValueError("MindsDB server must be connected")
            
        self.connection = mdb_server

    def create(
        self, 
        name: str, 
        knowledge_bases: Optional[List[str]] = None, 
        tables: Optional[List[str]] = None
    ) -> None:
        """Create a new MindsDB agent.
        
        Args:
            name: Name of the agent to create.
            knowledge_bases: List of knowledge base names to associate with the agent.
            tables: List of table names to associate with the agent.
            
        Raises:
            ValueError: If agent name is empty or invalid.
            AgentCreationError: If agent creation fails.
        """
        if not name or not name.strip():
            raise ValueError("Agent name cannot be empty")
            
        # Default to empty lists if None provided
        knowledge_bases = knowledge_bases or []
        tables = tables or []
        
        try:
            logger.info(f"Creating agent '{name}' with {len(knowledge_bases)} KB(s) and {len(tables)} table(s)")
            create_agent_query = utils.build_create_agent_query(name, knowledge_bases, tables)
            self.connection.execute_query(create_agent_query)
            logger.info(f"Successfully created agent '{name}'")
            
        except Exception as e:
            logger.error(f"Failed to create agent '{name}': {e}")
            raise AgentCreationError(f"Failed to create agent '{name}': {e}") from e

    def list_agents(self) -> List[str]:
        """List all available MindsDB agents.
        
        Returns:
            List of agent names. Returns empty list if no agents found.
            
        Note:
            This method is renamed from 'ls' for better readability and 
            Python naming conventions.
        """
        try:
            logger.debug("Retrieving list of available agents")
            agents = self.connection.get_agents()
            logger.debug(f"Found {len(agents)} agent(s)")
            return agents
            
        except Exception as e:
            logger.error(f"Failed to retrieve agents list: {e}")
            return []
    
    # Keep original method name for backward compatibility
    def ls(self) -> List[str]:
        """List all available MindsDB agents.
        
        Returns:
            List of agent names.
            
        Deprecated:
            Use list_agents() instead for better readability.
        """
        return self.list_agents()

    def chat(self, agent_name: str, query: str) -> str:
        """Send a chat message to a MindsDB agent.
        
        Args:
            agent_name: Name of the agent to chat with.
            query: The message/query to send to the agent.
            
        Returns:
            The agent's response as a string. Returns empty string if no response.
            
        Raises:
            ValueError: If agent_name or query is empty.
            AgentChatError: If chat interaction fails.
        """
        if not agent_name or not agent_name.strip():
            raise ValueError("Agent name cannot be empty")
            
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
            
        try:
            logger.debug(f"Sending chat message to agent '{agent_name}'")
            chat_query = utils.build_chat_agent_query(agent_name, query)
            result = self.connection.execute_query(chat_query)
            
            if not result or len(result) == 0:
                logger.warning(f"No response received from agent '{agent_name}'")
                return ""
                
            # Extract answer from the first result
            first_result = result[0]
            if not isinstance(first_result, dict) or "answer" not in first_result:
                logger.warning(f"Unexpected response format from agent '{agent_name}'")
                return ""
                
            answer = first_result["answer"]
            logger.debug(f"Received response from agent '{agent_name}': {len(str(answer))} characters")
            
            return str(answer) if answer is not None else ""
            
        except Exception as e:
            logger.error(f"Failed to chat with agent '{agent_name}': {e}")
            raise AgentChatError(f"Failed to chat with agent '{agent_name}': {e}") from e

    def agent_exists(self, agent_name: str) -> bool:
        """Check if an agent exists.
        
        Args:
            agent_name: Name of the agent to check.
            
        Returns:
            True if agent exists, False otherwise.
        """
        if not agent_name:
            return False
            
        try:
            available_agents = self.list_agents()
            return agent_name in available_agents
        except Exception as e:
            logger.error(f"Failed to check if agent '{agent_name}' exists: {e}")
            return False
