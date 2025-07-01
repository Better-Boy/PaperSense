from itertools import cycle
import sys
from datetime import datetime
from typing import Any
import gevent
from locust import HttpUser, between, task
from locust.env import Environment
from locust.stats import stats_history, stats_printer
from locust.log import setup_logging

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich import box

from models import StressConfig, TestConfig
from plot import Plot
from utils import *

# Global variables for test configuration
search_queries_cycle = None
records_cycle = None
console = Console()

class KBTestUser(HttpUser):
    weight = 1
    wait_time = between(1, 5)
    
    @task(3)
    def ingest_data(self):
        """Ingest data"""
        
        insert_query = next(records_cycle)
        
        with self.client.post(
            "/api/sql/query",
            json={'query': insert_query, 'context': {'db': 'mindsdb'}},
            catch_response=True,
            timeout=30,
            name="ingest"
        ) as response:
            if response.status_code == 200:
                res = response.json()
                if res["type"] == "error":
                    response.failure(f"Ingestion failed: {response.status_code}, response_text: {response.text}")
                else: response.success()
            else:
                response.failure(f"Ingestion failed: {response.status_code}, response_text: {response.text}")
    
    @task(2)
    def search(self):
        """Perform simple search operations"""
        
        query = next(search_queries_cycle)
        select_query = f"SELECT * from arxiv_test_kb where content = '{query}';"
        
        with self.client.post(
            "/api/sql/query",
            json={'query': select_query, 'context': {'db': 'mindsdb'}},
            catch_response=True,
            timeout=30,
            name="search"
        ) as response:
            if response.status_code == 200:
                res = response.json()
                if res["type"] == "error":
                    response.failure(f"Search failed: {response.status_code}, response_text: {response.text}")
                else: response.success()
            else:
                response.failure(f"Search failed: {response.status_code}, response_text: {response.text}")


