# Quest 19 Checklist

### **🛠️ [40 pts] Build an app with KBs**  

Build a functional application (CLI, Web App, API, Bot Interface etc.) where the primary interaction or feature relies on the semantic query results from the KB. To claim these points make sure:

- [x] Your app executes [🔗 `CREATE KNOWLEDGE_BASE`](https://docs.mindsdb.com/mindsdb_sql/knowledge-bases#create-knowledge-base-syntax)
- [x] Your app ingests data using [🔗 `INSERT INTO knowledge_base`](https://docs.mindsdb.com/mindsdb_sql/knowledge-bases#insert-into-syntax)
- [x] Your app retrieves relevant data based on on semantic queries [🔗 `SELECT ... FROM ... WHERE content LIKE '<query>'`](https://docs.mindsdb.com/mindsdb_sql/knowledge-bases#select-from-kb-syntax)
- [x] Your app uses [🔗 `CREATE INDEX ON KNOWLEDGE_BASE`](https://docs.mindsdb.com/mindsdb_sql/knowledge-bases#create-index-on-knowledge-base-syntax)

---

### **🛠️ [10 pts]  Use metadata columns**  

- [x] Define [🔗 `metadata_columns`](https://docs.mindsdb.com/mindsdb_sql/knowledge-bases#metadata-columns) during ingestion and use `WHERE` clauses that combine semantic search with SQL attribute filtering on `metadata_columns`.

---

### **🛠️ [10 pts] Integrate JOBS**

- [x] Set up a [🔗 `MindsDB JOB`](https://docs.mindsdb.com/rest/jobs/create#create-a-job) that periodically checks a data source and inserts *new* data into the KB (using LAST or similar logic).

---

### **🛠️ [10 pts] Integrate with AI Tables or Agents** 

- [x] Build a multi-step workflow within MindsDB by taking the results from a KB semantic query and feeding them as input into another [🔗 `MindsDB AI Table`](https://docs.mindsdb.com/generative-ai-tables#what-are-generative-ai-tables) (e.g., for summarisation, classification, generation).

---

### **✍️ [30 pts] Upload a video and write a nice README**  

You can claim this if:

- [x] You upload a short video demo explaining the app & showcasing the KB interaction.
- [x] Your project has a `README.md` with clear setup instructions.

---

### **✍️ [5 pts] Document the process and showcase your app** 

- [x] Write an article on DevTo, HashNode, Medium, or any blogging platform of your choice to document how you built this app and to showcase the practical product use cases for these features.

---

### **✍️ [5 pts] Give feedback and suggest features**

- [x] You submit the [🔗 Product Feedback Form](https://quira-org.typeform.com/to/magewvh9). Extra points might be given here if you suggest really good features 😉

---

### **🎁 [10 pts] Integreate `CREATE Agent`**

- [x] Projects that integrate [`CREATE Agent`](https://docs.mindsdb.com/mindsdb_sql/agents/agent) will be rewarded with an additional 10 points.

---

### **🎁  [10 pts] Secret Challenge #2**

- [x] Use [`EVALUATE KNOWLEDGE_BASE`](https://docs.mindsdb.com/mindsdb_sql/knowledge-bases#evaluate-knowledge-base-syntax) to evaluate the relevancy and accuracy of the documents and data returned by the knowledge base.

---

### ** 🏷️ Performance Benchmarking**

- [ ] Create a reproducible benchmark report to provide concrete performance numbers for specific scenarios. For example, select a reasonably sized dataset (e.g., 10k, 100k, 1M+ rows, specify size), document their test environment (hardware/cloud specs, MindsDB version/config), methodology (e.g., script used), and report clear metrics (e.g., total ingestion time, time per 1k records, average/p95/p99 query latency over N queries of varying complexity).

---

### ** 🏷️ Stress Testing**

- [ ] Stress-test the system by systematically increasing load. For example, by using very large datasets, a high number of concurrent queries, or deeply nested/complex semantic queries, until KB operations either fail or exhibit unacceptable latency. Create a report to document the configuration used, load parameters, sequence of steps executed, and the observed failure mode or point of performance degradation.

