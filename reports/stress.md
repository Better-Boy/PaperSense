## Stress Testing

### 🧪 Purpose of Stress Testing

This document outlines the stress testing conducted on MindsDB knowledge bases. The goal is to test the system under various scenarios to evaluate speed, scalability, and stability.

The stress testing depends heavily on the number of concurrent users.

### Data used for testing

1. Downloaded 12,000 arxiv pdf papers from different categories stored at Google Cloud Storage. For more info, refer the bulk access section [Kaggle Arxiv](https://www.kaggle.com/datasets/Cornell-University/arxiv)
2. Downloading the pdfs from the google cloud storage took almost 2 hours.
3. Processed each pdf via a data processing pipeline. The pipeline code is [bulk_data_processing.py](../src/bulk_data_processing.py)
4. The data processing pipeline for the 12,000 pdfs ran for almost 4 hours.
3. The different data sizes i.e paper counts - 1k, 5k, 10k were stored. The size of the individual files are large and can be found at []()
4. A sample data is included in this repository - [sample test data](../data/test_data.json)

### How to run the stress testing script?

The configuration settings for stress settings are in the yaml file - [config.yaml](test/config.yaml). Though the config file contains `benchmark` and `stress` config, only relevant config will be picked by the script. In this case, `stress` and `mindsdb_infra`.

---
mindsdb_infra 

| Key           | Description                                | Example Value        |
|---------------|--------------------------------------------|----------------------|
| `host`        | URL of the MindsDB server host             | `http://127.0.0.1`   |
| `port`        | Port number used by the MindsDB server     | `47334`              |
| `mindsdb_pid` | Process ID of the running MindsDB instance | `410423`             |

---
stress 

| Key                   | Value                                               |   Description                                                    |
|-----------------------|---------------------------------------------------------|--------------------------------------------------------------------|
| `data_size`           | 500                                                     | Number of data samples to be used during the stress test.          |
| `test_data_path`      | `/home/abhi/latest/PaperSense/data/test_data.json`      | File path to the test data used for executing queries.             |
| `queries_file_path`   | `/home/abhi/latest/PaperSense/data/queries.json`        | File path to the set of queries used in the stress test.           |
| `output_dir`          | `reports/stress_tests/scenario_2`                       | Directory where stress test results and reports will be stored.    |
| `concurrent_users`    | 5                                                       | Number of virtual users simulated concurrently during the test.    |
| `spawn_rate`          | 1                                                       | Rate at which new users are spawned (users per second).            |
| `test_runtime`        | 10                                                      | Duration of the test run in seconds.                               |


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

5. The create, insertion, search and delete functionalities are tested.
6. On running the test script, a subprocess is spawned which monitors the resource usage of mindsdb process during test duration. 
7. The subprocess will be terminated after successful completion of load test.

**Imp**  

8. Find the pid of the mindsdb process. 

MindsDB spawns multiple subprocess, it's important to find the main mindsdb process.

You can get the pid of the mindsdb process by running - `ps -ef | grep mindsdb`. But you need to find the main (or parent) process.

9. Mention the pid in the `test/config.yaml` for the config key `mindsdb_infra.mindsdb_pid`. 

Running the script:

```bash
python stress.py
```

MindsDB pid has to be given in order to run the test script.

9. Once the test is complete, 3 files are created in the output directory mentioned at `stress.output_dir`.
    1. `resource_usage.png` - An image file that shows the mindsdb process resource usage
    2. `stress_test_report_<timestamp>.md` - The stress test report
    3. `activity.csv` - The resource utilization numbers of the mindsdb process collected during the test.

10. Once you run the start, you can view the locust dashboard at `http://127.0.0.1:8089`.


### Test Scenarios

Note:
- The knowledge base name, schema, embedding and reranking model for all the tests are kept same. This info can be found at each individual scenario report.
- I couldn't test with the 10k dataset because my OpenAI credits for the testing phase were exhausted.

#### Scenario 1:

- Description - Test with reranking enabled
- Report - [Scenario_1_report](stress_tests/scenario_1/stress_test_report_20250701_095142.md)

A brief overview of the report:

Ingestion Performance
- Total Records (Papers) Processed: 131
- Success Rate: 100.00%
- Average Response Time: 2747.02ms
- Throughput (Records per Second): 0.74


Search Performance  
- Total Search Queries: 82
- Success Rate: 100.00%
- Average Response Time: 19264.34ms
- Queries per Second: 0.46

---
#### Scenario 2:

- Description - Test with reranking disabled 
- Report - [Scenario_2_report](stress_tests/scenario_2/stress_test_report_20250701_095801.md)


Ingestion Performance
- Total Records (Papers) Processed: 291
- Success Rate: 97.59%
- Average Response Time: 3358.35ms
- Throughput (Records per Second): 1.64


Search Performance  
- Total Search Queries: 179
- Success Rate: 99.44%
- Average Response Time: 1267.24ms
- Queries per Second: 1.01

---
#### Scenario 3:

- Description - 50 concurrent users with reranking enabled
- Report - [Scenario_3_report](stress_tests/scenario_3/stress_test_report_20250701_100146.md)


Ingestion Performance
- Total Records (Papers) Processed: 207
- Success Rate: 100.00%
- Average Response Time: 18463.21ms
- Throughput (Records per Second): 1.17


Search Performance  
- Total Search Queries: 118
- Success Rate: 17.80%
- Average Response Time: 28025.69ms
- Queries per Second: 0.66

#### Scenario 4:

- Description - 100 concurrent users with reranking disabled
- Report - [Scenario_4_report](stress_tests/scenario_4/stress_test_report_20250701_101507.md)

Ingestion Performance
- **Total Records (Papers) Processed**: 355
- **Success Rate**: 45.92%
- **Average Response Time**: 25059.99ms
- **Throughput (Records per Second)**: 2.00


Search Performance  
- **Total Search Queries**: 241
- **Success Rate**: 86.31%
- **Average Response Time**: 21520.53ms
- **Queries per Second**: 1.36




### 📝 Summary & Conclusion

- Disabling reranking increased the success rate of ingest and search requests as there was no blocking call from search requests. The throughput doubled in both ingest and search queries
- At 50 concurrent users with reranking enabled, all ingestion requests were successful with increased latency due to contention of the openai connections. But 73% search request failed to openai API rate limiting.
- At 100 concurrent users with reranking disabled, the ingestion success rate was just 46% due to rate limiting from openAI
- So, we can conclude that mindsDB knowledge is as good as the LLM APIs powering it. Though mindsdb itself doesn't have issues with memory, cpu usage, it's highly dependent on the LLM used for embedding and reranking.