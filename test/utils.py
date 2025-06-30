import json
import os
import subprocess
import time
from typing import Dict, List
import psutil


def setup_kb(host):
    """Setup Knowledge base before testing"""
    import requests, os
    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        create_kb_query = f"""
            CREATE KNOWLEDGE_BASE IF NOT EXISTS arxiv_test_kb
            USING
                embedding_model = {{
                    "provider": "openai",
                    "model_name": "text-embedding-3-small",
                    "api_key": "{openai_api_key}"
                }},
                reranking_model = {{
                    "provider": "openai", 
                    "model_name": "gpt-4o",
                    "api_key": "{openai_api_key}"
                }},
                content_columns = ['text'],
                metadata_columns = ['authors', 'title', 'categories', 'arxiv_id'];
            """
        start_time = time.time()
        response = requests.post(host + "/api/sql/query", json={'query': create_kb_query, 'context': {'db': 'mindsdb'}}, timeout=30)
        end_time = time.time()
        if response.status_code == 200:
            res = response.json()
            print("✓ Knowledge base setup completed successfully")
            return (True, end_time - start_time)
        else:
            print(f"✗ Knowledge base setup failed: {response.status_code}")
            return (False, None)
    except Exception as e:
        print(f"✗ Knowledge base setup error: {e}")
        return (False, None)

def row_count_kb(host):
    """Row count in knowledge base"""
    import requests
    try:
        row_cnt_kb_query = "SELECT COUNT(*) AS row_cnt KNOWLEDGE_BASE arxiv_test_kb"
        response = requests.post(host + "/api/sql/query", json={'query': row_cnt_kb_query, 'context': {'db': 'mindsdb'}}, timeout=30)
        if response.status_code == 200:
            res = response.json()
            if res["type"] == "error": return 0
            return res["data"][0][0]
        else:
            print(f"✗ Knowledge row count down failed: {response.status_code}")
            return 0
    except Exception as e:
        print(f"✗ Knowledge Base row count error: {e}")
        return 0

def cleanup_kb(host):
    """Cleanup knowlege base after testing"""
    import requests
    try:
        create_kb_query = "DROP KNOWLEDGE_BASE arxiv_test_kb"
        start_time = time.time()
        response = requests.post(host + "/api/sql/query", json={'query': create_kb_query, 'context': {'db': 'mindsdb'}}, timeout=30)
        end_time = time.time()
        if response.status_code == 200:
            print("✓ Knowledge base tear down completed successfully")
            return (True, end_time - start_time)
        else:
            print(f"✗ Knowledge base tear down failed: {response.status_code}")
            return (False, None)
    except Exception as e:
        print(f"✗ Knowledge Base tear down error: {e}")
        return (False, None)

def load_search_queries(path) -> List[Dict]:
        """Load different types of search queries with varying complexity"""
        return json.load(open(path))
    
def load_ingestion_data(path, data_size) -> List[Dict]:
    test_data = json.load(open(path, "r", encoding="utf-16"))
    # test_data = test_data[:config["data_size"]]
    test_data = test_data[:data_size]
    size_bytes = 0
    for item in test_data:
        size_bytes += len(item["text"].encode("utf-16"))
    total_mb = size_bytes / (1024 ** 2)
    test_queries = build_insert_queries(test_data)
    return test_queries, total_mb

def build_insert_queries(records: List[Dict]) -> List[str]:
    insert_queries = []
    columns = ["text", "authors", "title", "categories", "arxiv_id"]
    for record in records:
        val = []
        for col in columns:
            val.append(f'"{record[col]}"')
        
        val_clause = f"({', '.join(val)})"
        query = f"""
            INSERT INTO arxiv_test_kb ({", ".join(columns)}) VALUES {val_clause};
        """
        insert_queries.append(query.strip())
    return insert_queries


def validate_args(parser, args):
    if not os.path.isfile(args.data_file_path):
        parser.error(f"The file {args.data_file_path} does not exist.")
    
    if not args.data_file_path.lower().endswith('.json'):
        parser.error(f"The file {args.data_file_path} is not a JSON file.")

    if not os.path.isfile(args.search_query_file_path):
        parser.error(f"The file {args.search_query_file_path} does not exist.")

    if not args.search_query_file_path.lower().endswith('.json'):
        parser.error(f"The file {args.search_query_file_path} is not a JSON file.")

def start_resource_monitor_process(mdb_pid, test_type):
    log_path = f"{os.getcwd()}/{test_type}_activity.csv"
    cmd = ['psrecord', None, '--log-format', 'csv', '--log', log_path, '--interval', '1', '--include-children', '--include-io']
    cmd[1] = str(mdb_pid)
    return subprocess.Popen(cmd)

def validate_pid(pid):
    pid = int(pid)
    psutil.Process(pid)
    return pid