# MindsDB Knowledge Base Stress Test Report

## Test Configuration
- **Test Date**: 2025-07-01 09:55:04
- **Test Duration**: 177.05 seconds
- **Data Size**: 1,000 records (research papers)
- **Concurrent Users**: 15
- **Spawn Rate**: 2 users/second
- **Wait Time**: between 1s and 5s
- **Target Host**: http://127.0.0.1:47334
- **Total Data Volume**: 89.07 MB

## Test Environment
### Software Specs
- **OS**: Linux-6.6.87.2-microsoft-standard-WSL2-x86_64-with-glibc2.39
- **Python Version**: 3.12.11
- **MindsDB Version**: 25.6.3.1
- **Knowledge Base Embedding Model**: text-embedding-3-small
- **Knowledge Base ReRanking Model**: None
- **Knowledge Base Storage**: ChromaDB
### Hardware Specs
- **Machine**: x86_64
- **Processor**: x86_64
- **CPU Cores**: 32
- **RAM (GB)**: 15.15
- **Disk Total (GB)**: 1006.85


## Executive Summary

### Overall Performance
- **Total Requests**: 470
- **Total Failures**: 8
- **Overall Success Rate**: 98.30%
- **Average Response Time**: 2561.95ms
- **Overall RPS**: 2.66 requests/second
- **Knowledge Base Creation Time**: 3.61s
- **Knowledge Base Deletion Time**: 3.61s
- **Knowledge Base Row Count**: 1
- **Total Data Volume**: 89.07 MB

### Ingestion Performance
- **Total Records (Papers) Processed**: 291
- **Success Rate**: 97.59%
- **Average Response Time**: 3358.35ms
- **Throughput (Records per Second)**: 1.64


### Search Performance  
- **Total Search Queries**: 179
- **Success Rate**: 99.44%
- **Average Response Time**: 1267.24ms
- **Queries per Second**: 1.01

## Detailed Performance Metrics

### Ingestion Endpoint Analysis

#### Key Metrics
- **Total Requests**: 291
- **Failed Requests**: 7
- **Average Response Time**: 3358.35ms
- **Minimum Response Time**: 1066.99ms
- **Maximum Response Time**: 12648.06ms
- **Requests per Second**: 1.65
- **Median Response Time**: 3000.00ms

#### Response Time Percentiles
- **50th Percentile**: 3000.00ms
- **95th Percentile**: 6300.00ms
- **99th Percentile**: 8500.00ms


### Search Endpoint Analysis

#### Key Metrics
- **Total Requests**: 179
- **Failed Requests**: 1
- **Average Response Time**: 1267.24ms
- **Minimum Response Time**: 376.89ms
- **Maximum Response Time**: 5508.85ms
- **Requests per Second**: 1.01
- **Median Response Time**: 1000.00ms

#### Response Time Percentiles
- **50th Percentile**: 1000.00ms
- **95th Percentile**: 3100.00ms
- **99th Percentile**: 4100.00ms


### MindsDB Process Resource Usage
#### Key Metrics

- **Max memory usage**: 8,182.07 MB

- **Average memory usage (MB)**: 6,706.85 MB

- **Max CPU usage (%)**: 309.20

- **Average CPU usage (%)**: 83.10


Resource usage graph:

![plot](resource_usage.png)


## Response Time Distribution

### Ingestion Response Times

| Metric | Value |
|--------|-------|
| Average | 3358.35ms |
| Median | 3000.00ms |
| 95th Percentile | 6300.00ms |
| 99th Percentile | 8500.00ms |
| Min | 1066.99ms |
| Max | 12648.06ms |


### Search Response Times

| Metric | Value |
|--------|-------|
| Average | 1267.24ms |
| Median | 1000.00ms |
| 95th Percentile | 3100.00ms |
| 99th Percentile | 4100.00ms |
| Min | 376.89ms |
| Max | 5508.85ms |


## Performance Recommendations

### Ingestion Optimization
- **Critical**: Average response time is very high (>2s). Consider batching the input records
- Implement asynchronous processing
- **Warning**: Some failures detected (2.4%). Monitor error patterns

### Search Optimization
- **Performance**: Slow search detected
- Add database indexes on frequently searched fields
- Consider implementing search result caching

## System Resource Implications

### Capacity Analysis
- **Ingestion Capacity**: ~2 records/second
- **Peak Ingestion Rate**: ~99 records/minute
- **Search Capacity**: ~1 queries/second
- **Peak Search Rate**: ~61 queries/minute

### Scaling Recommendations
- **Good**: System performance is acceptable for production
- Monitor performance under sustained high loads
- Consider horizontal scaling due to high response times

## Test Validity and Limitations
- Test executed under controlled conditions with 15 concurrent users
- Results may vary with different data patterns and real-world usage scenarios
- Network latency simulated through HTTP requests
- Knowledge Base performance depends on hardware configuration and system resources
- Test data consists of research papers which may not represent all use cases

## Conclusion
The Stress test revealed acceptable performance with some areas for improvement. The system achieved a 98.30% success rate with an average response time of 2561.95ms.

**Key Findings:**
- System handled the majority of requests successfully
- Some performance degradation under peak load
- Response times occasionally exceeded optimal thresholds

**Recommendation:** Implement the suggested optimizations before scaling to higher loads in production.

## Testing Process and Methodology

This test adheres to a standardized methodology to ensure consistent and reproducible results.
In order to run the stress script, refer `stress.md` file found in the `reports` folder of the repo https://github.com/Better-Boy/PaperSense.


---
*Report generated on 2025-07-01 09:58:02*  
*Test Generated By: Big-Bounty*