class Report:
    
    def generate_stress_report(self, stats, test_config: StressConfig, info: Dict[str, Any]):

        report_filename = f"stress_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_file_path = f"{test_config.output_dir}/{report_filename}"

        info["test_duration"] = (info["end_time"] - info["start_time"]).total_seconds()
        
        # Get aggregated stats
        total_stats = stats.total

        # Separate ingestion and search stats
        entries_dict = dict(stats.entries.items())
        ingestion_stats = entries_dict[("ingest", "POST")] if ("ingest", "POST") in entries_dict else None
        search_stats = entries_dict[("search", "POST")] if ("search", "POST") in entries_dict else None

        report_sections = [
            self._generate_header(),
            self._generate_test_config(test_config=test_config, info=info),
            self._generate_test_environment(),
            self._generate_executive_summary(total_stats, ingestion_stats, search_stats, info),
            self._generate_detailed_metrics(ingestion_stats, search_stats, test_config.output_dir),
            self._generate_response_time_analysis(ingestion_stats, search_stats),
            self._generate_recommendations(ingestion_stats, search_stats, total_stats, info["test_duration"]),
            self._generate_test_metadata(total_stats, test_config.concurrent_users),
            self._generate_footer()
        ]

        report_content = "\n\n".join(filter(None, report_sections))
        report_content = self._clean_indentation(report_content)
        
        # Write to file
        self._write_report_file(report_file_path, report_content)
        
        print(f"✓ Stress test report generated: {report_file_path}")

    def _clean_indentation(self, content: str) -> str:
        """Remove leading whitespace from each line while preserving relative indentation."""
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove leading spaces but preserve markdown formatting
            stripped = line.lstrip()
            cleaned_lines.append(stripped)
        
        return '\n'.join(cleaned_lines)

    def _write_report_file(self, filename: str, content: str) -> None:
        """Write report content to file with error handling."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
        except IOError as e:
            print(f"Error writing report file {filename}: {e}")
            raise

    
    def _generate_footer(self) -> str:
        """Generate report footer."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return f"""---
    *Report generated on {timestamp}*  
    *Test Generated By: Big-Bounty*"""

    def _generate_test_metadata(self, total_stats, concurrent_users: int) -> str:
        """Generate test validity and limitations section."""
        return f"""## Test Validity and Limitations
    - Test executed under controlled conditions with {concurrent_users} concurrent users
    - Results may vary with different data patterns and real-world usage scenarios
    - Network latency simulated through HTTP requests
    - Knowledge Base performance depends on hardware configuration and system resources
    - Test data consists of research papers which may not represent all use cases

    ## Conclusion
    {self.generate_conclusion(total_stats=total_stats)}

    ## Testing Process and Methodology
    {self.generate_test_methodology()}"""

    
    def _generate_recommendations(self, ingestion_stats, search_stats, total_stats, 
                             test_duration: float) -> str:
        """Generate performance recommendations section."""
        return f"""## Performance Recommendations

    ### Ingestion Optimization
    {self.generate_ingestion_recommendations(ingestion_stats)}

    ### Search Optimization
    {self.generate_search_recommendations(search_stats)}

    ## System Resource Implications

    ### Capacity Analysis
    {self.generate_capacity_analysis(ingestion_stats, search_stats, test_duration)}

    ### Scaling Recommendations
    {self.generate_scaling_recommendations(total_stats)}"""

    def _generate_response_time_analysis(self, ingestion_stats, search_stats) -> str:
        """Generate response time distribution analysis."""
        return f"""## Response Time Distribution

    ### Ingestion Response Times
    {self.generate_response_time_table(ingestion_stats, "Ingestion")}

    ### Search Response Times
    {self.generate_response_time_table(search_stats, "Search")}"""


    def _generate_detailed_metrics(self, ingestion_stats, search_stats, output_dir: str) -> str:
        """Generate detailed performance metrics section."""
        return f"""## Detailed Performance Metrics

    ### Ingestion Endpoint Analysis
    {self.generate_ingestion_details(ingestion_stats)}

    ### Search Endpoint Analysis
    {self.generate_ingestion_details(search_stats)}

    ### MindsDB Process Resource Usage
    {Plot().generate_resource_usage_md(output_dir)}"""

        
    def _generate_executive_summary(self, total_stats, ingestion_stats, search_stats, info: Dict[str, Any]) -> str:
        """Generate executive summary section."""
        
        summary = f"""## Executive Summary

    ### Overall Performance
    - **Total Requests**: {total_stats.num_requests:,}
    - **Total Failures**: {total_stats.num_failures:,}
    - **Overall Success Rate**: {((total_stats.num_requests - total_stats.num_failures) / total_stats.num_requests * 100) if total_stats.num_requests > 0 else 0:.2f}%
    - **Average Response Time**: {total_stats.avg_response_time:.2f}ms
    - **Overall RPS**: {total_stats.total_rps:.2f} requests/second
    - **Knowledge Base Creation Time**: {info.get('kb_create', 0):.2f}s
    - **Knowledge Base Deletion Time**: {info.get('kb_create', 0):.2f}s
    - **Knowledge Base Row Count**: {info.get('kb_row_cnt', 0):,}
    - **Total Data Volume**: {info["data_size_mb"]:.2f} MB

    ### Ingestion Performance
    {self.generate_ingestion_summary(ingestion_stats, info["test_duration"])}

    ### Search Performance  
    {self.generate_search_summary(search_stats, info["test_duration"])}"""
        
        return summary
        
    def _generate_test_config(self, test_config: StressConfig, info: Dict[str, Any]) -> str:
        """Generate test configuration section."""
        
        return f"""## Test Configuration
    - **Test Date**: {info["start_time"].strftime('%Y-%m-%d %H:%M:%S')}
    - **Test Duration**: {info["test_duration"]:.2f} seconds
    - **Data Size**: {test_config.data_size:,} records (research papers)
    - **Concurrent Users**: {test_config.concurrent_users}
    - **Spawn Rate**: {test_config.spawn_rate} users/second
    - **Wait Time**: between 1s and 5s
    - **Target Host**: {info["host"]}
    - **Total Data Volume**: {info["data_size_mb"]:.2f} MB"""

    def _generate_header(self) -> str:
        """Generate report header."""
        return f"# MindsDB Knowledge Base Stress Test Report"

    def _generate_test_environment(self) -> str:
        """Generate test environment section."""
        return f"""## Test Environment
        {test_env_info()}"""


    def generate_test_methodology(self):
        return f"""
        This test adheres to a standardized methodology to ensure consistent and reproducible results.
        In order to run the stress script, refer `stress.md` file found in the `reports` folder of the repo https://github.com/Better-Boy/PaperSense.
    """

    def generate_ingestion_summary(self, ingestion_stats, test_duration):
        """Generate ingestion performance summary"""
        if not ingestion_stats:
            return "- **Status**: No ingestion data recorded"
        
        success_rate = ((ingestion_stats.num_requests - ingestion_stats.num_failures) / ingestion_stats.num_requests * 100) if ingestion_stats.num_requests > 0 else 0
        records_per_second = ingestion_stats.num_requests / test_duration if test_duration > 0 else 0
        
        return f"""- **Total Records (Papers) Processed**: {ingestion_stats.num_requests:,}
    - **Success Rate**: {success_rate:.2f}%
    - **Average Response Time**: {ingestion_stats.avg_response_time:.2f}ms
    - **Throughput (Records per Second)**: {records_per_second:.2f}
    """

    def generate_search_summary(self, search_stats, test_duration):
        """Generate search performance summary"""
        if not search_stats:
            return "- **Status**: No search data recorded"
        
        total_requests = search_stats.num_requests
        
        success_rate = ((total_requests - search_stats.num_failures) / total_requests * 100) if total_requests > 0 else 0
        queries_per_second = total_requests / test_duration if test_duration > 0 else 0
        
        return f"""- **Total Search Queries**: {total_requests:,}
    - **Success Rate**: {success_rate:.2f}%
    - **Average Response Time**: {search_stats.avg_response_time:.2f}ms
    - **Queries per Second**: {queries_per_second:.2f}"""

    def generate_ingestion_details(self, stats):
        """Generate detailed ingestion analysis"""
        if not stats:
            return "No ingestion statistics available."
        
        return f"""
    #### Key Metrics
    - **Total Requests**: {stats.num_requests:,}
    - **Failed Requests**: {stats.num_failures:,}
    - **Average Response Time**: {stats.avg_response_time:.2f}ms
    - **Minimum Response Time**: {stats.min_response_time:.2f}ms
    - **Maximum Response Time**: {stats.max_response_time:.2f}ms
    - **Requests per Second**: {stats.total_rps:.2f}
    - **Median Response Time**: {stats.median_response_time:.2f}ms

    #### Response Time Percentiles
    - **50th Percentile**: {stats.get_response_time_percentile(0.5):.2f}ms
    - **95th Percentile**: {stats.get_response_time_percentile(0.95):.2f}ms
    - **99th Percentile**: {stats.get_response_time_percentile(0.99):.2f}ms
    """

    def generate_response_time_table(self, stats, endpoint_name):
        """Generate response time distribution table"""
        if not stats:
            return f"No {endpoint_name.lower()} statistics available."
        
        return f"""
    | Metric | Value |
    |--------|-------|
    | Average | {stats.avg_response_time:.2f}ms |
    | Median | {stats.median_response_time:.2f}ms |
    | 95th Percentile | {stats.get_response_time_percentile(0.95):.2f}ms |
    | 99th Percentile | {stats.get_response_time_percentile(0.99):.2f}ms |
    | Min | {stats.min_response_time:.2f}ms |
    | Max | {stats.max_response_time:.2f}ms |
    """

    def generate_ingestion_recommendations(self, ingestion_stats):
        """Generate ingestion optimization recommendations"""
        if not ingestion_stats:
            return "- No ingestion data available for analysis"
        
        recommendations = []
        avg_response_time = ingestion_stats.avg_response_time
        p95_response_time = ingestion_stats.get_response_time_percentile(0.95)
        failure_rate = (ingestion_stats.num_failures / ingestion_stats.num_requests * 100) if ingestion_stats.num_requests > 0 else 0
        
        if avg_response_time > 2000:  # > 2 seconds
            recommendations.append("- **Critical**: Average response time is very high (>2s). Consider batching the input records")
            recommendations.append("- Implement asynchronous processing")
        elif avg_response_time > 1000:  # > 1 second
            recommendations.append("- **Warning**: Response times are elevated. Consider batch insertion")
            recommendations.append("- Review vector database indexing strategy")
        else:
            recommendations.append("- Response times are acceptable for scenario")
        
        if p95_response_time > avg_response_time * 2:
            recommendations.append("- High variance in response times detected. Investigate performance bottlenecks")
        
        if failure_rate > 5:
            recommendations.append(f"- **Critical**: High failure rate ({failure_rate:.1f}%). Implement retry logic and error handling")
        elif failure_rate > 1:
            recommendations.append(f"- **Warning**: Some failures detected ({failure_rate:.1f}%). Monitor error patterns")
        
        if not recommendations:
            recommendations.append("- Current ingestion performance is optimal")
        
        return "\n".join(recommendations)

    def generate_search_recommendations(self, search_stats):
        """Generate search optimization recommendations"""
        if not search_stats:
            return "- No search data available for analysis"
        
        recommendations = []
        
        failure_rate = (search_stats.num_failures / search_stats.num_requests * 100) if search_stats.num_requests > 0 else 0
        
        if search_stats.avg_response_time > 1000:
            recommendations.append(f"- **Performance**: Slow search detected")
            recommendations.append("- Add database indexes on frequently searched fields")
            recommendations.append("- Consider implementing search result caching")
        
        if failure_rate > 5:
            recommendations.append(f"- **Reliability**: High failure rates detected")
            recommendations.append("- Review knowledge base search and reranking strategies")
        
        if not recommendations:
            recommendations.append("- Current search performance is acceptable across all query types")
        
        return "\n".join(recommendations)

    def generate_capacity_analysis(self, ingestion_stats, search_stats, test_duration):
        """Generate capacity analysis"""
        analysis = []
        
        if ingestion_stats:
            records_per_second = ingestion_stats.num_requests / test_duration
            analysis.append(f"- **Ingestion Capacity**: ~{records_per_second:.0f} records/second")
            analysis.append(f"- **Peak Ingestion Rate**: ~{records_per_second * 60:.0f} records/minute")
        
        if search_stats:
            total_search_rps = search_stats.num_requests / test_duration
            analysis.append(f"- **Search Capacity**: ~{total_search_rps:.0f} queries/second")
            analysis.append(f"- **Peak Search Rate**: ~{total_search_rps * 60:.0f} queries/minute")
        
        return "\n".join(analysis) if analysis else "- Insufficient data for capacity analysis"

    def generate_scaling_recommendations(self, total_stats):
        """Generate scaling recommendations"""
        recommendations = []
        
        overall_success_rate = ((total_stats.num_requests - total_stats.num_failures) / total_stats.num_requests * 100) if total_stats.num_requests > 0 else 0
        
        if overall_success_rate > 99:
            recommendations.append("- **Excellent**: System handled load very well, ready for production scaling")
            recommendations.append("- Consider testing with higher concurrent user loads")
        elif overall_success_rate > 95:
            recommendations.append("- **Good**: System performance is acceptable for production")
            recommendations.append("- Monitor performance under sustained high loads")
        elif overall_success_rate > 90:
            recommendations.append("- **Warning**: Some performance degradation observed")
            recommendations.append("- Implement recommended optimizations before scaling")
        else:
            recommendations.append("- **Critical**: Significant performance issues detected")
            recommendations.append("- Address performance bottlenecks before production deployment")
        
        # Specific recommendations based on response times
        if total_stats.avg_response_time > 1000:
            recommendations.append("- Consider horizontal scaling due to high response times")
        
        return "\n".join(recommendations)

    def generate_conclusion(self, total_stats):
        """Generate test conclusion"""
        overall_success_rate = ((total_stats.num_requests - total_stats.num_failures) / total_stats.num_requests * 100) if total_stats.num_requests > 0 else 0
        
        if overall_success_rate > 95 and total_stats.avg_response_time < 1000:
            return f"""The Stress test completed successfully with excellent results. The system maintained a {overall_success_rate:.2f}% success rate with an average response time of {total_stats.avg_response_time:.2f}ms across {total_stats.num_requests:,} total requests.

    **Key Findings:**
    - Both ingestion and search endpoints performed well under the test load
    - Response times remained within acceptable ranges
    - Error rates were minimal

    **Recommendation:** The system is ready for production deployment with the tested data volumes and concurrent user loads."""
        
        elif overall_success_rate > 90:
            return f"""The Stress test revealed acceptable performance with some areas for improvement. The system achieved a {overall_success_rate:.2f}% success rate with an average response time of {total_stats.avg_response_time:.2f}ms.

    **Key Findings:**
    - System handled the majority of requests successfully
    - Some performance degradation under peak load
    - Response times occasionally exceeded optimal thresholds

    **Recommendation:** Implement the suggested optimizations before scaling to higher loads in production."""
        
        else:
            return f"""The Stress test identified significant performance challenges. The system achieved only a {overall_success_rate:.2f}% success rate with an average response time of {total_stats.avg_response_time:.2f}ms.

    **Key Findings:**
    - High failure rates indicate system stress under current load
    - Response times exceeded acceptable thresholds
    - Multiple performance bottlenecks detected

    **Recommendation:** Immediate optimization is required before production deployment. Focus on the critical issues identified in the recommendations sections."""

def main():
    """Main function to run the test"""
    global search_queries_cycle, records_cycle
    
    console.print(create_header_panel())
    
    with console.status("[bold green]Loading configuration...", spinner="dots"):
        app_config = TestConfig.from_yaml("test/config.yaml")
        validate_pid(app_config.mindsdb_infra.mindsdb_pid)

        if app_config.mindsdb_infra.host.endswith("/"):
            app_config.mindsdb_infra.host = app_config.mindsdb_infra.host[:-1]

        host = f"{app_config.mindsdb_infra.host}:{app_config.mindsdb_infra.port}"
        test_config = app_config.stress
        
        if test_config.output_dir.endswith("/"):
            test_config.output_dir = test_config.output_dir[:-1]

        os.makedirs(test_config.output_dir, exist_ok=True)

    console.print("✅ [green]Configuration loaded successfully[/green]")
    
    with console.status("[bold green]Starting resource monitor...", spinner="dots"):
        ps_record_process = start_resource_monitor_process(app_config.mindsdb_infra.mindsdb_pid, test_config.output_dir)
    
    console.print("✅ [green]Resource monitor started[/green]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        
        load_task = progress.add_task("Loading test data files...", total=2)
        
        progress.update(load_task, description="Loading ingestion data...")
        records, data_size_mb = load_ingestion_data(test_config.test_data_path, test_config.data_size)
        progress.advance(load_task)
        
        progress.update(load_task, description="Loading search queries...")
        search_queries_cycle = cycle([q["query"] for q in load_search_queries(test_config.queries_file_path)])
        records_cycle = cycle(records)
        progress.advance(load_task)

    console.print("✅ [green]Test data files loaded successfully[/green]")
    console.print(create_config_table(app_config, test_config, host, data_size_mb))

    with console.status("[bold green]Setting up knowledge base...", spinner="bouncingBall"):
        status, kb_create_time_taken = setup_kb(host=host)
        
    if not status:
        console.print("❌ [red]Failed to setup KB. Exiting.[/red]")
        sys.exit(1)
    
    console.print(f"✅ [green]Knowledge base setup completed in {kb_create_time_taken:.2f}s[/green]")

    # Setup Locust environment
    setup_logging("INFO", None)
    
    # Create environment
    env = Environment(user_classes=[KBTestUser], host=host)
    runner = env.create_local_runner()

    # Enable stats history for better reporting
    env.stats.reset_all()
    
    start_time = datetime.now()
    
    try:
        web_ui = env.create_web_ui("127.0.0.1", 8089)

        gevent.spawn(stats_printer(env.stats))
        gevent.spawn(stats_history, env.runner)

        # Start test
        runner.start(test_config.concurrent_users, spawn_rate=test_config.spawn_rate)
        
        run_time_seconds = int(test_config.test_runtime)
        
        # Create test info panel
        test_info = Panel(
            f"🚀 [bold]Test Started![/bold]\n\n"
            f"⏱️  Runtime: {run_time_seconds} seconds\n"
            f"🎯 Target: {host}\n"
            f"👥 Users: {test_config.concurrent_users}\n"
            f"📈 Spawn Rate: {test_config.spawn_rate}/s\n"
            f"🌐 Web UI: http://127.0.0.1:8089",
            title="Load Test Information",
            border_style="green"
        )
        console.print(test_info)
        
        # Run the test with live stats
        gevent_timer = gevent.spawn_later(run_time_seconds, lambda: env.runner.quit())
        
        # Create a simple live display for stats
        with Progress(
            TextColumn("[progress.description]"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            test_progress = progress.add_task("Running load test...", total=run_time_seconds)
            
            start_test_time = datetime.now()
            
            # Run for specified duration with live updates
            while (datetime.now() - start_test_time).total_seconds() < run_time_seconds:
                elapsed = (datetime.now() - start_test_time).total_seconds()
                progress.update(test_progress, completed=min(elapsed, run_time_seconds))
                
                # Print live stats every 10 seconds
                if int(elapsed) % 10 == 0 and elapsed > 0:
                    console.print(create_stats_table(env.stats))
                
                # Check if runner has stopped
                if hasattr(runner, 'state') and runner.state in ['stopped', 'stopping']:
                    break
                    
                gevent.sleep(1)
        
        # Wait for any remaining operations to complete
        if hasattr(runner, 'greenlet') and runner.greenlet:
            runner.greenlet.join(timeout=5)
        
        if gevent_timer:
            gevent_timer.kill()

    except KeyboardInterrupt:
        console.print("\n⚠️ [yellow]Test interrupted by user[/yellow]")
        runner.stop()
    
    except Exception as e:
        console.print(f"❌ [red]Test error: {e}[/red]")
        runner.stop()
    
    finally:
        web_ui.stop()
        end_time = datetime.now()
        
        # Generate final stats with Rich formatting
        console.print("\n" + "="*80)
        
        completion_panel = Panel(
            "[bold green]TEST COMPLETED SUCCESSFULLY! 🎉[/bold green]",
            box=box.DOUBLE,
            style="green"
        )
        console.print(completion_panel)
        
        # Get final stats
        stats = env.stats
        total_stats = stats.total
        
        with console.status("[bold green]Collecting final metrics...", spinner="dots"):
            kb_row_cnt = row_count_kb(host)
        
        # Create comprehensive results table
        results_table = Table(title="Final Test Results", box=box.HEAVY)
        results_table.add_column("Metric", style="cyan", no_wrap=True)
        results_table.add_column("Value", style="green")
        
        test_duration = (end_time - start_time).total_seconds()
        success_rate = ((total_stats.num_requests - total_stats.num_failures) / total_stats.num_requests * 100) if total_stats.num_requests > 0 else 0
        
        results_table.add_row("⏱️ Test Duration", f"{test_duration:.2f} seconds")
        results_table.add_row("📊 Total Requests", f"{total_stats.num_requests:,}")
        results_table.add_row("❌ Total Failures", f"{total_stats.num_failures:,}")
        results_table.add_row("✅ Success Rate", f"{success_rate:.2f}%")
        results_table.add_row("⚡ Avg Response Time", f"{total_stats.avg_response_time:.2f}ms")
        results_table.add_row("🚀 Requests per Second", f"{total_stats.total_rps:.2f}")
        results_table.add_row("🔥 Max Response Time", f"{total_stats.max_response_time:.2f}ms")
        results_table.add_row("📈 95th Percentile", f"{total_stats.get_response_time_percentile(0.95):.2f}ms")
        results_table.add_row("🗄️ KB Row Count", f"{kb_row_cnt:,}")
        
        console.print(results_table)
        
        with console.status("[bold green]Cleaning up knowledge base...", spinner="dots"):
            status, kb_cleanup_time = cleanup_kb(host)
            
        if not status:
            console.print("⚠️ [yellow]Warning: KB cleanup may have failed[/yellow]")
        else:
            console.print(f"✅ [green]KB cleanup completed in {kb_cleanup_time:.2f}s[/green]")
    
    # Cleanup process monitor
    ps_record_process.terminate()
    ps_record_process.wait()
    
    # Prepare info for report generation
    info = {
        "kb_create": kb_create_time_taken, 
        "kb_delete": kb_cleanup_time, 
        "kb_row_cnt": kb_row_cnt,
        "data_size_mb": data_size_mb,
        "host": host,
        "start_time": start_time,
        "end_time": end_time
    }
    
    with console.status("[bold green]Generating final report...", spinner="dots"):
        Report().generate_stress_report(stats, test_config, info)
    
    # Final success message
    success_panel = Panel(
        f"🎯 [bold green]Stress test completed successfully![/bold green]\n\n"
        f"📋 Report generated in: {test_config.output_dir}\n"
        f"📊 Total requests processed: {total_stats.num_requests:,}\n"
        f"⚡ Average RPS: {total_stats.total_rps:.2f}",
        title="Test Summary",
        border_style="green",
        box=box.DOUBLE
    )
    console.print(success_panel)

if __name__ == "__main__":
    main()