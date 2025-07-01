# MindsDB Knowledge Base Stress Test Report

## Test Configuration
- **Test Date**: 2025-07-01 09:58:30
- **Test Duration**: 177.45 seconds
- **Data Size**: 1,000 records (research papers)
- **Concurrent Users**: 50
- **Spawn Rate**: 4 users/second
- **Wait Time**: between 1s and 5s
- **Target Host**: http://127.0.0.1:47334
- **Total Data Volume**: 89.07 MB

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
- **Total Requests**: 325
- **Total Failures**: 97
- **Overall Success Rate**: 70.15%
- **Average Response Time**: 21935.13ms
- **Overall RPS**: 1.83 requests/second
- **Knowledge Base Creation Time**: 2.80s
- **Knowledge Base Deletion Time**: 2.80s
- **Knowledge Base Row Count**: 1
- **Total Data Volume**: 89.07 MB

### Ingestion Performance
- **Total Records (Papers) Processed**: 207
- **Success Rate**: 100.00%
- **Average Response Time**: 18463.21ms
- **Throughput (Records per Second)**: 1.17


### Search Performance  
- **Total Search Queries**: 118
- **Success Rate**: 17.80%
- **Average Response Time**: 28025.69ms
- **Queries per Second**: 0.66

## Detailed Performance Metrics

### Ingestion Endpoint Analysis

#### Key Metrics
- **Total Requests**: 207
- **Failed Requests**: 0
- **Average Response Time**: 18463.21ms
- **Minimum Response Time**: 1915.13ms
- **Maximum Response Time**: 26268.04ms
- **Requests per Second**: 1.17
- **Median Response Time**: 20000.00ms

#### Response Time Percentiles
- **50th Percentile**: 20000.00ms
- **95th Percentile**: 23000.00ms
- **99th Percentile**: 24000.00ms


### Search Endpoint Analysis

#### Key Metrics
- **Total Requests**: 118
- **Failed Requests**: 97
- **Average Response Time**: 28025.69ms
- **Minimum Response Time**: 778.80ms
- **Maximum Response Time**: 30003.79ms
- **Requests per Second**: 0.67
- **Median Response Time**: 30000.00ms

#### Response Time Percentiles
- **50th Percentile**: 30000.00ms
- **95th Percentile**: 30000.00ms
- **99th Percentile**: 30000.00ms


### MindsDB Process Resource Usage
#### Key Metrics

- **Max memory usage**: 9,915.77 MB

- **Average memory usage (MB)**: 7,160.69 MB

- **Max CPU usage (%)**: 160.30

- **Average CPU usage (%)**: 70.29


Resource usage graph:

![plot](resource_usage.png)


## Response Time Distribution

### Ingestion Response Times

| Metric | Value |
|--------|-------|
| Average | 18463.21ms |
| Median | 20000.00ms |
| 95th Percentile | 23000.00ms |
| 99th Percentile | 24000.00ms |
| Min | 1915.13ms |
| Max | 26268.04ms |


### Search Response Times

| Metric | Value |
|--------|-------|
| Average | 28025.69ms |
| Median | 30000.00ms |
| 95th Percentile | 30000.00ms |
| 99th Percentile | 30000.00ms |
| Min | 778.80ms |
| Max | 30003.79ms |


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
- **Peak Ingestion Rate**: ~70 records/minute
- **Search Capacity**: ~1 queries/second
- **Peak Search Rate**: ~40 queries/minute

### Scaling Recommendations
- **Critical**: Significant performance issues detected
- Address performance bottlenecks before production deployment
- Consider horizontal scaling due to high response times

## Test Validity and Limitations
- Test executed under controlled conditions with 50 concurrent users
- Results may vary with different data patterns and real-world usage scenarios
- Network latency simulated through HTTP requests
- Knowledge Base performance depends on hardware configuration and system resources
- Test data consists of research papers which may not represent all use cases

## Conclusion
The Stress test identified significant performance challenges. The system achieved only a 70.15% success rate with an average response time of 21935.13ms.

**Key Findings:**
- High failure rates indicate system stress under current load
- Response times exceeded acceptable thresholds
- Multiple performance bottlenecks detected

**Recommendation:** Immediate optimization is required before production deployment. Focus on the critical issues identified in the recommendations sections.

## Testing Process and Methodology

This test adheres to a standardized methodology to ensure consistent and reproducible results.
In order to run the stress script, refer `stress.md` file found in the `reports` folder of the repo https://github.com/Better-Boy/PaperSense.


---
*Report generated on 2025-07-01 10:01:46*  
*Test Generated By: Big-Bounty*