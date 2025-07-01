# MindsDB Knowledge Base Benchmark Report

**Generated on:** 2025-07-01 08:34:11  
**Total Test Duration:** 1459.01 seconds  
**Report Type:** Knowledge Base API Performance Analysis

---

## Executive Summary

### 📊 Key Performance Indicators

| Metric | Value | Status |
|--------|-------|--------|
| **Total Requests** | 1025 | ✅ |
| **Success Rate** | 99.8% | ✅ |
| **Successful Requests** | 1023 | - |
| **Failed Requests** | 2 | ⚠️ |
| **Average Response Time** | 2.822s | ⚠️ |

### 🎯 Overall Assessment

**🔴 POOR** - Significant performance issues detected. Immediate optimization required.

### 🔍 Quick Insights

- **Fastest Knowledge Base Operation:** create (0.006s avg)
- **Slowest Knowledge Base Operation:** delete (18.108s avg)
- **Most Reliable:** create (100.0% success rate)

- **Row count in Knowledge Base:** 800

### 📋 Test Configuration

- **Test Period:** 2025-07-01 08:10:06.741207 to 2025-07-01 08:34:09.053215
- **Knowledge Base Functionalities tested:** create, insert, search, delete
- **Test Methodology:** Sequential execution (setup → insert → search → delete)

---
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


---
## Detailed Analysis

### 🔧 Create Operation

**Performance Status:** 🟢 EXCELLENT

#### 📈 Core Metrics

| Metric | Value |
|--------|-------|
| Total Requests | 1 |
| Successful Requests | 1 |
| Success Rate | 100.00% |
| Average Response Time | 0.006s |
| Median Response Time | 0.006s |
| Minimum Response Time | 0.006s |
| Maximum Response Time | 0.006s |
| Standard Deviation | 0.000s |
| 95th Percentile | 0.006s |
| 99th Percentile | 0.006s |

#### 🎯 Performance Analysis

- **Response Time:** ✅ Excellent - Very fast response times
- **Consistency:** ✅ Very consistent performance
- **Tail Latency:** ✅ Good - 95th percentile within expected range

---

### 🔧 Insert Operation

**Performance Status:** 🟡 GOOD

#### 📈 Core Metrics

| Metric | Value |
|--------|-------|
| Total Requests | 1000 |
| Successful Requests | 998 |
| Success Rate | 99.80% |
| Average Response Time | 2.515s |
| Median Response Time | 2.327s |
| Minimum Response Time | 0.860s |
| Maximum Response Time | 13.705s |
| Standard Deviation | 1.045s |
| 95th Percentile | 3.998s |
| 99th Percentile | 6.229s |

#### 🎯 Performance Analysis

- **Response Time:** ❌ Poor - Very slow response times
- **Consistency:** ⚠️ Moderately consistent performance
- **Tail Latency:** ✅ Good - 95th percentile within expected range

#### ⚠️ Error Analysis

| Status Code | Count | Description |
|-------------|-------|-------------|
| 200 | 2 | Unknown Error |

**Sample Error Messages:**

1. `{"type": "error", "error_code": 0, "error_message": "The SQL statement cannot be parsed - INSERT INT...`

#### 💡 Specific Recommendations

- ⚠️ insert has 99.8% success rate. Investigate error causes and improve reliability.
- ⏰ insert response time (2.52s) could be improved. Consider adding database indexes or optimizing business logic.
- 💾 Consider implementing batch insert operations to improve throughput.

---

### 🔧 Search Operation

**Performance Status:** 🟢 EXCELLENT

#### 📈 Core Metrics

| Metric | Value |
|--------|-------|
| Total Requests | 15 |
| Successful Requests | 15 |
| Success Rate | 100.00% |
| Average Response Time | 12.341s |
| Median Response Time | 15.598s |
| Minimum Response Time | 2.052s |
| Maximum Response Time | 18.920s |
| Standard Deviation | 6.085s |
| 95th Percentile | 18.351s |
| 99th Percentile | 18.806s |

#### 🎯 Performance Analysis

- **Response Time:** ❌ Poor - Very slow response times
- **Consistency:** ⚠️ Moderately consistent performance
- **Tail Latency:** ✅ Good - 95th percentile within expected range

#### 💡 Specific Recommendations

- 🐌 search has high average response time (12.34s). Consider optimizing database queries, adding caching, or scaling resources.
- 🔍 Search performance could benefit from better indexing or search optimization.

---

### 🔧 Delete Operation

**Performance Status:** 🟢 EXCELLENT

#### 📈 Core Metrics

| Metric | Value |
|--------|-------|
| Total Requests | 1 |
| Successful Requests | 1 |
| Success Rate | 100.00% |
| Average Response Time | 18.108s |
| Median Response Time | 18.108s |
| Minimum Response Time | 18.108s |
| Maximum Response Time | 18.108s |
| Standard Deviation | 0.000s |
| 95th Percentile | 18.108s |
| 99th Percentile | 18.108s |

#### 🎯 Performance Analysis

- **Response Time:** ❌ Poor - Very slow response times
- **Consistency:** ✅ Very consistent performance
- **Tail Latency:** ✅ Good - 95th percentile within expected range

#### 💡 Specific Recommendations

- 🐌 delete has high average response time (18.11s). Consider optimizing database queries, adding caching, or scaling resources.

---

## Resource usage analysis
#### Key Metrics
            
- **Max memory usage**: 5,199.05 MB

- **Average memory usage (MB)**: 3,237.76 MB

- **Max CPU usage (%)**: 100.80

- **Average CPU usage (%)**: 20.40


Resource usage graph:

![plot](resource_usage.png)
            ---

## 💡 Optimization Recommendations

### 🚀 Priority Actions

#### 🟡 Medium Priority

1. ⚠️ insert has 99.8% success rate. Investigate error causes and improve reliability.
2. ⏰ insert response time (2.52s) could be improved. Consider adding database indexes or optimizing business logic.
3. 🐌 search has high average response time (12.34s). Consider optimizing database queries, adding caching, or scaling resources.
4. 🐌 delete has high average response time (18.11s). Consider optimizing database queries, adding caching, or scaling resources.

#### 🟢 Low Priority

1. 💾 Consider implementing batch insert operations to improve throughput.
2. 🔍 Search performance could benefit from better indexing or search optimization.
3. 🔧 Implement monitoring and alerting for these performance metrics in production.

---

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
