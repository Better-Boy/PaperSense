# MindsDB Knowledge Base Stress Test Report

## Test Configuration
- **Test Date**: 2025-06-30 08:22:16
- **Test Duration**: 124.31 seconds
- **Data Size**: 5,000 records (research papers)
- **Concurrent Users**: 50
- **Spawn Rate**: 2 users/second
- **Wait time**: between 1s and 5s
- **Target Host**: http://127.0.0.1:47334

## Test Environment
### Software Specs
- **OS**: Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39
- **Python Version**: 3.12.11
- **MindsDB Version**: 25.6.3.1
- **Knowledge Base Embedding Model**: text-embedding-3-small
- **Knowledge Base ReRanking Model**: gpt-4o
- **Knowledge Base Storage**: ChromaDB
### Hardware Specs
- **Machine**: x86_64
- **Processor**: x86_64
- **CPU Cores**: 32
- **RAM (GB)**: 15.15
- **Disk Total (GB)**: 1006.85


## Executive Summary

### Overall Performance
- **Total Requests**: 213
- **Total Failures**: 57
- **Overall Success Rate**: 73.24%
- **Average Response Time**: 20284.27ms
- **Overall RPS**: 1.71 requests/second
- **Knowledge Base creation time**: 2.0293991565704346s
- **Knowledge Base deletion time**: 0.03382754325866699s
- **Knowledge Base row count**: 1
- **Total size of text data inserted**: 448.72657775878906 MB

### Ingestion Performance
- **Total Records (Papers) Processed**: 132
- **Success Rate**: 100.00%
- **Average Response Time**: 16797.17ms
- **Throughput (Records per Second)**: 1.06


### Search Performance
- **Total Search Queries**: 81
- **Success Rate**: 29.63%
- **Average Response Time**: 25966.96ms
- **Queries per Second**: 0.65

## Detailed Performance Metrics

### Ingestion Endpoint Analysis

#### Key Metrics
- **Total Requests**: 132
- **Failed Requests**: 0
- **Average Response Time**: 16797.17ms
- **Minimum Response Time**: 1549.35ms
- **Maximum Response Time**: 23945.92ms
- **Requests per Second**: 1.06
- **Median Response Time**: 20000.00ms

#### Response Time Percentiles
- **50th Percentile**: 20000.00ms
- **95th Percentile**: 23000.00ms
- **99th Percentile**: 23000.00ms


### Search Endpoint Analysis

#### Key Metrics
- **Total Requests**: 81
- **Failed Requests**: 57
- **Average Response Time**: 25966.96ms
- **Minimum Response Time**: 434.83ms
- **Maximum Response Time**: 30013.32ms
- **Requests per Second**: 0.65
- **Median Response Time**: 30000.00ms

#### Response Time Percentiles
- **50th Percentile**: 30000.00ms
- **95th Percentile**: 30000.00ms
- **99th Percentile**: 30000.00ms


### MindsDB process resource usage

#### Key Metrics

- **Max memory usage**: 6,260.38 MB
- **Average memory usage (MB)**: 4,710.61 MB
- **Max CPU usage (%)**: 213.40 MB
- **Average CPU usage (%)**: 61.73 MB

Resource usage graph:

![plot](stress_resource_usage.png)


## Response Time Distribution

### Ingestion Response Times

| Metric | Value |
|--------|-------|
| Average | 16797.17ms |
| Median | 20000.00ms |
| 95th Percentile | 23000.00ms |
| 99th Percentile | 23000.00ms |
| Min | 1549.35ms |
| Max | 23945.92ms |


### Search Response Times

| Metric | Value |
|--------|-------|
| Average | 25966.96ms |
| Median | 30000.00ms |
| 95th Percentile | 30000.00ms |
| 99th Percentile | 30000.00ms |
| Min | 434.83ms |
| Max | 30013.32ms |


## Error Analysis

### Error Summary
- **Total Errors**: 57

### Errors by Endpoint

| Endpoint | Total Requests | Failures | Failure Rate |
|----------|----------------|----------|-------------|
| search | 81 | 57 | 70.37% |


#### Ingestion Error Examples
- No Ingestion errors recorded

#### Search Error Examples

**Most Recent Search Errors:**

**Error #1:**
- **Timestamp**: 2025-06-30T08:24:20.331467
- **Status Code**: 0
- **Error Message**: Search failed: 0
- **Response Text**: No response body

**Error #2:**
- **Timestamp**: 2025-06-30T08:24:19.991129
- **Status Code**: 0
- **Error Message**: Search failed: 0
- **Response Text**: No response body

**Error #3:**
- **Timestamp**: 2025-06-30T08:24:18.905240
- **Status Code**: 0
- **Error Message**: Search failed: 0
- **Response Text**: No response body

**Error #4:**
- **Timestamp**: 2025-06-30T08:24:18.267880
- **Status Code**: 0
- **Error Message**: Search failed: 0
- **Response Text**: No response body

**Error #5:**
- **Timestamp**: 2025-06-30T08:24:16.074257
- **Status Code**: 0
- **Error Message**: Search failed: 0
- **Response Text**: No response body



## Performance Recommendations

### Ingestion Optimization
- **Critical**: Average response time is very high (>2s). Consider batching the input records
- Implement asynchronous processing

### Search Optimization
- **Performance**: Slow search detected
- Add database indexes on frequently searched fields
- Consider implementing search result caching
- **Reliability**: High failure rates detected
- Review knowledge base search and reranking strategies

## System Resource Implications

### Capacity Analysis
- **Ingestion Capacity**: ~1 records/second
- **Peak Ingestion Rate**: ~64 records/minute
- **Search Capacity**: ~1 queries/second
- **Peak Search Rate**: ~39 queries/minute

### Scaling Recommendations
- **Critical**: Significant performance issues detected
- Address performance bottlenecks before production deployment
- Consider horizontal scaling due to high response times

## Test Validity and Limitations
- Test executed under controlled conditions with 50 concurrent users
- Results may vary with different data patterns and real-world usage
- Network latency simulated through HTTP requests
- Knowledge Base performance depends on hardware and configuration

## Conclusion
The stress test identified significant performance challenges. The system achieved only a 73.24% success rate with an average response time of 20284.27ms.

**Key Findings:**
- High failure rates indicate system stress under current load
- Response times exceeded acceptable thresholds
- Multiple performance bottlenecks detected

**Recommendation:** Immediate optimization is required before production deployment. Focus on the critical issues identified in the recommendations sections.

## Testing Process and Methodology

This  test adheres to a standardized methodology to ensure consistent and reproducible results.

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
embedding_model = {
"provider": "openai",
"model_name": "text-embedding-3-small",
"api_key": "<openai_api_key>"
},
reranking_model = {
"provider": "openai", 
"model_name": "gpt-4o",
"api_key": "<openai_api_key>"
},
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


---
*Report generated on 2025-06-30 08:24:42*
*Test configuration: 5000 data size, 50 users*
