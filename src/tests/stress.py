from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
import time
from typing import Dict, List

import pandas as pd
from src import config_loader
from src.tests.base import MindsDBKnowledgeBaseTest
from src.tests.models import ExecutionResult


class ConcurrentTester(MindsDBKnowledgeBaseTest):
    """Handles concurrent testing of functions"""
    
    def __init__(self, mindsdb_pid: str):
        super().__init__(mindsdb_pid)

    def execute_op(self, batch_data: List[Dict], op_type: str) -> tuple:
        mindsdb_server_before_snapshot = self.mindsdb_server_monitor.get_single_snapshot()
        test_script_before_snapshot = self.test_script_monitor.get_single_snapshot()
        actual_start_time = time.time()
        try:
            if op_type == "ingest":
                self._kb.insert(self.kb_name, batch_data, config_loader.stress_test.batch_size)
            else:
                self._kb.search(config_loader.kb.name, batch_data["query"], {})
            
        finally:
            # Take post-execution snapshot
            mindsdb_server_after_snapshot = self.mindsdb_server_monitor.get_single_snapshot()
            test_script_after_snapshot = self.test_script_monitor.get_single_snapshot()
        
        return actual_start_time, mindsdb_server_before_snapshot, mindsdb_server_after_snapshot, test_script_before_snapshot, test_script_after_snapshot

    def stress_test(self, data_subset: List[Dict], user_cnt: int, op_type: str, dataset_size: int):
        with ThreadPoolExecutor(max_workers=user_cnt) as executor:
                future_to_user = {}

                if op_type == "ingest":
                    jump = user_cnt
                else:
                    jump = 1

                for idx in range(0, len(data_subset), jump):
                    batch = data_subset[idx : idx + user_cnt]

                    user_id = f"user_{idx+1:03d}"
                    submit_time = time.time()
                    future = executor.submit(self.execute_op, batch, op_type)
                    future_to_user[future] = (user_id, submit_time)

                for future in as_completed(future_to_user):
                    user_id, submit_time = future_to_user[future]
                    completion_time = time.time()
                    
                    try:
                        actual_start_time, mindsdb_server_before_snapshot, mindsdb_server_after_snapshot, test_script_before_snapshot, test_script_after_snapshot = future.result()
                        
                        # Calculate latency metrics
                        execution_duration = completion_time - actual_start_time
                        total_latency = completion_time - submit_time
                        
                        self.results.append(
                            ExecutionResult(
                                operation_type=op_type,
                                batch_size=config_loader.stress_test.batch_size,
                                data_size=len(data_subset) if op_type == "ingest" else dataset_size,
                                execution_time=execution_duration,
                                total_latency=total_latency,
                                concurrent_user_cnt=user_cnt,
                                mindsdb_server_before_snapshot=mindsdb_server_before_snapshot,
                                mindsdb_server_after_snapshot=mindsdb_server_after_snapshot,
                                test_script_before_snapshot=test_script_before_snapshot,
                                test_script_after_snapshot=test_script_after_snapshot,
                                success=True
                            )
                        )
                    except Exception as e:
                        # For failed calls, we don't have snapshots
                        self.results.append(
                            ExecutionResult(
                                operation_type=op_type,
                                batch_size=config_loader.stress_test.batch_size,
                                data_size=len(data_subset) if op_type == "ingest" else dataset_size,
                                execution_time=0,
                                total_latency=completion_time - submit_time,
                                concurrent_user_cnt=user_cnt,
                                success=False,
                                error_message=str(e)
                            )
                        )

    def start(self, data: List[Dict], queries: List[str]) -> None:
        """Execute function calls concurrently and track results with detailed latency metrics"""
        all_chunks = []
        print("starting concurrent testing")
        for file_data in data:
                chunks = self.break_file_into_chunks(file_data)
                all_chunks.extend(chunks)

        if config_loader.benchmark_test.use_continuous_monitoring:
            self.mindsdb_server_monitor.start_monitoring()
            self.test_script_monitor.start_monitoring()

        try:

            for data_size in config_loader.stress_test.data_sizes:
                    
                    data_subset = all_chunks[:data_size]

                    if data_size > len(all_chunks):
                        raise Exception(f"Not enough data for test - {data_size}")
                
                    for user_cnt in config_loader.stress_test.concurrent_users:
                        self.create_knowledge_base()
                        self.stress_test(data_subset=data_subset, user_cnt=user_cnt, op_type="ingest", dataset_size=data_size)
                        self.stress_test(data_subset=queries, user_cnt=user_cnt, op_type="search", dataset_size=data_size)
                        self.cleanup_knowledge_base()
        finally:
            # Stop continuous monitoring
            if config_loader.benchmark_test.use_continuous_monitoring:
                self.mindsdb_server_monitor.stop_monitoring()
                self.test_script_monitor.stop_monitoring()
    
    

    def save_report(self):
        self.save_to_csv(self.results, "st.csv")

        self.save_to_csv(self.mindsdb_server_monitor.resource_snapshots, "mdb_st.csv")
        
        self.save_to_csv(self.test_script_monitor.resource_snapshots, "ts_st.csv")