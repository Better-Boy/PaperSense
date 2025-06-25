from .base import MindsDBKnowledgeBaseTest
from typing import List, Dict, Any

import psutil
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich import box
from datetime import datetime
from .. import config_loader as config

console = Console()

class StressTest(MindsDBKnowledgeBaseTest):

    def __init__(self):
        super().__init__()
        self.stress_config = config.stress_test
        self.results = {
            'test_start_time': datetime.now().isoformat(),
            'data_volume_stress': {},
            'concurrent_user_stress': {},
            'failure_points': []
        }

    def start(self, files_data: List[Dict[str, Any]], queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run stress tests to find system limits"""

        console.print(Panel("[bold red]Starting Stress Tests[/bold red]", box=box.DOUBLE))

        if not self.create_knowledge_base():
            console.print("Knowledge Base creation failed")
            return
        
        # Data volume stress test
        console.print("\n[bold yellow]--- Data Volume Stress Test ---[/bold yellow]")

        for size in self.stress_config.data_sizes:
            if size > len(files_data):
                # Duplicate data to reach target size
                stress_data = (files_data * (size // len(files_data) + 1))[:size]
            else:
                stress_data = files_data[:size]
                
            try:
                console.print(f"[blue]Testing with {size:,} records[/blue]")
                ingestion_result = self.ingest_data(stress_data, batch_size=self.stress_config.batch_size)
                self.results['data_volume_stress'][size] = ingestion_result
                
                if ingestion_result['chunks_per_second'] < 10:  # Threshold for acceptable performance
                    self.results['failure_points'].append({
                        'test_type': 'data_volume',
                        'failure_point': size,
                        'reason': 'Performance degradation below 10 chunks/second'
                    })
                    console.print(f"[red]⚠️  Performance degradation detected at {size:,} records[/red]")
                    break
                    
            except Exception as e:
                self.results['failure_points'].append({
                    'test_type': 'data_volume',
                    'failure_point': size,
                    'reason': f'Exception: {str(e)}'
                })
                console.print(f"[red]❌ Failed at {size:,} records: {str(e)}[/red]")
                break
                
        # Concurrent user stress test
        console.print("\n[bold yellow]--- Concurrent User Stress Test ---[/bold yellow]")
        for user_count in self.stress_config.concurrent_users:
            if user_count > self.stress_config.max_concurrent_users:
                break
                
            try:
                console.print(f"[blue]Testing with {user_count} concurrent users[/blue]")
                concurrent_exec_result = self.run_concurrent_queries(queries, user_count)  # Use subset of queries
                self.results['concurrent_user_stress'][user_count] = concurrent_exec_result
                
                # Check for failure conditions
                if concurrent_exec_result['avg_latency_ms'] > 5000 or concurrent_exec_result['successful_queries'] < len(queries) * user_count * 0.95:
                    self.results['failure_points'].append({
                        'test_type': 'concurrent_users',
                        'failure_point': user_count,
                        'reason': 'High latency or low success rate'
                    })
                    console.print(f"[red]⚠️  Performance issues detected with {user_count} users[/red]")
                    break
                    
            except Exception as e:
                self.results['failure_points'].append({
                    'test_type': 'concurrent_users',
                    'failure_point': user_count,
                    'reason': f'Exception: {str(e)}'
                })
                console.print(f"[red]❌ Failed with {user_count} users: {str(e)}[/red]")
                break
                
        self.results['test_end_time'] = datetime.now().isoformat()
        self.cleanup_knowledge_base()

    def _write_stress_report(self, f):
        """Write stress test report in markdown format"""
        f.write("# MindsDB Knowledge Base Stress Test Report\n\n")
        f.write(f"**Test Date**: {self.results.get('test_start_time', 'Unknown')}\n")
        f.write(f"**Knowledge Base**: {self.kb_name}\n")
        f.write(f"**Test Duration**: {self.results.get('test_start_time', '')} - {self.results.get('test_end_time', '')}\n\n")
        
        # Test Environment
        f.write("## Test Environment\n\n")
        f.write("- **MindsDB Version**: 25.6.3.1\n")
        f.write(f"- **System**: {psutil.cpu_count()} CPU cores, {psutil.virtual_memory().total / (1024**3):.1f} GB RAM\n")
        f.write(f"- **Max Concurrent Users**: {self.stress_config.max_concurrent_users}\n")
        f.write(f"- **Max Data Size**: {self.stress_config.max_data_size} records\n\n")
        
        # Executive Summary
        f.write("## Executive Summary\n\n")
        
        failure_points = self.results.get('failure_points', [])
        if failure_points:
            f.write("### System Limitations Identified\n\n")
            for failure in failure_points:
                f.write(f"- **{failure['test_type'].replace('_', ' ').title()}**: Failed at {failure['failure_point']} - {failure['reason']}\n")
        else:
            f.write("- **System Stability**: All stress tests completed successfully within configured limits\n")
        
        f.write("\n")
        
        # Data Volume Stress Test
        f.write("## Data Volume Stress Test\n\n")
        f.write("This test evaluates system performance as data volume increases.\n\n")
        
        if 'data_volume_stress' in self.results:
            f.write("### Volume Test Results\n\n")
            f.write("| Data Size | Ingestion Time (s) | Throughput (chunks/s) | Memory Usage (MB) | Status | Batch Size |\n")
            f.write("|-----------|--------------------|-----------------------|-------------------|--------|------------|\n")
            
            for size, test_results in self.results['data_volume_stress'].items():
                ingestion_time = test_results.get('total_ingestion_time_s', 0)
                throughput = test_results.get('chunks_per_second', 0)
                memory_usage = test_results.get('system_metrics', {}).get('peak_memory_mb', 0)
                status = "✅ Pass" if test_results.get('total_errors', 0) == 0 else "❌ Fail"
                
                f.write(f"| {size:,} | {ingestion_time:.2f} | {throughput:.2f} | {memory_usage:.2f} | {status} | 50 |\n")
            
            f.write("\n### Volume Analysis\n\n")
            
            # Find performance degradation points
            throughputs = [(size, self.results['data_volume_stress'][size].get('chunks_per_second', 0)) 
                          for size in sorted(self.results['data_volume_stress'].keys())]
            
            if len(throughputs) > 1:
                baseline_throughput = throughputs[0][1]
                for size, throughput in throughputs[1:]:
                    if baseline_throughput > 0:
                        degradation = ((baseline_throughput - throughput) / baseline_throughput) * 100
                        if degradation > 20:
                            f.write(f"- **Performance Degradation**: {degradation:.1f}% decrease in throughput at {size:,} records\n")
                            break
        
        # Concurrent User Stress Test
        f.write("\n## Concurrent User Stress Test\n\n")
        f.write("This test evaluates system performance under increasing concurrent load.\n\n")
        
        if 'concurrent_user_stress' in self.results:
            f.write("### Concurrent Load Results\n\n")
            f.write("| Concurrent Users | Throughput (QPS) | Avg Latency (ms) | Success Rate (%) | Status |\n")
            f.write("|------------------|------------------|-------------------|------------------|--------|\n")
            
            for users, test_results in self.results['concurrent_user_stress'].items():
                throughput = test_results.get('throughput_qps', 0)
                avg_latency = test_results.get('avg_latency_ms', 0)
                success_rate = (test_results.get('successful_queries', 0) / test_results.get('total_queries', 1)) * 100
                status = "✅ Pass" if success_rate > 95 and avg_latency < 5000 else "❌ Fail"
                
                f.write(f"| {users} | {throughput:.2f} | {avg_latency:.2f} | {success_rate:.1f} | {status} |\n")
            
            f.write("\n### Concurrency Analysis\n\n")
            
            # Find saturation point
            results_list = [(users, self.results['concurrent_user_stress'][users]) 
                           for users in sorted(self.results['concurrent_user_stress'].keys())]
            
            if len(results_list) > 1:
                for i, (users, test_results) in enumerate(results_list[1:], 1):
                    prev_throughput = results_list[i-1][1].get('throughput_qps', 0)
                    curr_throughput = test_results.get('throughput_qps', 0)
                    
                    if prev_throughput > 0:
                        throughput_increase = ((curr_throughput - prev_throughput) / prev_throughput) * 100
                        if throughput_increase < 10:  # Less than 10% improvement
                            f.write(f"- **Saturation Point**: System reaches saturation around {users} concurrent users\n")
                            break
    
    def save_report(self):
        """Save test report as markdown file"""
        output_path = Path(config.stress_test.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stress_report_{timestamp}.md"
        filepath = output_path / filename
        
        with open(filepath, 'w') as f:
            self._write_stress_report(f)
                
        console.print(f"[green]📊 Stress report saved to: {filepath}[/green]")