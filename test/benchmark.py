from dataclasses import dataclass
from datetime import datetime
import os
import platform
import statistics
import time
from typing import Any, Dict, List, Optional

import numpy as np
import psutil
import requests
import sys
from models import BenchmarkConfig, TestConfig
from plot import Plot
from utils import build_create_kb_query, load_ingestion_data, load_search_queries, row_count_kb, start_resource_monitor_process, test_env_info, validate_pid

@dataclass
class BenchmarkResult:
    """Single benchmark result"""
    kb_func: str
    response_time: float
    status_code: int
    success: bool
    timestamp: int
    error_message: Optional[str] = None

class KnowledgeBaseBenchmarkTest:
    def __init__(self, config: BenchmarkConfig, host: str):
        self.results: Dict[str, List[BenchmarkResult]] = {
            "create": [],
            "insert": [],
            "search": [],
            "delete": []
        }
        self.config = config
        self.host = host
        self.url = host + "/api/sql/query"
        self.session = requests.Session()
        
    def send_request(self, query: str, kb_func: str) -> None:
        """Benchmark a single endpoint call"""
        start_time = time.time()
        
        
        try:
            payload = {'query': query, 'context': {'db': 'mindsdb'}}
                       
            response = self.session.post(
                    self.url,
                    json=payload,
                    timeout=20
            )
            
            response_time = time.time() - start_time
            res = response.json()
            if res["type"] == "error":
                raise Exception(response.text)
            
            success = 200 <= response.status_code < 300
            
            return BenchmarkResult(
                kb_func=kb_func,
                response_time=response_time,
                status_code=response.status_code,
                success=success,
                timestamp=time.time()
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return BenchmarkResult(
                kb_func=kb_func,
                response_time=response_time,
                status_code=response.status_code,
                success=False,
                timestamp=time.time(),
                error_message=str(e)
            )

    def run_benchmark_cycle(self, insert_queries: List[Dict[str, Any]], 
                          search_queries: List[Dict[str, Any]]) -> None:
        """Run a complete benchmark cycle: setup -> insert -> search -> delete"""
        
        # 1. Setup
        print("🔧 Running knowledge base setup...")
        create_kb_query = build_create_kb_query()
        create_result = self.send_request(create_kb_query, 'create')
        self.results.get("create").append(create_result)
        
        if not create_result.success:
            print(f"❌ Knowledge base Setup failed: {create_result.status_code}")
            return create_result
        
        # 2. Insert records
        print(f"📝 Inserting {len(insert_queries)} records...")
        for i, query in enumerate(insert_queries):
            insert_result = self.send_request(query, 'insert')
            self.results.get("insert").append(insert_result)
            
            if not insert_result.success:
                print(f"❌ Insert failed for record {i+1}: {insert_result.status_code}")
            
            if i % 25 == 0:
                print(f"Insert index at {i}")
        
        # 3. Search records
        # search_queries = search_queries[:15]
        print(f"🔍 Running {len(search_queries)} search queries...")
        for i, query in enumerate(search_queries):
            search_result = self.send_request(query, 'search')
            self.results.get("search").append(search_result)
            
            if not search_result.success:
                print(f"❌ Search failed for query {i+1}: {search_result.status_code}")
            
            if i % 10 == 0:
                print(f"Search index at {i}")
            time.sleep(0.1)
        
        # 4. Delete knowledge base
        print("🗑️ Cleaning up knowledge base...")
        drop_kb_query = "DROP KNOWLEDGE_BASE arxiv_test_kb"
        delete_result = self.send_request(drop_kb_query, 'delete')
        self.results.get("delete").append(search_result)
        
        if not delete_result.success:
            print(f"❌ Delete failed: {delete_result.status_code}")

    def run_benchmark(self) -> None:
        """Run the complete benchmark suite"""
        print(f"🚀 Starting API benchmark with {self.config.iterations} iterations")
        print(f"📊 Insert data: {self.config.test_data_path}")
        print(f"🔎 Search data: {self.config.queries_file_path}")
        
        # Load data files
        try:
            insert_queries, data_size_mb = load_ingestion_data(self.config.test_data_path, self.config.data_size)
            search_queries = [f"SELECT * from arxiv_test_kb where content = '{q["query"]}';" for q in load_search_queries(self.config.queries_file_path)]
        except Exception as e:
            print(f"❌ Failed to load data files: {e}")
            return
        
        print(f"📋 Loaded {len(insert_queries)} insert records and {len(search_queries)} search queries")
        
        # Run benchmark iterations
        for iteration in range(1, self.config.iterations + 1):
            print(f"\n🔄 Iteration {iteration}/{self.config.iterations}")
            self.run_benchmark_cycle(insert_queries=insert_queries, search_queries=search_queries)
            
            # Progress update
            print(f"✅ Completed iteration {iteration}")
            
            # Brief pause between iterations
            if iteration < self.config.iterations:
                time.sleep(1)
        
        print(f"\n🎉 Benchmark completed! Processed {len(self.results)} total requests")

    def generate_statistics(self) -> Dict[str, Any]:
        """Generate comprehensive statistics from benchmark results"""
        if not self.results:
            return {}
        
        total_requests = sum(len(res) for res in self.results.values())
        
        stats = {
            'summary': {
                'total_requests': total_requests,
                'successful_requests': sum(1 for v in self.results.values() for r in v if r.success),
                'failed_requests': sum(1 for v in self.results.values() for r in v if not r.success),
                'overall_success_rate': (sum(1 for v in self.results.values() for r in v if r.success) / total_requests) * 100,
                'total_duration': sum(r.response_time for v in self.results.values() for r in v),
                'benchmark_start': datetime.fromtimestamp(min(r.timestamp for v in self.results.values() for r in v)),
                'benchmark_end': datetime.fromtimestamp(max(r.timestamp for v in self.results.values() for r in v))
            }
        }
        
        stats["detailed"] = {}

        for kb_func_op, results in self.results.items():
            successful_results = [r for r in results if r.success]
            response_times = [r.response_time for r in successful_results]
            
            if successful_results:
                kb_func_op_stats = {
                    'total_requests': len(results),
                    'successful_requests': len(successful_results),
                    'success_rate': (len(successful_results) / len(results)) * 100,
                    'avg_response_time': statistics.mean(response_times),
                    'median_response_time': statistics.median(response_times),
                    'min_response_time': min(response_times),
                    'max_response_time': max(response_times),
                    'std_dev_response_time': statistics.stdev(response_times) if len(response_times) > 1 else 0,
                    'p95_response_time': np.percentile(response_times, 95) if response_times else 0,
                    'p99_response_time': np.percentile(response_times, 99) if response_times else 0,
                    'errors': [{'status_code': r.status_code, 'message': r.error_message} for r in results if not r.success]
                }
            else:
                kb_func_op_stats = {
                    'total_requests': len(results),
                    'successful_requests': 0,
                    'success_rate': 0,
                    'errors': [{'status_code': r.status_code, 'message': r.error_message} for r in results]
                }
            
            stats["detailed"][kb_func_op] = kb_func_op_stats
        
        return stats

    def generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations based on benchmark results"""
        recommendations = []
        
        if not stats or 'detailed' not in stats:
            return ["❌ No data available for recommendations"]
        
        # Overall performance recommendations
        overall_success_rate = stats['summary']['overall_success_rate']
        if overall_success_rate < 95:
            recommendations.append(
                f"🚨 Overall success rate is {overall_success_rate:.1f}%. "
                "Consider improving error handling and retry mechanisms."
            )
        
        # Per-endpoint recommendations
        for endpoint_name, endpoint_stats in stats['detailed'].items():
            if endpoint_stats['success_rate'] < 100:
                recommendations.append(
                    f"⚠️ {endpoint_name} has {endpoint_stats['success_rate']:.1f}% success rate. "
                    "Investigate error causes and improve reliability."
                )
            
            if 'avg_response_time' in endpoint_stats:
                avg_time = endpoint_stats['avg_response_time']
                
                if avg_time > 5.0:
                    recommendations.append(
                        f"🐌 {endpoint_name} has high average response time ({avg_time:.2f}s). "
                        "Consider optimizing database queries, adding caching, or scaling resources."
                    )
                elif avg_time > 2.0:
                    recommendations.append(
                        f"⏰ {endpoint_name} response time ({avg_time:.2f}s) could be improved. "
                        "Consider adding database indexes or optimizing business logic."
                    )
                
                # Check for high variability
                if 'std_dev_response_time' in endpoint_stats:
                    std_dev = endpoint_stats['std_dev_response_time']
                    if std_dev > avg_time * 0.5:
                        recommendations.append(
                            f"📊 {endpoint_name} has high response time variability (σ={std_dev:.2f}s). "
                            "This indicates inconsistent performance - investigate resource contention."
                        )
        
        # Resource utilization recommendations
        insert_stats = stats['detailed'].get('insert', {})
        if insert_stats and 'avg_response_time' in insert_stats:
            insert_time = insert_stats['avg_response_time']
            if insert_time > 1.0:
                recommendations.append(
                    "💾 Consider implementing batch insert operations to improve throughput."
                )
        
        search_stats = stats['detailed'].get('search', {})
        if search_stats and 'avg_response_time' in search_stats:
            search_time = search_stats['avg_response_time']
            if search_time > 0.5:
                recommendations.append(
                    "🔍 Search performance could benefit from better indexing or search optimization."
                )
        
        # General recommendations
        if not recommendations:
            recommendations.append("✅ All endpoints are performing well! Consider load testing with higher concurrency.")
        else:
            recommendations.append("🔧 Implement monitoring and alerting for these performance metrics in production.")
        
        return recommendations
    
    def _generate_markdown_report(self, stats: Dict[str, Any], recommendations: List[str]) -> str:
        """Generate comprehensive markdown report"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        summary = stats['summary']
        
        md = f"""# MindsDB Knowledge Base Benchmark Report

**Generated on:** {timestamp}  
**Total Test Duration:** {summary['total_duration']:.2f} seconds  
**Report Type:** Knowledge Base API Performance Analysis

---

## Executive Summary

### 📊 Key Performance Indicators

| Metric | Value | Status |
|--------|-------|--------|
| **Total Requests** | {summary['total_requests']:,} | ✅ |
| **Success Rate** | {summary['overall_success_rate']:.1f}% | {'✅' if summary['overall_success_rate'] >= 95 else '⚠️' if summary['overall_success_rate'] >= 90 else '❌'} |
| **Successful Requests** | {summary['successful_requests']:,} | - |
| **Failed Requests** | {summary['failed_requests']:,} | {'✅' if summary['failed_requests'] == 0 else '⚠️'} |
| **Average Response Time** | {(summary['total_duration'] / summary['total_requests']):.3f}s | {'✅' if (summary['total_duration'] / summary['total_requests']) < 1.0 else '⚠️'} |

### 🎯 Overall Assessment

"""
        
        # Overall assessment based on metrics
        overall_success_rate = summary['overall_success_rate']
        avg_response_time = summary['total_duration'] / summary['total_requests']
        
        if overall_success_rate >= 98 and avg_response_time < 0.5:
            md += "**🟢 EXCELLENT** - All endpoints are performing exceptionally well with high reliability and fast response times.\n\n"
        elif overall_success_rate >= 95 and avg_response_time < 1.0:
            md += "**🟡 GOOD** - Endpoints are performing well with good reliability, but there's room for optimization.\n\n"
        elif overall_success_rate >= 90 and avg_response_time < 2.0:
            md += "**🟠 FAIR** - Performance is acceptable but requires attention to improve reliability and response times.\n\n"
        else:
            md += "**🔴 POOR** - Significant performance issues detected. Immediate optimization required.\n\n"
        
        # Quick insights
        md += "### 🔍 Quick Insights\n\n"
        endpoint_performances = []
        for endpoint_name, endpoint_stats in stats['detailed'].items():
            if 'avg_response_time' in endpoint_stats:
                endpoint_performances.append((endpoint_name, endpoint_stats['avg_response_time'], endpoint_stats['success_rate']))
        
        if endpoint_performances:
            fastest_endpoint = min(endpoint_performances, key=lambda x: x[1])
            slowest_endpoint = max(endpoint_performances, key=lambda x: x[1])
            most_reliable = max(endpoint_performances, key=lambda x: x[2])
            
            md += f"- **Fastest Knowledge Base Operation:** {fastest_endpoint[0]} ({fastest_endpoint[1]:.3f}s avg)\n"
            md += f"- **Slowest Knowledge Base Operation:** {slowest_endpoint[0]} ({slowest_endpoint[1]:.3f}s avg)\n"
            md += f"- **Most Reliable:** {most_reliable[0]} ({most_reliable[2]:.1f}% success rate)\n\n"
            md += f"- **Row count in Knowledge Base:** {row_count_kb(self.host)}\n\n"
        # Test environment info
        md += f"""### 📋 Test Configuration

- **Test Period:** {summary['benchmark_start']} to {summary['benchmark_end']}
- **Knowledge Base Functionalities tested:** create, insert, search, delete
- **Test Methodology:** Sequential execution (setup → insert → search → delete)

---
## Test Environment

{test_env_info()}

---
## Detailed Analysis

"""
        
        # Detailed analysis for each endpoint
        for endpoint_name, endpoint_stats in stats['detailed'].items():
            md += f"### 🔧 {endpoint_name.title()} Operation\n\n"
            
            # Status badge
            success_rate = endpoint_stats['success_rate']
            if success_rate == 100:
                status_badge = "🟢 EXCELLENT"
            elif success_rate >= 95:
                status_badge = "🟡 GOOD"
            elif success_rate >= 90:
                status_badge = "🟠 FAIR"
            else:
                status_badge = "🔴 POOR"
            
            md += f"**Performance Status:** {status_badge}\n\n"
            
            # Core metrics table
            md += "#### 📈 Core Metrics\n\n"
            md += "| Metric | Value |\n|--------|-------|\n"
            md += f"| Total Requests | {endpoint_stats['total_requests']:,} |\n"
            md += f"| Successful Requests | {endpoint_stats['successful_requests']:,} |\n"
            md += f"| Success Rate | {endpoint_stats['success_rate']:.2f}% |\n"
            
            if 'avg_response_time' in endpoint_stats:
                md += f"| Average Response Time | {endpoint_stats['avg_response_time']:.3f}s |\n"
                md += f"| Median Response Time | {endpoint_stats['median_response_time']:.3f}s |\n"
                md += f"| Minimum Response Time | {endpoint_stats['min_response_time']:.3f}s |\n"
                md += f"| Maximum Response Time | {endpoint_stats['max_response_time']:.3f}s |\n"
                md += f"| Standard Deviation | {endpoint_stats['std_dev_response_time']:.3f}s |\n"
                md += f"| 95th Percentile | {endpoint_stats['p95_response_time']:.3f}s |\n"
                md += f"| 99th Percentile | {endpoint_stats['p99_response_time']:.3f}s |\n"
            
            md += "\n"
            
            # Performance analysis
            if 'avg_response_time' in endpoint_stats:
                md += "#### 🎯 Performance Analysis\n\n"
                
                avg_time = endpoint_stats['avg_response_time']
                std_dev = endpoint_stats['std_dev_response_time']
                p95_time = endpoint_stats['p95_response_time']
                
                # Response time analysis
                if avg_time < 0.1:
                    md += "- **Response Time:** ✅ Excellent - Very fast response times\n"
                elif avg_time < 0.5:
                    md += "- **Response Time:** ✅ Good - Fast response times\n"
                elif avg_time < 1.0:
                    md += "- **Response Time:** ⚠️ Fair - Acceptable response times\n"
                elif avg_time < 2.0:
                    md += "- **Response Time:** ⚠️ Slow - Response times need improvement\n"
                else:
                    md += "- **Response Time:** ❌ Poor - Very slow response times\n"
                
                # Consistency analysis
                cv = (std_dev / avg_time) * 100 if avg_time > 0 else 0
                if cv < 20:
                    md += "- **Consistency:** ✅ Very consistent performance\n"
                elif cv < 50:
                    md += "- **Consistency:** ⚠️ Moderately consistent performance\n"
                else:
                    md += "- **Consistency:** ❌ Inconsistent performance - high variability\n"
                
                # Tail latency analysis
                if p95_time <= avg_time * 2:
                    md += "- **Tail Latency:** ✅ Good - 95th percentile within expected range\n"
                elif p95_time <= avg_time * 3:
                    md += "- **Tail Latency:** ⚠️ Fair - Some requests experience delays\n"
                else:
                    md += "- **Tail Latency:** ❌ Poor - Significant tail latency issues\n"
                
                md += "\n"
            
            # Error analysis
            if endpoint_stats.get('errors'):
                md += "#### ⚠️ Error Analysis\n\n"
                error_counts = {}
                for error in endpoint_stats['errors']:
                    status_code = error['status_code']
                    if status_code in error_counts:
                        error_counts[status_code] += 1
                    else:
                        error_counts[status_code] = 1
                
                md += "| Status Code | Count | Description |\n|-------------|-------|-------------|\n"
                for status_code, count in sorted(error_counts.items()):
                    description = {
                        400: "Bad Request",
                        401: "Unauthorized", 
                        403: "Forbidden",
                        404: "Not Found",
                        500: "Internal Server Error",
                        502: "Bad Gateway",
                        503: "Service Unavailable",
                        504: "Gateway Timeout",
                        0: "Connection/Network Error"
                    }.get(status_code, "Unknown Error")
                    
                    md += f"| {status_code} | {count} | {description} |\n"
                
                md += "\n"
                
                # Show sample error messages
                unique_errors = list(set(error['message'] for error in endpoint_stats['errors'] if error['message']))[:3]
                if unique_errors:
                    md += "**Sample Error Messages:**\n\n"
                    for i, error_msg in enumerate(unique_errors, 1):
                        md += f"{i}. `{error_msg[:100]}{'...' if len(error_msg) > 100 else ''}`\n"
                    md += "\n"
            
            # Recommendations for this endpoint
            endpoint_recs = [rec for rec in recommendations if endpoint_name in rec]
            if endpoint_recs:
                md += "#### 💡 Specific Recommendations\n\n"
                for rec in endpoint_recs:
                    md += f"- {rec}\n"
                md += "\n"
            
            md += "---\n\n"
        
        md += "## Resource usage analysis\n"
        md += Plot().generate_resource_usage_md(self.config.output_dir)
        md += "---\n\n"

        # Overall recommendations
        md += "## 💡 Optimization Recommendations\n\n"
        md += "### 🚀 Priority Actions\n\n"
        
        high_priority = []
        medium_priority = []
        low_priority = []
        
        for rec in recommendations:
            if "🚨" in rec or "❌" in rec:
                high_priority.append(rec)
            elif "⚠️" in rec or "🐌" in rec or "⏰" in rec:
                medium_priority.append(rec)
            else:
                low_priority.append(rec)
        
        if high_priority:
            md += "#### 🔴 High Priority\n\n"
            for i, rec in enumerate(high_priority, 1):
                md += f"{i}. {rec}\n"
            md += "\n"
        
        if medium_priority:
            md += "#### 🟡 Medium Priority\n\n"
            for i, rec in enumerate(medium_priority, 1):
                md += f"{i}. {rec}\n"
            md += "\n"
        
        if low_priority:
            md += "#### 🟢 Low Priority\n\n"
            for i, rec in enumerate(low_priority, 1):
                md += f"{i}. {rec}\n"
            md += "\n"

        
        # Technical appendix
        md += """---

## 📊 Technical Appendix

### Methodology

This benchmark follows a sequential testing approach:
1. **Setup Phase:** Initialize knowledge base
2. **Insert Phase:** Add records to the knowledge base
3. **Search Phase:** Query the knowledge base
4. **Cleanup Phase:** Delete the knowledge base

In order to run the benchmarking script, refer `benchmark.md` file found in the `reports` folder of the repo https://github.com/Better-Boy/PaperSense.

### Metrics Definitions

- **Response Time:** Time from request initiation to response completion
- **Success Rate:** Percentage of requests returning 2xx HTTP status codes
- **P95/P99:** 95th and 99th percentile response times (tail latency)
- **Standard Deviation:** Measure of response time variability
- **Throughput:** Requests processed per unit time

### Performance Thresholds

- **Excellent:** < 100ms average response time, > 99% success rate
- **Good:** < 500ms average response time, > 95% success rate  
- **Fair:** < 1000ms average response time, > 90% success rate
- **Poor:** > 1000ms average response time or < 90% success rate

---

*Report generated by API Benchmark Tool*
"""
        
        return md
    
    def test_env_info(self):
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
        md += "\n### Hardware Specs\n"
        for key, value in hardware.items():
            md += f"- **{key}**: {value}\n"

        return md

    def save_detailed_report(self) -> None:
        """Save detailed benchmark report to file"""
        
        stats = self.generate_statistics()
        recommendations = self.generate_recommendations(stats)
        
        report_str = self._generate_markdown_report(stats=stats, recommendations=recommendations)
        report_filename = f"benchmark_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        if self.config.output_dir.endswith("/"):
            self.config.output_dir = self.config.output_dir[:-1]

        os.makedirs(self.config.output_dir, exist_ok=True)

        report_file_path = f"{self.config.output_dir}/{report_filename}"

        with open(report_file_path, 'w') as f:
            f.write(report_str)
        
        print(f"📊 Detailed report saved to: {report_file_path}")

def main():
    app_config = TestConfig.from_yaml("test/config.yaml")
    validate_pid(app_config.mindsdb_infra.mindsdb_pid)

    if app_config.mindsdb_infra.host.endswith("/"):
        app_config.mindsdb_infra.host = app_config.mindsdb_infra.host[:-1]

    host = f"{app_config.mindsdb_infra.host}:{app_config.mindsdb_infra.port}"
    test_config = app_config.benchmark
    
    try:
        ps_record_process = start_resource_monitor_process(app_config.mindsdb_infra.mindsdb_pid, test_config.output_dir)
        
        time.sleep(1)
        # Initialize benchmarker
        benchmarker = KnowledgeBaseBenchmarkTest(test_config, host)
        
        # Run benchmark
        benchmarker.run_benchmark()
        
        time.sleep(1)
        ps_record_process.terminate()
        ps_record_process.wait()
        time.sleep(1)
        benchmarker.save_detailed_report()

    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()