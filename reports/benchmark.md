## Benchmark Testing

### 🧪 Purpose of Benchmark Testing

This document outlines the performance benchmarking conducted on MindsDB knowledge bases. The goal is to test the system under various scenarios to evaluate speed, scalability, and stability.

If concurrent benchmarking is needed, refer to stress testing with low maximum concurrent users i.e keep it at 5-10 to simulate real life user under normal conditions.


### Data used for testing

1. Downloaded 12,000 arxiv pdf papers from different categories stored at Google Cloud Storage. For more info, refer the bulk access section [Kaggle Arxiv](https://www.kaggle.com/datasets/Cornell-University/arxiv)
2. The metadata related to the papers is downloaded from google cloud storage.
2. Downloading the raw pdfs from the google cloud storage took almost 2 hours.
3. Processed each pdf via a data processing pipeline. The pipeline code is [bulk_data_processing.py](../src/bulk_data_processing.py)
4. The data processing pipeline for the 12,000 pdfs ran for almost 4 hours.
5. The different data sizes i.e paper counts - 1k, 5k, 10k were stored. The size of the individual files are large and can be found at [Gdrive]()
6. A sample data is included in this repository - [sample test data](../data/test_data.json)

### How to run the benchmark testing script?

The configuration settings for benchmark settings are in the yaml file - [config.yaml](test/config.yaml). Though the config file contains `benchmark` and `stress` config, only relevant config will be picked by the script. In this case, `benchmark` and `mindsdb_infra`.

---
mindsdb_infra 

| Key           | Description                                | Example Value        |
|---------------|--------------------------------------------|----------------------|
| `host`        | URL of the MindsDB server host             | `http://127.0.0.1`   |
| `port`        | Port number used by the MindsDB server     | `47334`              |
| `mindsdb_pid` | Process ID of the running MindsDB instance | `410423`             |

---
benchmark 

| Key                | Description                                               | Example Value                                           |
|--------------------|-----------------------------------------------------------|---------------------------------------------------------|
| `data_size`        | Number of records to be used in the benchmark             | `500`                                                   |
| `test_data_path`   | File path to the test dataset in JSON format              | `/home/abhi/latest/PaperSense/data/test_data.json`     |
| `queries_file_path`| File path to the queries JSON file used for the benchmark | `/home/abhi/latest/PaperSense/data/queries.json`       |
| `output_dir`       | Directory where benchmark results will be stored          | `reports/benchmark_tests/scenario_1`                   |
| `iterations`       | Number of times the benchmark should run                  | `1`                                                     |

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
python test/benchmark.py
```

MindsDB pid has to be given in order to run the test script.

9. Once the test is complete, 3 files are created in the output directory mentioned at `benchmark.output_dir`.
    1. `resource_usage.png` - An image file that shows the mindsdb process resource usage
    2. `benchmark_test_report_<timestamp>.md` - The benchmark test report
    3. `activity.csv` - The resource utilization numbers of the mindsdb process collected during the test.


### Test Scenarios

Note:
- The knowledge base name, schema, embedding and reranking model for all the tests are kept same. This info can be found at each individual scenario report.
- I couldn't test with the 10k dataset because my OpenAI credits for the testing phase were exhausted.

#### Scenario 1:

- Description - Inserting and searching 1000 research papers
- Report - [Scenario 1](benchmark_tests/scenario_1/benchmark_test_report_20250701_083412.md)


#### Scenario 2:

- Description - Inserting 5000 research papers approx around 500MB of text data
- Benchmark report - [Scenario 2](benchmark_tests/scenario_2/benchmark_test_report_20250701_094318.md)


### 📝 Summary & Conclusion

1. Overall there was a high success rate in ingestion and searching but the latency was high.
2. Deletion of large knowledge bases take more time.
3. Creation was the fastest operation among all the four.
4. As more and more data gets added, search operations slow down - due to reranking using LLMs or vector search becomes slow.
5. Insertion of large texts in a single API call have higher latency than smaller texts.
6. Since I'm inserting a full research paper in a single call, the response times are higher. Chunking the entire research paper into smaller batches will lead to higher performance. For scenario 2, the average size of single record inserted was 9 MB (that too only text!!).


