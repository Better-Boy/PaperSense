from .base import MindsDBKnowledgeBaseTest
from typing import List, Dict, Any

import psutil
import json

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich import box
from datetime import datetime
from .. import config_loader as config

console = Console()

class BenchmarkTest(MindsDBKnowledgeBaseTest):

    def __init__(self):
        super().__init__()
        self.bench_config = config.benchmark_test
        self.results = {
            'test_start_time': datetime.now().isoformat(),
            'ingestion_tests': {},
            'query_tests': {}
        }

    def start(self, files_data: List[Dict[str, Any]], queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run comprehensive benchmark tests"""

        console.print(Panel("[bold green]Starting Benchmark Tests[/bold green]", box=box.DOUBLE))

        if not self.create_knowledge_base():
            console.print("Knowledge Base creation failed")
            return
        

        # Test different batch sizes for ingestion
        for batch_size in self.bench_config.batch_sizes:
            console.print(f"\n[bold cyan]--- Testing batch size: {batch_size} ---[/bold cyan]")
            ingestion_results = []
            
            # Run multiple iterations for reliability
            for iteration in range(self.bench_config.iterations):
                console.print(f"[yellow]Iteration {iteration + 1}/{self.bench_config.iterations}[/yellow]")
                result = self.ingest_data(files_data, batch_size)
                ingestion_results.append(result)
                
            # Calculate average metrics across iterations
            self.results['ingestion_tests'][batch_size] = {
                'iterations': ingestion_results,
                'avg_metrics': self._calculate_average_metrics(ingestion_results)
            }
            
        # Test query performance
        console.print("\n[bold cyan]--- Testing Query Performance ---[/bold cyan]")
        query_results = self.execute_queries(queries)
        self.results['query_tests'] = query_results
            
        self.results['test_end_time'] = datetime.now().isoformat()

        self.cleanup_knowledge_base()

    def _write_benchmark_report(self, f):
        """Write benchmark test report in markdown format"""
        f.write("# MindsDB Knowledge Base Benchmark Test Report\n\n")
        f.write(f"**Test Date**: {self.results.get('test_start_time', 'Unknown')}\n")
        f.write(f"**Knowledge Base**: {self.kb_name}\n")
        f.write(f"**Test Duration**: {self.results.get('test_start_time', '')} - {self.results.get('test_end_time', '')}\n\n")
        
        # Test Environment
        f.write("## Test Environment\n\n")
        f.write("- **MindsDB Version**: 25.6.3.1\n")
        f.write(f"- **System**: {psutil.cpu_count()} CPU cores, {psutil.virtual_memory().total / (1024**3):.1f} GB RAM\n")
        f.write(f"- **Test Configuration**: {self.bench_config.iterations} iterations per test\n")
        f.write(f"- **Batch Sizes Tested**: {', '.join(map(str, self.bench_config.batch_sizes))}\n")
        
        # Executive Summary
        f.write("## Executive Summary\n\n")
        
        # Find best performing configuration
        best_batch_size = None
        best_throughput = 0
        if 'ingestion_tests' in self.results:
            for batch_size, test_results in self.results['ingestion_tests'].items():
                avg_throughput = test_results['avg_metrics'].get('chunks_per_second', 0)
                if avg_throughput > best_throughput:
                    best_throughput = avg_throughput
                    best_batch_size = batch_size
        
        if best_batch_size:
            f.write(f"- **Optimal Batch Size**: {best_batch_size} (achieving {best_throughput:.2f} chunks/second)\n")
        
        if 'query_tests' in self.results:
            query_stats = self.results['query_tests'].get('latency_stats', {})
            avg_latency = query_stats.get('avg_latency_ms', 0)
            p95_latency = query_stats.get('p95_latency_ms', 0)
            f.write(f"- **Query Performance**: Average latency {avg_latency:.2f}ms, P95 latency {p95_latency:.2f}ms\n")
        
        f.write("\n")
        
        # Data Ingestion Results
        f.write("## Data Ingestion Performance\n\n")
        
        if 'ingestion_tests' in self.results:
            f.write("### Batch Size Performance Comparison\n\n")
            f.write("| Batch Size | Avg Throughput (chunks/s) | Avg Time per Chunk (ms) | Avg Time per 1000 Chunks (ms) | Memory Usage (MB) |\n")
            f.write("|------------|---------------------------|-------------------------|-------------------------------|-------------------|\n")
            
            for batch_size, test_results in self.results['ingestion_tests'].items():
                avg_metrics = test_results['avg_metrics']
                throughput = avg_metrics.get('chunks_per_second', 0)
                time_per_chunk = avg_metrics.get('avg_time_per_chunk_ms', 0)
                time_per_1000 = avg_metrics.get('avg_time_per_1000_chunks_ms', 0)
                
                # Get memory usage from first iteration
                memory_usage = 0
                if test_results['iterations']:
                    memory_usage = test_results['iterations'][0].get('system_metrics', {}).get('peak_memory_mb', 0)
                
                f.write(f"| {batch_size} | {throughput:.2f} | {time_per_chunk:.2f} | {time_per_1000:.2f} | {memory_usage:.2f} |\n")
            
            f.write("\n### Detailed Ingestion Metrics\n\n")
            
            for batch_size, test_results in self.results['ingestion_tests'].items():
                f.write(f"#### Batch Size: {batch_size}\n\n")
                
                avg_metrics = test_results['avg_metrics']
                iterations = test_results['iterations']
                
                f.write(f"- **Iterations**: {len(iterations)}\n")
                f.write(f"- **Average Throughput**: {avg_metrics.get('chunks_per_second', 0):.2f} ± {avg_metrics.get('chunks_per_second_std', 0):.2f} chunks/second\n")
                f.write(f"- **Average Time per Chunk**: {avg_metrics.get('avg_time_per_chunk_ms', 0):.2f} ± {avg_metrics.get('avg_time_per_chunk_ms_std', 0):.2f} ms\n")
                f.write(f"- **Average Time per 1000 Chunks**: {avg_metrics.get('avg_time_per_1000_chunks_ms', 0):.2f} ± {avg_metrics.get('avg_time_per_1000_chunks_ms_std', 0):.2f} ms\n")
                
                if iterations:
                    first_iteration = iterations[0]
                    f.write(f"- **Total Files Processed**: {first_iteration.get('total_files', 0)}\n")
                    f.write(f"- **Total Chunks**: {first_iteration.get('total_chunks', 0)}\n")
                    f.write(f"- **Average Chunks per File**: {first_iteration.get('avg_chunks_per_file', 0):.2f}\n")
                    f.write(f"- **Success Rate**: {(first_iteration.get('successful_chunks', 0) / first_iteration.get('total_chunks', 1)) * 100:.1f}%\n")
                
                f.write("\n")
        
        # Query Performance Results
        f.write("## Query Performance\n\n")
        
        if 'query_tests' in self.results:
            query_results = self.results['query_tests']
            latency_stats = query_results.get('latency_stats', {})
            
            f.write("### Query Latency Statistics\n\n")
            f.write("| Metric | Value (ms) |\n")
            f.write("|--------|------------|\n")
            f.write(f"| Average Latency | {latency_stats.get('avg_latency_ms', 0):.2f} |\n")
            f.write(f"| Median Latency | {latency_stats.get('median_latency_ms', 0):.2f} |\n")
            f.write(f"| P95 Latency | {latency_stats.get('p95_latency_ms', 0):.2f} |\n")
            f.write(f"| P99 Latency | {latency_stats.get('p99_latency_ms', 0):.2f} |\n")
            f.write(f"| Min Latency | {latency_stats.get('min_latency_ms', 0):.2f} |\n")
            f.write(f"| Max Latency | {latency_stats.get('max_latency_ms', 0):.2f} |\n")
            
            f.write("\n### Query Execution Summary\n\n")
            f.write(f"- **Total Queries**: {query_results.get('total_queries', 0)}\n")
            f.write(f"- **Successful Queries**: {query_results.get('successful_queries', 0)}\n")
            f.write(f"- **Failed Queries**: {query_results.get('failed_queries', 0)}\n")
            f.write(f"- **Success Rate**: {(query_results.get('successful_queries', 0) / query_results.get('total_queries', 1)) * 100:.1f}%\n")
            f.write(f"- **Queries per Second**: {query_results.get('queries_per_second', 0):.2f}\n\n")
        
        # Add recommendations section to benchmark report
        f.write("## Performance Recommendations\n\n")
        if hasattr(self, 'recommendations') and self.recommendations:
            for i, recommendation in enumerate(self.recommendations, 1):
                f.write(f"{i}. {recommendation}\n\n")
        else:
            f.write("No specific recommendations generated. System performance appears optimal.\n\n")
        
        # Add reproduction section
        f.write("## Reproducing This Test\n\n")
        f.write("To reproduce this benchmark test:\n\n")
        f.write("1. **Setup Environment**\n")
        f.write("   - Install MindsDB SDK and required dependencies\n")
        f.write("   - Ensure MindsDB server is running\n")
        f.write("   - Prepare test data in the required JSON format\n\n")
        f.write("2. **Configure Test Parameters**\n")
        f.write("   ```python\n")
        f.write("   config = TestConfig(\n")
        f.write(f"       kb_name=\"{self.kb_name}\",\n")
        f.write(f"       batch_sizes={self.bench_config.batch_sizes},\n")
        f.write(f"       benchmark_iterations={self.bench_config.iterations}\n")
        f.write("   )\n")
        f.write("   ```\n\n")
        f.write("3. **Execute Test Suite**\n")
        f.write("   ```python\n")
        f.write("   test_suite = MindsDBKnowledgeBaseTest(config)\n")
        f.write("   test_suite.run_benchmark_tests(files_data, queries_data)\n")
        f.write("   ```\n\n")
        f.write("4. **Review Results**\n")
        f.write("   - Check generated markdown reports\n")
        f.write("   - Compare with baseline metrics if available\n")
        f.write("   - Implement recommended optimizations\n\n")
        
        # Add baseline comparison if available
        f.write("## Baseline Comparison\n\n")
        baseline_metrics = self.load_baseline_metrics()
        if baseline_metrics:
            f.write("### Performance Changes from Baseline\n\n")
            # Add detailed baseline comparison here
            f.write("| Metric | Current | Baseline | Change | Status |\n")
            f.write("|--------|---------|----------|--------|--------|\n")
            # This would be populated with actual comparison data
            f.write("*Detailed baseline comparison data would appear here*\n\n")
        else:
            f.write("No baseline metrics available for comparison.\n")
            f.write("To establish baseline metrics, save the current test results as baseline for future comparisons.\n\n")
        
        # Test configuration appendix
        f.write("## Test Configuration Details\n\n")
        f.write("```json\n")
        f.write(json.dumps(dict(self.bench_config), indent=2))
        f.write("\n```\n\n")
        
        f.write("---\n")
        f.write("*Report generated by MindsDB Knowledge Base Test Suite*\n")

    def save_report(self):
        """Save test report as markdown file"""
        output_path = Path(self.bench_config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_report_{timestamp}.md"
        filepath = output_path / filename
        
        with open(filepath, 'w') as f:
            self._write_benchmark_report(f)
                
        console.print(f"[green]📊 Benchmark report saved to: {filepath}[/green]")