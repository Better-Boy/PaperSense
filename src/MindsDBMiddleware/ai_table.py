"""AI table management module for MindsDB operations.

This module provides functionality for creating, listing, and interacting
with MindsDB AI tables through a high-level interface.
"""

import logging

from .manager import MindsDBManager
from .. import utils


logger = logging.getLogger(__name__)


class AITable:

    def __init__(self, mdb_server: MindsDBManager) -> None:
        if not mdb_server:
            raise ValueError("MindsDB server connection is required")

        if not mdb_server.is_connected():
            raise ValueError("MindsDB server must be connected")

        self.connection = mdb_server
        self.ai_tables = {
            "summary": """You are an expert research assistant specializing in identifying impactful research opportunities. Given abstract and key details of the following research paper, generate three distinct and innovative future research directions that meaningfully extend, challenge, or build upon the work described. Focus on addressing current limitations, unexplored gaps, or logical next steps. Avoid restating what the paper already covers, and instead propose novel avenues that could advance the field.
            Give the answer in markdown format.

Title: {{title}}
Authors: {{authors}}
Abstract: {{abstract}}
Research Field: {{field}}
            """,
            "ideas": """
            You are a creative and knowledgeable research assistant. Given the abstract and key details of the following arXiv research paper, generate a list of novel and promising research ideas inspired by its content. These ideas should explore new angles, applications, or extensions that go beyond the current scope. Focus on originality and feasibility within the field.
            Give the answer in markdown format.

Title: {{title}}
Authors: {{authors}}
Abstract: {{abstract}}
Research Field: {{field}}

Research Ideas:
                """
        }

    def create_ai_tables(self) -> None:
        try:
            for name, prompt in self.ai_tables.items():
                logger.info(
                    f"Creating ai table '{name}'"
                )
                create_ai_table_query = utils.build_create_ai_table_query(
                    name, prompt
                )
                self.connection.execute_query(create_ai_table_query)
                logger.info(f"Successfully created ai table '{name}'")

        except Exception as e:
            logger.error(f"Failed to create ai table '{name}': {e}")
            raise Exception(f"Failed to create table '{name}': {e}") from e

    def ask_table(self, name: str, params: dict) -> str:

        try:
            query = utils.build_ask_table_query(name, params)
            result = self.connection.execute_query(query)

            if not result or len(result) == 0:
                logger.warning(f"No response received from ai table '{name}'")
                return ""

            # Extract answer from the first result
            first_result = result[0]
            if not isinstance(first_result, dict) or "answer" not in first_result:
                logger.warning(f"Unexpected response format from table '{name}'")
                return ""

            answer = first_result["answer"]

            return str(answer) if answer is not None else ""

        except Exception as e:
            logger.error(f"Failed to query table '{name}': {e}")
            raise Exception(
                f"Failed to chat with table '{name}': {e}"
            ) from e
