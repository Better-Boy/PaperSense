from collections import defaultdict
from datetime import datetime
import json
import os
import statistics
import time
import pandas as pd
from typing import Any, Dict, List
from dataclasses import asdict

from src.tests.models import ExecutionResult, ResourceSnapshot
from src import config_loader
from src.tests.base import MindsDBKnowledgeBaseTest

class BenchmarkTester(MindsDBKnowledgeBaseTest):
    """Handles benchmark testing of functions with continuous monitoring"""
    
    def __init__(self, mindsdb_pid: str):
        super().__init__(mindsdb_pid)
    
    def run_single_batch_ingestion(self, batch_data: List[Dict]) -> ExecutionResult:
        """Run a single benchmark iteration"""
        batch_size = len(batch_data)

        data_size = 0

        for record in batch_data:
            data_size += len(record["text"].encode('utf-16'))

        # Take before snapshot
        
        mindsdb_server_before_snapshot = self.mindsdb_server_monitor.get_single_snapshot()
        test_script_before_snapshot = self.test_script_monitor.get_single_snapshot()
        
        # Execute the method and measure time
        start_time = time.time()
        try:
            if not self._kb.insert_batch(self.kb_name, batch_data):
                raise Exception("Batch processing failed")
            
            execution_time = time.time() - start_time
            
            # Take after snapshot
            mindsdb_server_after_snapshot = self.mindsdb_server_monitor.get_single_snapshot()
            test_script_after_snapshot = self.test_script_monitor.get_single_snapshot()

            return ExecutionResult(
                operation_type="ingest",
                batch_size=batch_size,
                data_size=data_size,
                execution_time=execution_time,
                mindsdb_server_before_snapshot=mindsdb_server_before_snapshot,
                mindsdb_server_after_snapshot=mindsdb_server_after_snapshot,
                test_script_before_snapshot=test_script_before_snapshot,
                test_script_after_snapshot=test_script_after_snapshot,
                success=True
            )
            
        except Exception as e:
            mindsdb_server_after_snapshot = self.mindsdb_server_monitor.get_single_snapshot()
            test_script_after_snapshot = self.test_script_monitor.get_single_snapshot()

            execution_time = time.time() - start_time
            
            return ExecutionResult(
                operation_type="ingest",
                batch_size=batch_size,
                data_size=data_size,
                execution_time=execution_time,
                mindsdb_server_before_snapshot=mindsdb_server_before_snapshot,
                mindsdb_server_after_snapshot=mindsdb_server_after_snapshot,
                test_script_before_snapshot=test_script_before_snapshot,
                test_script_after_snapshot=test_script_after_snapshot,
                success=False,
                error_message=str(e)
            )
        
    def run_single_query(self, query: str, batch_size: int):
        mindsdb_server_before_snapshot = self.mindsdb_server_monitor.get_single_snapshot()
        test_script_before_snapshot = self.test_script_monitor.get_single_snapshot()
        
        # Execute the method and measure time
        start_time = time.time()
        try:
            res = self._kb.search(
                    config_loader.kb.name,
                    query["query"],
                    {})
            
            execution_time = time.time() - start_time
            
            # Take after snapshot
            mindsdb_server_after_snapshot = self.mindsdb_server_monitor.get_single_snapshot()
            test_script_after_snapshot = self.test_script_monitor.get_single_snapshot()
            
            return ExecutionResult(
                operation_type="search",
                batch_size=batch_size,
                data_size=0,
                execution_time=execution_time,
                mindsdb_server_before_snapshot=mindsdb_server_before_snapshot,
                mindsdb_server_after_snapshot=mindsdb_server_after_snapshot,
                test_script_before_snapshot=test_script_before_snapshot,
                test_script_after_snapshot=test_script_after_snapshot,
                success=True
            )
            
        except Exception as e:
            mindsdb_server_after_snapshot = self.mindsdb_server_monitor.get_single_snapshot()
            test_script_after_snapshot = self.test_script_monitor.get_single_snapshot()

            execution_time = time.time() - start_time
            
            return ExecutionResult(
                operation_type="search",
                batch_size=batch_size,
                data_size=0,
                execution_time=execution_time,
                mindsdb_server_before_snapshot=mindsdb_server_before_snapshot,
                mindsdb_server_after_snapshot=mindsdb_server_after_snapshot,
                test_script_before_snapshot=test_script_before_snapshot,
                test_script_after_snapshot=test_script_after_snapshot,
                success=False,
                error_message=str(e)
            )
        
    def start(self, data: List[Dict], queries: List[str]):
        all_chunks = []
        
        for file_data in data:
                chunks = self.break_file_into_chunks(file_data)
                all_chunks.extend(chunks)

        if config_loader.benchmark_test.use_continuous_monitoring:
            self.mindsdb_server_monitor.start_monitoring()
            self.test_script_monitor.start_monitoring()


        try:
            self.test_start_time = time.time()
            for data_size in config_loader.benchmark_test.data_sizes:

                if data_size > len(all_chunks):
                    print(f"Not enough data for test - {data_size}")
                    continue

                data_subset = all_chunks[:data_size]
            
                for b_size in config_loader.benchmark_test.batch_sizes:
                    self.create_knowledge_base()
                    
                    for idx in range(0, len(data_subset), b_size):
                        batch = data_subset[idx : idx + b_size]
                        result = self.run_single_batch_ingestion(batch)
                        self.results.append(result)

                    for query in queries:
                        result = self.run_single_query(query=query, batch_size=b_size, data_size=data_size)
                        self.results.append(result)
                    
                    self.cleanup_knowledge_base()
            self.test_end_time = time.time()
        finally:
            # Stop continuous monitoring
            if config_loader.benchmark_test.use_continuous_monitoring:
                self.mindsdb_server_monitor.stop_monitoring()
                self.test_script_monitor.stop_monitoring()


    def calculate_resource_delta(self, before: ResourceSnapshot, after: ResourceSnapshot) -> Dict[str, float]:
        """Calculate the change in resources from before to after"""
        
        return {
            'cpu_delta': after.cpu_percent - before.cpu_percent,
            'memory_percent_delta': after.memory_percent - before.memory_percent,
            'memory_rss_delta_mb': after.memory_rss_mb - before.memory_rss_mb,
            'memory_vms_delta_mb': after.memory_vms_mb - before.memory_vms_mb,
            'threads_delta': after.num_threads - before.num_threads,
            'files_delta': after.open_files - before.open_files,
            'connections_delta': after.network_connections - before.network_connections,
            'io_read_delta_mb': (after.io_read_bytes - before.io_read_bytes) / (1024 * 1024),
            'io_write_delta_mb': (after.io_write_bytes - before.io_write_bytes) / (1024 * 1024),
            'fds_delta': after.num_fds - before.num_fds
        }

    def calculate_throughput(self, result: ExecutionResult) -> Dict[str, float]:
        """Calculate throughput metrics"""
        return {
            'data_per_second_mb': result.data_size / (1024 * 1024) / result.execution_time,
            'operations_per_second': 1 / result.execution_time if result.execution_time > 0 else 0
        }

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of a dataset"""
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = k - f
        if f == len(sorted_data) - 1:
            return sorted_data[f]
        return sorted_data[f] * (1 - c) + sorted_data[f + 1] * c

    def calculate_statistics(self, results: List[ExecutionResult]) -> Dict[str, Dict[str, Any]]:
        """Calculate comprehensive statistics for a list of results"""
        if not results:
            return {}
        
        exec_times = [r.execution_time for r in results]

        mindsdb_deltas = [self.calculate_resource_delta(r.mindsdb_server_before_snapshot, r.mindsdb_server_after_snapshot) for r in results]

        test_script_deltas = [self.calculate_resource_delta(r.test_script_before_snapshot, r.test_script_after_snapshot) for r in results]

        throughputs = [self.calculate_throughput(r) for r in results]
        
        success_rate = len(1 for r in results if r.success is True) / len(results) if results else 0

        return {
                'success_rate': success_rate,
                'execution_time': {
                    'mean': statistics.mean(exec_times),
                    'median': statistics.median(exec_times),
                    'min': min(exec_times),
                    'max': max(exec_times),
                    'stdev': statistics.stdev(exec_times) if len(exec_times) > 1 else 0,
                    'p95': self._percentile(exec_times, 95),
                    'p99': self._percentile(exec_times, 99)
                },
                'mindsdb_resource_usage': {
                    'cpu_delta': {
                        'mean': statistics.mean([d['cpu_delta'] for d in mindsdb_deltas]),
                        'max': max([d['cpu_delta'] for d in mindsdb_deltas]),
                        'min': min([d['cpu_delta'] for d in mindsdb_deltas])
                    },
                    'memory_rss_delta_mb': {
                        'mean': statistics.mean([d['memory_rss_delta_mb'] for d in mindsdb_deltas]),
                        'max': max([d['memory_rss_delta_mb'] for d in mindsdb_deltas]),
                        'min': min([d['memory_rss_delta_mb'] for d in mindsdb_deltas])
                    },
                    'memory_percent_delta': {
                        'mean': statistics.mean([d['memory_percent_delta'] for d in mindsdb_deltas]),
                        'max': max([d['memory_percent_delta'] for d in mindsdb_deltas]),
                        'min': min([d['memory_percent_delta'] for d in mindsdb_deltas])
                    },
                    'io_read_delta_mb': {
                        'mean': statistics.mean([d['io_read_delta_mb'] for d in mindsdb_deltas]),
                        'total': sum([d['io_read_delta_mb'] for d in mindsdb_deltas])
                    },
                    'io_write_delta_mb': {
                        'mean': statistics.mean([d['io_write_delta_mb'] for d in mindsdb_deltas]),
                        'total': sum([d['io_write_delta_mb'] for d in mindsdb_deltas])
                    }
                },
                'test_script_resource_usage': {
                    'cpu_delta': {
                        'mean': statistics.mean([d['cpu_delta'] for d in test_script_deltas]),
                        'max': max([d['cpu_delta'] for d in test_script_deltas]),
                        'min': min([d['cpu_delta'] for d in test_script_deltas])
                    },
                    'memory_rss_delta_mb': {
                        'mean': statistics.mean([d['memory_rss_delta_mb'] for d in test_script_deltas]),
                        'max': max([d['memory_rss_delta_mb'] for d in test_script_deltas]),
                        'min': min([d['memory_rss_delta_mb'] for d in test_script_deltas])
                    },
                    'memory_percent_delta': {
                        'mean': statistics.mean([d['memory_percent_delta'] for d in test_script_deltas]),
                        'max': max([d['memory_percent_delta'] for d in test_script_deltas]),
                        'min': min([d['memory_percent_delta'] for d in test_script_deltas])
                    },
                    'io_read_delta_mb': {
                        'mean': statistics.mean([d['io_read_delta_mb'] for d in test_script_deltas]),
                        'total': sum([d['io_read_delta_mb'] for d in test_script_deltas])
                    },
                    'io_write_delta_mb': {
                        'mean': statistics.mean([d['io_write_delta_mb'] for d in test_script_deltas]),
                        'total': sum([d['io_write_delta_mb'] for d in test_script_deltas])
                    }
                },
                'throughput': {
                    'data_per_second_mb': {
                        'mean': statistics.mean([t['data_per_second_mb'] for t in throughputs]),
                        'max': max([t['data_per_second_mb'] for t in throughputs]),
                        'min': min([t['data_per_second_mb'] for t in throughputs])
                    },
                    'operations_per_second': {
                        'mean': statistics.mean([t['operations_per_second'] for t in throughputs]),
                        'max': max([t['operations_per_second'] for t in throughputs]),
                        'min': min([t['operations_per_second'] for t in throughputs])
                    }
                },
                'batch_sizes': config_loader.benchmark_test.batch_sizes,
                'data_sizes': {
                    'mean': statistics.mean([r.data_size for r in results]),
                    'total': sum([r.data_size for r in results])
                }
            }

    def generate_comparison(self, current_val: float, baseline_val: float, is_higher_better: bool = False) -> Dict[str, Any]:
        """Generate comparison between current and baseline values"""
        if baseline_val == 0:
            return {'change_percent': 0, 'change_absolute': current_val - baseline_val, 'status': 'baseline_zero'}
        
        change_percent = ((current_val - baseline_val) / baseline_val) * 100
        change_absolute = current_val - baseline_val
        
        if is_higher_better:
            status = 'improved' if change_percent > 0 else 'degraded' if change_percent < 0 else 'unchanged'
        else:
            status = 'improved' if change_percent < 0 else 'degraded' if change_percent > 0 else 'unchanged'
        
        return {
            'change_percent': change_percent,
            'change_absolute': change_absolute,
            'status': status
        }
    
    def performance_report(self, op_type, op_res, stats):
        report = []
        report.append(f"## {op_type.title()} Operation Analysis\n")
        report.append("### Performance Metrics\n")
        report.append(f"- **Total Operations**: {len(op_res)}")
        report.append(f"- **Success Rate**: {stats['success_rate']:.2%}")

        if op_type == "ingest":
            report.append(f"- **Batch Sizes Tested**: {', '.join(config_loader.benchmark_test.batch_sizes)}")
            
        report.append(f"- **Knowledge Base Rows Tested**: {', '.join(config_loader.benchmark_test.data_sizes)}")

        if op_type == "ingest":
            report.append(f"- **Average Data Size**: {stats['data_sizes']['mean']/(1024*1024):.2f} MB")
            report.append(f"- **Total Data Processed**: {stats['data_sizes']['total']/(1024*1024):.2f} MB\n")

        # Execution Time Analysis
        exec_stats = stats['execution_time']
        report.append("### Execution Time Analysis\n")
        report.append(f"- **Mean**: {exec_stats['mean']:.3f}s")
        report.append(f"- **Median**: {exec_stats['median']:.3f}s")
        report.append(f"- **Min**: {exec_stats['min']:.3f}s")
        report.append(f"- **Max**: {exec_stats['max']:.3f}s")
        report.append(f"- **Standard Deviation**: {exec_stats['stdev']:.3f}s")
        report.append(f"- **95th Percentile**: {exec_stats['p95']:.3f}s")
        report.append(f"- **99th Percentile**: {exec_stats['p99']:.3f}s\n")

        # Resource Usage
        report.append("## Resource Usage\n")
        resource_stats = stats['mindsdb_resource_usage']
        report.append("### MindsDB Process Resource Usage\n")
        report.append(f"- **CPU Delta**: {resource_stats['cpu_delta']['mean']:.2f}% (avg), {resource_stats['cpu_delta']['max']:.2f}% (max)")
        report.append(f"- **Memory RSS Delta**: {resource_stats['memory_rss_delta_mb']['mean']:.2f} MB (avg), {resource_stats['memory_rss_delta_mb']['max']:.2f} MB (max)")
        report.append(f"- **Memory % Delta**: {resource_stats['memory_percent_delta']['mean']:.2f}% (avg)")
        report.append(f"- **IO Read**: {resource_stats['io_read_delta_mb']['total']:.2f} MB (total)")
        report.append(f"- **IO Write**: {resource_stats['io_write_delta_mb']['total']:.2f} MB (total)\n")

        resource_stats = stats['test_script_resource_usage']
        report.append("### Benchmarking script Process Resource Usage\n")
        report.append(f"- **CPU Delta**: {resource_stats['cpu_delta']['mean']:.2f}% (avg), {resource_stats['cpu_delta']['max']:.2f}% (max)")
        report.append(f"- **Memory RSS Delta**: {resource_stats['memory_rss_delta_mb']['mean']:.2f} MB (avg), {resource_stats['memory_rss_delta_mb']['max']:.2f} MB (max)")
        report.append(f"- **Memory % Delta**: {resource_stats['memory_percent_delta']['mean']:.2f}% (avg)")
        report.append(f"- **IO Read**: {resource_stats['io_read_delta_mb']['total']:.2f} MB (total)")
        report.append(f"- **IO Write**: {resource_stats['io_write_delta_mb']['total']:.2f} MB (total)\n")

        throughput_stats = stats['throughput']
        report.append("### Throughput\n")
        if op_type == "ingest":
            report.append(f"- **Data Throughput**: {throughput_stats['data_per_second_mb']['mean']:.2f} MB/s (avg), {throughput_stats['data_per_second_mb']['max']:.2f} MB/s (max)")
        report.append(f"- **Operations Throughput**: {throughput_stats['operations_per_second']['mean']:.2f} ops/s (avg)\n")

        if self.baseline_stats and op_type in self.baseline_stats:
            report.append("### Baseline Comparison\n")
            baseline = self.baseline_stats[op_type]
            
            # Execution time comparison
            exec_comparison = self.generate_comparison(
                exec_stats['mean'], 
                baseline['execution_time']['mean'], 
                is_higher_better=False
            )
            status_emoji = "✅" if exec_comparison['status'] == 'improved' else "❌" if exec_comparison['status'] == 'degraded' else "➖"
            report.append(f"- **Execution Time**: {status_emoji} {exec_comparison['change_percent']:+.1f}% ({exec_stats['mean']:.3f}s vs {baseline['execution_time']['mean']:.3f}s)")
            
            # Throughput comparison
            if op_type == "ingest":
                throughput_comparison = self.generate_comparison(
                    throughput_stats['data_per_second_mb']['mean'],
                    baseline['throughput']['data_per_second_mb']['mean'],
                    is_higher_better=True
                )
                status_emoji = "✅" if throughput_comparison['status'] == 'improved' else "❌" if throughput_comparison['status'] == 'degraded' else "➖"
                report.append(f"- **Throughput**: {status_emoji} {throughput_comparison['change_percent']:+.1f}% ({throughput_stats['data_per_second_mb']['mean']:.2f} vs {baseline['throughput']['data_per_second_mb']['mean']:.2f} MB/s)")
            
            # Memory comparison
            resource_stats = stats['mindsdb_resource_usage']
            memory_comparison = self.generate_comparison(
                resource_stats['memory_rss_delta_mb']['mean'],
                baseline['resource_usage']['memory_rss_delta_mb']['mean'],
                is_higher_better=False
            )
            status_emoji = "✅" if memory_comparison['status'] == 'improved' else "❌" if memory_comparison['status'] == 'degraded' else "➖"
            report.append(f"- **MindsDB Memory Usage**: {status_emoji} {memory_comparison['change_percent']:+.1f}% ({resource_stats['memory_rss_delta_mb']['mean']:.2f} vs {baseline['resource_usage']['memory_rss_delta_mb']['mean']:.2f} MB)\n")

            resource_stats = stats['test_script_resource_usage']
            memory_comparison = self.generate_comparison(
                resource_stats['memory_rss_delta_mb']['mean'],
                baseline['resource_usage']['memory_rss_delta_mb']['mean'],
                is_higher_better=False
            )
            status_emoji = "✅" if memory_comparison['status'] == 'improved' else "❌" if memory_comparison['status'] == 'degraded' else "➖"
            report.append(f"- **Benchmarking Script Memory Usage**: {status_emoji} {memory_comparison['change_percent']:+.1f}% ({resource_stats['memory_rss_delta_mb']['mean']:.2f} vs {baseline['resource_usage']['memory_rss_delta_mb']['mean']:.2f} MB)\n")
        
        return report
    

    def comparative_analysis(self, stats):
        report = []
        report.append("## Comparative Analysis\n")
        operation_types = list(stats.keys())
        
        # Compare execution times
        report.append("### Operation Type Performance Comparison\n")
        for i, op1 in enumerate(operation_types):
            for op2 in operation_types[i+1:]:
                op1_time = stats[op1]['execution_time']['mean']
                op2_time = stats[op2]['execution_time']['mean']
                faster_op = op1 if op1_time < op2_time else op2
                slower_op = op2 if op1_time < op2_time else op1
                speedup = max(op1_time, op2_time) / min(op1_time, op2_time)
                report.append(f"- **{faster_op.title()}** is {speedup:.1f}x faster than **{slower_op.title()}**")
        report.append("")


    def recommendations(self, stats):
        report = []
        report.append("## Recommendations\n")
        
        for op_type, stats in stats.items():
            exec_stats = stats['execution_time']
            resource_stats = stats['resource_usage']
            
            report.append(f"### {op_type.title()} Operations\n")
            
            # Performance recommendations
            if exec_stats['stdev'] / exec_stats['mean'] > 0.3:
                report.append("- ⚠️ **High execution time variability detected** - Consider investigating inconsistent performance")
            
            if resource_stats['memory_rss_delta_mb']['max'] > 1000:
                report.append("- ⚠️ **High memory usage detected** - Consider memory optimization")
            
            if stats['success_rate'] < 0.95:
                report.append(f"- ❌ **Low success rate ({stats['success_rate']:.1%})** - Investigate failure causes")
            
            if exec_stats['p99'] / exec_stats['median'] > 3:
                report.append("- ⚠️ **High tail latency** - 99th percentile is significantly higher than median")
            
            # Baseline comparison recommendations
            if self.baseline_stats and op_type in self.baseline_stats:
                baseline = self.baseline_stats[op_type]
                current_throughput = stats['throughput']['data_per_second_mb']['mean']
                baseline_throughput = baseline['throughput']['data_per_second_mb']['mean']
                
                if current_throughput < baseline_throughput * 0.9:
                    report.append("- 📉 **Performance regression detected** - Current throughput is significantly lower than baseline")
                elif current_throughput > baseline_throughput * 1.1:
                    report.append("- 📈 **Performance improvement detected** - Current throughput is significantly higher than baseline")
            
            report.append("")


    def error_analysis(self):
        report = []
        # Error Analysis
        failed_results = [r for r in self.results if not r.success]
        if failed_results:
            report.append("## Error Analysis\n")
            error_by_type = defaultdict(list)
            for result in failed_results:
                error_by_type[result.operation_type].append(result.error_message)
            
            for op_type, errors in error_by_type.items():
                report.append(f"### {op_type.title()} Operation Errors\n")
                error_counts = defaultdict(int)
                for error in errors:
                    error_counts[error] += 1
                
                for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                    report.append(f"- **{error}**: {count} occurrences")
                report.append("")
        
        return report
    
    def load_baseline_stats(self):
        self.baseline_stats = json.load(open(config_loader.benchmark_test.baseline_metrics_path))

    def generate_markdown_report(self):
        self.load_baseline_stats()
        main_report = []
        main_report.append("# Benchmark Analysis Report\n")
        main_report.append("---")
        main_report.append(f"**Test start time** : {str(datetime.fromtimestamp(self.test_start_time))}\n")
        main_report.append(f"**Test end time** : {str(datetime.fromtimestamp(self.test_end_time))}\n")
        main_report.append(f"**Test duration** : {(self.test_end_time - self.test_start_time):.2f} seconds\n")
        main_report.append(f"**Test Version** : v1.0.0\n")
        main_report.append(self.test_environment_info() + "\n")

        md += "---"
        main_report.append("## Executive Summary\n")
        main_report.append(f"- **Total Operations Analyzed**: {len(self.results)}")
        main_report.append("- **Operation Types**: ingestion, search")
        overall_success_rate = sum(1 for r in self.results if r.success is True) / len(self.results)
        main_report.append(f"- **Overall Success Rate**: {overall_success_rate:.2%}\n")
        ingest_metrics = [r for r in self.results if r.operation_type == "ingest"]
        search_metrics = [r for r in self.results if r.operation_type == "search"]
        ingest_stats = self.calculate_statistics(ingest_metrics)
        search_stats = self.calculate_statistics(search_metrics)

        combined_stats = {"ingest": ingest_stats, "search": search_stats}
        main_report.extend(self.performance_report("ingest", ingest_metrics, ingest_stats))
        main_report.extend(self.performance_report("search", search_metrics, search_stats))

        main_report.extend(self.comparative_analysis(combined_stats))

        main_report.extend(self.recommendations(combined_stats))

        main_report.extend(self.error_analysis())

        return "\n".join(main_report)
    
    def save_to_csv(self, snapshots, f_name):
        to_dict = []
        
        for snap in snapshots:
            to_dict.append(asdict(snap))
        
        df = pd.DataFrame(to_dict)

        df.to_csv(f_name, index=False)

    def save_report(self):
        report = self.generate_markdown_report()
        out_dir = config_loader.benchmark_test.output_dir
        f_path = out_dir + "/benchmark.md"
        os.makedirs(out_dir, exist_ok=True)
        with open(out_dir + "/benchmark.md", 'w') as f:
            f.write(report)
        print(f"Report saved to {f_path}")

        self.save_to_csv(self.mindsdb_server_monitor.resource_snapshots, out_dir+"/mindsdb_server_resource_snapshots.csv")
        
        self.save_to_csv(self.test_script_monitor.resource_snapshots, out_dir+"/benchmark_testing_script_resource_snapshots.csv")
        
