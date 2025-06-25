"""WarmUp class for initializing database and knowledge base components."""

import json
import logging
import random
from pathlib import Path
from typing import List, Dict, Any

from src.mindsdb import mdb_server, knowledge_base
from src import psql, utils, config_loader as config

logger = logging.getLogger(__name__)

class WarmUp:
    """Handles initialization of PostgreSQL tables, knowledge base, and sample data."""

    def __init__(self, mdb: mdb_server.MDBServer, kb: knowledge_base.KnowledgeBase, psql: psql.PostgresHandler) -> None:
        """Initialize WarmUp with required service instances.
        
        Args:
            mdb: MindsDB server instance
            kb: Knowledge base instance  
            psql: PostgreSQL connection instance
        """
        self._mdb = mdb
        self._kb = kb
        self._psql = psql
        logger.info("WarmUp instance initialized with MDB, KB, and PostgreSQL handlers")

    def create_psql_table(self) -> None:
        """Create PostgreSQL table if it doesn't exist."""
        try:
            logger.info(f"Creating PostgreSQL table '{config.psql.table_name}' if it doesn't exist")
            
            columns = set(config.kb.content_columns + config.kb.metadata_columns)
            column_definitions = ", ".join([f"{col} VARCHAR" for col in columns])
            
            create_table_sql = f"""
                CREATE TABLE IF NOT EXISTS {config.psql.table_name} (
                    id SERIAL PRIMARY KEY,
                    {column_definitions}
                );
            """
            
            logger.debug(f"Executing SQL: {create_table_sql}")
            self._psql.execute_query(create_table_sql)
            logger.info(f"PostgreSQL table '{config.psql.table_name}' created/verified successfully")
            
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL table '{config.psql.table_name}': {e}")
            raise

    def check_and_create_kb(self) -> None:
        """Check if knowledge base exists and create it if not."""
        try:
            kb_name = config.kb.name
            logger.info(f"Checking if knowledge base '{kb_name}' exists")
            
            existing_kbs = self._kb.list_knowledge_bases()
            logger.debug(f"Existing knowledge bases: {existing_kbs}")
            
            if kb_name not in existing_kbs:
                logger.info(f"Knowledge base '{kb_name}' not found, creating new one")
                self._kb.create(kb_name)
                logger.info(f"Knowledge base '{kb_name}' created successfully")
            else:
                logger.info(f"Knowledge base '{kb_name}' already exists")
                
        except Exception as e:
            logger.error(f"Failed to check/create knowledge base '{kb_name}': {e}")
            raise

    def create_mindsdb_psql_db_connection(self, db_name: str, engine: str) -> None:
        """Create a MindsDB database connection if it doesn't exist.

        Args:
            db_name (str): Name of the database to connect.
            engine (str): Database engine type ('postgres' or 'pgvector').
            conn_config (dict): Dictionary containing host, port, user, password.

        Returns:
            None
        """
        try:
            logger.info(f"Creating MindsDB database connection for '{db_name}'")
            existing_databases = [db.name for db in self._mdb.client.databases.list()]
            logger.debug(f"Existing MindsDB databases: {existing_databases}")

            if db_name not in existing_databases:
                logger.info(f"Database '{db_name}' not found in MindsDB, creating connection")

                conn_config={
                    "host": config.psql.host,
                    "port": config.psql.port,
                    "database": config.psql.database,
                    "user": config.psql.user,
                    "password": config.psql.password
                }

                safe_conn_params = conn_config.copy()
                safe_conn_params["password"] = "***"
                logger.debug(f"Connection parameters: {safe_conn_params}")

                self._mdb.client.databases.create(db_name, engine, conn_config)
                logger.info(f"MindsDB database connection '{db_name}' created successfully")
            else:
                logger.info(f"MindsDB database connection '{db_name}' already exists")

        except Exception as e:
            logger.error(f"Failed to create MindsDB database connection '{db_name}': {e}")
            raise


    def _load_sample_data(self) -> List[Dict[str, Any]]:
        """Load sample data from JSON file.
        
        Returns:
            List of sample records
            
        Raises:
            FileNotFoundError: If data file doesn't exist
            json.JSONDecodeError: If JSON is invalid
        """
        data_file_path = Path(__file__).parent.parent / "data/data.json"
        logger.info(f"Loading sample data from '{data_file_path}'")
        
        if not data_file_path.exists():
            logger.error(f"Data file not found: {data_file_path}")
            raise FileNotFoundError(f"Data file not found: {data_file_path}")
        
        try:
            with open(data_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                logger.info(f"Successfully loaded {len(data)} records from data file")
                return data
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in data file '{data_file_path}': {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading data file '{data_file_path}': {e}")
            raise

    def _process_record(self, record: Dict[str, Any]) -> None:
        """Process a single record by inserting to PostgreSQL and knowledge base.
        
        Args:
            record: Dictionary containing record data
        """
        try:
            logger.debug(f"Processing record with keys: {list(record.keys())}")
            txt = record["text"]
            
            logger.debug("Inserting record to PostgreSQL")
            record["text"] = txt.replace("0x00", "").replace("\x00","")
            self._psql.insert_article(record)
            
            text_content = utils.escape_text(txt)
            if not text_content:
                logger.warning("Record contains no 'text' field, skipping text processing")
                return
                
            metadata = {k: v for k, v in record.items() if k != "text"}
            logger.debug(f"Extracted metadata keys: {list(metadata.keys())}")
            
            logger.debug(f"Chunking text content (length: {len(text_content)} characters)")
            chunks = utils.chunk_text(text_content, chunk_size=2000, chunk_overlap=300)
            enriched_chunks = [chunk | metadata for chunk in chunks]
            
            logger.info(f"Processing {len(enriched_chunks)} chunks for record {metadata["article_id"]}")
            
            kb_name = config.kb.name
            logger.debug(f"Inserting chunks to knowledge base '{kb_name}'")
            self._kb.insert(kb_name, enriched_chunks, 10)
            logger.info(f"Successfully inserted {len(enriched_chunks)} chunks to knowledge base")
            
        except Exception as e:
            logger.error(f"Failed to process record: {e}")
            raise

    def insert_sample_records(self) -> None:
        """Insert sample records to PostgreSQL and knowledge base."""
        try:
            logger.info("Starting sample records insertion process")
            records = self._load_sample_data()
            records = random.sample(records, config.app.sample_data_count)
            for i, record in enumerate(records, 1):
                logger.info(f"Processing record {i}/{len(records)}")
                self._process_record(record)
                
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading sample data: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during sample records insertion: {e}")
            raise

    def check_embedding_compatability(self):
        if config.kb.embedding_model == "text-embedding-3-large":
            raise Exception("Invalid embedding model for pgvector. Please use 'text-embedding-3-small' or 'text-embedding-ada-002'.")

    def create_index_on_kb(self):
        self._kb.create_index(config.kb.name)
        
    def start(self) -> None:
        """Execute the complete warm-up process.
        
        Process:
        1. Check if postgres table exists, create if not
        2. Check if main KB exists, create if not  
        3. Create MindsDB database connection
        4. Insert sample data to postgres and KB
        """
        logger.info("Starting warm-up process...")
        
        try:

            logger.info("Step 1: Creating MindsDB PSQL vector database connection if enabled")
            if config.kb_storage.enable_pg_vector:
                self.check_embedding_compatability()
                self.create_mindsdb_psql_db_connection(
                        db_name=config.kb_storage.pg_vector_database,
                        engine='pgvector'
                    )

            logger.info("Step 2: Checking and creating knowledge base")
            self.check_and_create_kb()
            
            logger.info("Step 3: Creating PostgreSQL table")
            self.create_psql_table()
            
            logger.info("Step 4: Creating MindsDB PSQL database connection")
            self.create_mindsdb_psql_db_connection(
                db_name=config.psql.database,
                engine='postgres'
            )
            
            logger.info("Step 5: Inserting sample records")
            if config.app.load_sample_data:
                self.insert_sample_records()
                self.create_index_on_kb()
            
        except Exception as e:
            logger.error(f"Error during warm-up process: {e}")
            logger.exception("Full traceback:")
            raise
