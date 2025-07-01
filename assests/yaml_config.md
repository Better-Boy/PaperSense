## Configuration Settings

The yaml configuration file is very important as it can affect the way papersense app behaves. 

```yaml
mindsdb_infra:
  host: 127.0.0.1
  port: 47334

knowledge_base:
  name: arxiv_kb
  embedding_model: text-embedding-3-small
  reranking_model: gpt-4o
  metadata_columns:
    - authors
    - categories
    - published_year
    - primary_category
    - article_id
    - title
    - abstract
  storage:
    enable_pg_vector: False
    pg_vector_database: pgvec_db
    pg_vector_table: vec_table
  content_columns:
    - text

postgres:
  host: localhost
  port: 5432
  database: arxiv_psql_db
  user: postgres
  password: postgres
  table_name: arxiv_txt

agent:
  openai_model: gpt-4o

app:
  log_level: INFO
  log_format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  load_sample_data: True
  sample_data_count: 20
  openai_api_key: <sk-proj>
```


Description of the configs in the config file:

`mindsdb_infra` - Configures the connection to the MindsDB instance.


| Key    | Description                                                                    |
| ------ | ------------------------------------------------------------------------------ |
| `host` | IP address of the MindsDB server. Typically `127.0.0.1` for local development. |
| `port` | Port number to connect to the MindsDB service (default: `47334`).              |


---

`knowledge_base` - Defines how data is embedded, stored, and retrieved from knowledge base.

| Key                | Description                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------------- |
| `name`             | Name assigned to the knowledge base (e.g., `arxiv_kb`).                                     |
| `embedding_model`  | Name of the embedding model used to vectorize textual data.                                 |
| `reranking_model`  | Model used to rerank search or retrieval results (e.g., `gpt-4o`).                          |
| `metadata_columns` | List of columns containing metadata (non-content fields such as authors, categories, etc.). |
| `content_columns`  | List of columns containing the actual textual content to be embedded (e.g., `text`).        |

`knowledge_base.storage` - Settings related to the vector storage the knowledge uses.

| Key                  | Description                                                                        |
| -------------------- | ---------------------------------------------------------------------------------- |
| `enable_pg_vector`   | Boolean flag to enable/disable the use of `pgvector` extension for vector storage. |
| `pg_vector_database` | Name of the PostgreSQL database where vectors will be stored.                      |
| `pg_vector_table`    | Name of the table within the vector database.                                      |

- When `enable_pg_vector` is enabled, then the connection settings from the `postgres` section will be used.
- When `enable_pg_vector` is disabled, then the knowledge bases are created using the default `chromaDB` vector storage

---

`postgres` - Database connection settings

| Key          | Description                                              |
| ------------ | -------------------------------------------------------- |
| `host`       | Hostname or IP where the PostgreSQL server is running.   |
| `port`       | Port number for the PostgreSQL server (default: `5432`). |
| `database`   | Name of the PostgreSQL database to connect to.           |
| `user`       | Username for PostgreSQL authentication.                  |
| `password`   | Password for the PostgreSQL user.                        |
| `table_name` | Table name in the database that stores article data.     |

---

`agent` - Specifies the OpenAI model used for AI-driven response generation.

| Key            | Description                                                   |
| -------------- | ------------------------------------------------------------- |
| `openai_model` | Name of the OpenAI model used for the agent (e.g., `gpt-4o`). |

---

`app` - General application-level settings for logging, API usage, and sample data loading.

| Key                 | Description                                                        |
| ------------------- | ------------------------------------------------------------------ |
| `log_level`         | Sets the logging verbosity level (e.g., `INFO`, `DEBUG`, `ERROR`). |
| `log_format`        | Format string for logs using Python logging syntax.                |
| `load_sample_data`  | Boolean flag to load sample data on app startup.                   |
| `sample_data_count` | Number of sample records to load if enabled.                       |
| `openai_api_key`    | API key for accessing OpenAI services (masked here for security).  |

