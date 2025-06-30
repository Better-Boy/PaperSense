from datetime import datetime
import platform
import sys

import psutil

from plot import Plot


class Report:
    def generate_report(self, stats, start_time, end_time, config, kb_times, data_size_mb, test_type, api_errors):
        """Generate comprehensive test report using Locust stats"""
        
        self.test_type = test_type

        report_filename = f"{test_type}_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        test_duration = (end_time - start_time).total_seconds()
        
        # Get aggregated stats
        total_stats = stats.total

        # Separate ingestion and search stats
        entries_dict = dict(stats.entries.items())
        ingestion_stats = entries_dict[("ingest", "POST")] if ("ingest", "POST") in entries_dict else None
        search_stats = entries_dict[("search", "POST")] if ("search", "POST") in entries_dict else None

        # Generate report content
        report_content = f"""# MindsDB Knowledge Base {test_type.title()} Test Report

    ## Test Configuration
    - **Test Date**: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
    - **Test Duration**: {test_duration:.2f} seconds
    - **Data Size**: {config['data_size']:,} records (research papers)
    - **Concurrent Users**: {config['users']}
    - **Spawn Rate**: {config['spawn_rate']} users/second
    - **Wait time**: between 1s and 5s
    - **Target Host**: {config['host']}

    ## Test Environment
    {self.test_env_info()}

    ## Executive Summary

    ### Overall Performance
    - **Total Requests**: {total_stats.num_requests}
    - **Total Failures**: {total_stats.num_failures}
    - **Overall Success Rate**: {((total_stats.num_requests - total_stats.num_failures) / total_stats.num_requests * 100) if total_stats.num_requests > 0 else 0:.2f}%
    - **Average Response Time**: {total_stats.avg_response_time:.2f}ms
    - **Overall RPS**: {total_stats.total_rps:.2f} requests/second
    - **Knowledge Base creation time**: {kb_times.get("create", 0)}s
    - **Knowledge Base deletion time**: {kb_times.get("delete", 0)}s
    - **Knowledge Base row count**: {kb_times.get("row_cnt", 0)}
    - **Total size of text data inserted**: {data_size_mb} MB

    ### Ingestion Performance
    {self.generate_ingestion_summary(ingestion_stats, test_duration)}

    ### Search Performance
    {self.generate_search_summary(search_stats, test_duration)}

    ## Detailed Performance Metrics

    ### Ingestion Endpoint Analysis
    {self.generate_ingestion_details(ingestion_stats)}

    ### Search Endpoint Analysis
    {self.generate_ingestion_details(search_stats)}

    ### MindsDB process resource usage
    {Plot().generate_resource_usage_md(test_type=test_type)}

    ## Response Time Distribution

    ### Ingestion Response Times
    {self.generate_response_time_table(ingestion_stats, "Ingestion")}

    ### Search Response Times
    {self.generate_response_time_table(search_stats, "Search")}

    ## Error Analysis
    {self.generate_error_analysis(stats)}

    #### Ingestion Error Examples
    {self.generate_error_samples(api_errors['ingest'], 'Ingestion')}

    #### Search Error Examples
    {self.generate_error_samples(api_errors['search'], 'search')}

    ## Performance Recommendations

    ### Ingestion Optimization
    {self.generate_ingestion_recommendations(ingestion_stats)}

    ### Search Optimization
    {self.generate_search_recommendations(search_stats)}

    ## System Resource Implications

    ### Capacity Analysis
    {self.generate_capacity_analysis(ingestion_stats, search_stats, test_duration)}

    ### Scaling Recommendations
    {self.generate_scaling_recommendations(total_stats)}

    ## Test Validity and Limitations
    - Test executed under controlled conditions with {config['users']} concurrent users
    - Results may vary with different data patterns and real-world usage
    - Network latency simulated through HTTP requests
    - Knowledge Base performance depends on hardware and configuration

    ## Conclusion
    {self.generate_conclusion(total_stats)}

    ## Testing Process and Methodology
    {self.generate_test_methodology()}

    ---
    *Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
    *Test configuration: {config['data_size']} data size, {config['users']} users*
    """
        report = []
        for line in report_content.split('\n'):
            report.append(line.lstrip())

        report_content = "\n".join(report)
        # Write report to file
        with open(report_filename, 'w') as f:
            f.write(report_content)
        
        print(f"✓ {test_type.title()} test report generated: {report_filename}")
        return report_filename

    def generate_error_samples(self, errors, op_type):
        """Generate sample error messages for detailed analysis"""
        if not errors:
            return f"- No {op_type} errors recorded"
        
        # Get up to 5 most recent errors
        recent_errors = sorted(errors, key=lambda x: x['timestamp'], reverse=True)[:5]
        
        samples = f"\n**Most Recent {op_type.title()} Errors:**\n\n"
        
        for i, error in enumerate(recent_errors, 1):
            samples += f"""**Error #{i}:**
    - **Timestamp**: {error['timestamp']}
    - **Status Code**: {error['status_code']}
    - **Error Message**: {error['error_message']}
    - **Response Text**: {error['response_text'] or 'No response body'}

    """
        
        return samples


    def generate_test_methodology(self):
        return f"""
        This test adheres to a standardized methodology to ensure consistent and reproducible results.

Difference between benchmarking and stress testing is just that benchmarking is testing under normal conditions like upto 10 users and stress testing is testing concurrent 100 users. 
Hence, this test script is configurable enough to do both benchmarking and stress testing.

    ### Executing the Test Script: A How-To

    1. Install the required libraries (If not installed already):

    ```bash
    pip install seaborn
    pip install matplotlib
    pip install pandas
    pip install locust
    pip install gevent
    pip install psutil
    pip install numpy
    pip install psrecord
    ```
    2. The name and schema of the knowledge base is constant. The sql query used to create the knowledge base is as follows:

    ```sql
    CREATE KNOWLEDGE_BASE IF NOT EXISTS arxiv_test_kb
    USING
        embedding_model = {{
            "provider": "openai",
            "model_name": "text-embedding-3-small",
            "api_key": "<openai_api_key>"
        }},
        reranking_model = {{
            "provider": "openai", 
            "model_name": "gpt-4o",
            "api_key": "<openai_api_key>"
        }},
        content_columns = ['text'],
        metadata_columns = ['authors', 'title', 'categories', 'arxiv_id'];
    ```
    The knowledge is created before starting the test and cleaned up afterwards.

    3. Test data generation:

    Since I built semantic search using arxiv, I used the papers downloaded itself as the input to the knowledge base. A sample data file is in the `data` folder.
    Link to the sample file - [sample_test_data.json](../data/data.json)

    The sample file contains clean and processed data of 500 papers.

    4. The test script - `benchmark_stress.py` is main running script which uses locust to load test the API endpoints. 
    5. The insertion and search functionalities are tested by building respective queries and hitting the `/api/sql/query` endpoint
    6. On running the test script, a subprocess is spawned which monitors the resource usage of mindsdb process during test duration. 
    7. The subprocess will be terminated after successful completion of load test.
    8. Running the script

    **Imp**

    Before running the script, find the pid (process id) of mindsdb process. MindsDB spawns multiple subprocess, it's important to find the main mindsdb process.

    You can get the pid of the mindsdb process by running - `ps -ef | grep mindsdb`. But you need to find the main (or parent) process.

    Running the script:

    ```bash
    python benchmark_stress.py --data-file-path ../data/test_data.json --search-query-file-path ../data/queries.json --data-size 400 --host http://127.0.0.1:47334 --users 3 --spawn-rate 1  --run-time 10 --mdb-pid 98970
    ```

    The command line arguments are as follows:

    ```bash
    Knowledge base Test

    options:
    -h, --help            show this help message and exit
    --data-file-path DATA_FILE_PATH
                            Path to the json data file to be ingested to KB
    --search-query-file-path SEARCH_QUERY_FILE_PATH
                            Path to the json search queries file to be searched on KB
    --data-size DATA_SIZE
                            Total amount of data to process
    --host HOST           MindsDB server host
    --port PORT           MindsDB server port
    --users USERS         Number of concurrent users
    --spawn-rate SPAWN_RATE
                            Users spawned per second
    --run-time RUN_TIME   Test duration. Unit is in seconds
    --mdb-pid MDB_PID     Mindsdb server pid
    ```

    MindsDB pid has to be given in order to run the test script.

    9. Once the test is complete, 3 files are created - 
        1. `performance_dashboard.png` - An image file that shows the mindsdb process resource usage
        2. `stress_test_report_<timestamp>.md` - The stress test report
        3. `benchmark_test_report_<timestamp>.md` - The benchmark test report
        4. `activity.csv` - The resource utilization numbers of the mindsdb process collected during the test.
    """


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
        md += "### Hardware Specs\n"
        for key, value in hardware.items():
            md += f"- **{key}**: {value}\n"

        return md

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

    def generate_error_analysis(self, stats):
        """Generate error analysis from Locust stats"""
        error_analysis = "\n### Error Summary\n"
        
        total_errors = sum(stat.num_failures for stat in stats.entries.values())
        if total_errors == 0:
            return error_analysis + "- **Total Errors**: 0\n- **Status**: All requests completed successfully\n"
        
        error_analysis += f"- **Total Errors**: {total_errors:,}\n\n"
        error_analysis += "### Errors by Endpoint\n\n"
        error_analysis += "| Endpoint | Total Requests | Failures | Failure Rate |\n"
        error_analysis += "|----------|----------------|----------|-------------|\n"
        
        for name, stat in stats.entries.items():
            if stat.num_failures > 0:
                failure_rate = (stat.num_failures / stat.num_requests * 100) if stat.num_requests > 0 else 0
                error_analysis += f"| {name[0]} | {stat.num_requests} | {stat.num_failures} | {failure_rate:.2f}% |\n"
        
        return error_analysis

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
            return f"""The {self.test_type} test completed successfully with excellent results. The system maintained a {overall_success_rate:.2f}% success rate with an average response time of {total_stats.avg_response_time:.2f}ms across {total_stats.num_requests:,} total requests.

    **Key Findings:**
    - Both ingestion and search endpoints performed well under the test load
    - Response times remained within acceptable ranges
    - Error rates were minimal

    **Recommendation:** The system is ready for production deployment with the tested data volumes and concurrent user loads."""
        
        elif overall_success_rate > 90:
            return f"""The {self.test_type} test revealed acceptable performance with some areas for improvement. The system achieved a {overall_success_rate:.2f}% success rate with an average response time of {total_stats.avg_response_time:.2f}ms.

    **Key Findings:**
    - System handled the majority of requests successfully
    - Some performance degradation under peak load
    - Response times occasionally exceeded optimal thresholds

    **Recommendation:** Implement the suggested optimizations before scaling to higher loads in production."""
        
        else:
            return f"""The {self.test_type} test identified significant performance challenges. The system achieved only a {overall_success_rate:.2f}% success rate with an average response time of {total_stats.avg_response_time:.2f}ms.

    **Key Findings:**
    - High failure rates indicate system stress under current load
    - Response times exceeded acceptable thresholds
    - Multiple performance bottlenecks detected

    **Recommendation:** Immediate optimization is required before production deployment. Focus on the critical issues identified in the recommendations sections."""

