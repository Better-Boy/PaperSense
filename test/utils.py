import json
import os
import platform
import subprocess
import sys
import time
from typing import Dict, List
import psutil
from rich.text import Text
from rich.table import Table
from rich.align import Align
from rich.panel import Panel
from rich import box

def setup_kb(host):
    """Setup Knowledge base before testing"""
    import requests, os
    try:
        create_kb_query = build_create_kb_query()
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
    
def build_create_kb_query():
    openai_api_key = os.getenv("OPENAI_API_KEY")
    # return f"""
    #         CREATE KNOWLEDGE_BASE IF NOT EXISTS arxiv_test_kb
    #         USING
    #             embedding_model = {{
    #                 "provider": "openai",
    #                 "model_name": "text-embedding-3-small",
    #                 "api_key": "{openai_api_key}"
    #             }},
    #             reranking_model = {{
    #                 "provider": "openai", 
    #                 "model_name": "gpt-4o",
    #                 "api_key": "{openai_api_key}"
    #             }},
    #             content_columns = ['text'],
    #             metadata_columns = ['authors', 'title', 'categories', 'arxiv_id'];
    #         """
    return f"""
            CREATE KNOWLEDGE_BASE IF NOT EXISTS arxiv_test_kb
            USING
                embedding_model = {{
                    "provider": "openai",
                    "model_name": "text-embedding-3-small",
                    "api_key": "{openai_api_key}"
                }},
                reranking_model = false,
                content_columns = ['text'],
                metadata_columns = ['authors', 'title', 'categories', 'arxiv_id'];
            """

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
        drop_kb_query = "DROP KNOWLEDGE_BASE arxiv_test_kb"
        start_time = time.time()
        response = requests.post(host + "/api/sql/query", json={'query': drop_kb_query, 'context': {'db': 'mindsdb'}}, timeout=30)
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

def start_resource_monitor_process(mdb_pid, output_dir: str):
    log_path = f"{output_dir}/activity.csv"
    cmd = ['psrecord', None, '--log-format', 'csv', '--log', log_path, '--interval', '1', '--include-children', '--include-io']
    cmd[1] = str(mdb_pid)
    return subprocess.Popen(cmd)

def validate_pid(pid):
    pid = int(pid)
    psutil.Process(pid)
    return pid

def create_header_panel():
    """Create a header panel with test information"""
    header_text = Text("MindsDB Knowledge Base Load Testing", style="bold magenta")
    return Panel(
        Align.center(header_text),
        box=box.DOUBLE,
        style="blue"
    )

def create_config_table(app_config, test_config, host, data_size_mb):
    """Create a configuration table"""
    config_table = Table(title="Test Configuration", box=box.ROUNDED)
    config_table.add_column("Parameter", style="cyan", no_wrap=True)
    config_table.add_column("Value", style="green")
    
    config_table.add_row("Host", host)
    config_table.add_row("Concurrent Users", str(test_config.concurrent_users))
    config_table.add_row("Spawn Rate", f"{test_config.spawn_rate}/s")
    config_table.add_row("Test Runtime", f"{test_config.test_runtime}s")
    config_table.add_row("Data Size", f"{data_size_mb:.2f} MB")
    config_table.add_row("Output Directory", test_config.output_dir)
    
    return config_table

def create_stats_table(stats):
    """Create a real-time stats table"""
    stats_table = Table(title="Live Test Statistics", box=box.ROUNDED)
    stats_table.add_column("Metric", style="cyan", no_wrap=True)
    stats_table.add_column("Value", style="yellow")
    
    total_stats = stats.total
    success_rate = ((total_stats.num_requests - total_stats.num_failures) / total_stats.num_requests * 100) if total_stats.num_requests > 0 else 0
    
    stats_table.add_row("Total Requests", f"{total_stats.num_requests:,}")
    stats_table.add_row("Total Failures", f"{total_stats.num_failures:,}")
    stats_table.add_row("Success Rate", f"{success_rate:.2f}%")
    stats_table.add_row("Avg Response Time", f"{total_stats.avg_response_time:.2f}ms")
    stats_table.add_row("Requests/Second", f"{total_stats.total_rps:.2f}")
    stats_table.add_row("Max Response Time", f"{total_stats.max_response_time:.2f}ms")
    stats_table.add_row("95th Percentile", f"{total_stats.get_response_time_percentile(0.95):.2f}ms")
    
    return stats_table

def create_operation_stats_table(stats):
    """Create a table showing stats for each operation type"""
    ops_table = Table(title="Operation Statistics", box=box.ROUNDED)
    ops_table.add_column("Operation", style="cyan")
    ops_table.add_column("Requests", style="green")
    ops_table.add_column("Failures", style="red")
    ops_table.add_column("Avg Time (ms)", style="yellow")
    ops_table.add_column("RPS", style="blue")
    
    for name, entry in stats.entries.items():
        if entry.num_requests > 0:
            ops_table.add_row(
                name,
                f"{entry.num_requests:,}",
                f"{entry.num_failures:,}",
                f"{entry.avg_response_time:.2f}",
                f"{entry.total_rps:.2f}"
            )
    
    return ops_table

def test_env_info():
        software = {}
        hardware = {}

        # OS and Python
        software['OS'] = platform.platform()
        software['Python Version'] = sys.version.split()[0]
        software['MindsDB Version'] = '25.6.3.1'
        software['Knowledge Base Embedding Model'] = "text-embedding-3-small"
        software['Knowledge Base ReRanking Model'] = "gpt-4o"
        software['Knowledge Base Storage'] = "ChromaDB"
        hardware['Machine'] = platform.machine()
        hardware['Processor'] = platform.processor()
        hardware['CPU Cores'] = psutil.cpu_count()
        hardware['RAM (GB)'] = round(psutil.virtual_memory().total / (1024**3), 2)
        
        # Disk info
        disk = psutil.disk_usage('/')
        hardware['Disk Total (GB)'] = round(disk.total / (1024**3), 2)
        
        md = ""

        md += "### Software Specs\n"
        for key, value in software.items():
            md += f"- **{key}**: {value}\n"
        md += "### Hardware Specs\n"
        for key, value in hardware.items():
            md += f"- **{key}**: {value}\n"

        return md