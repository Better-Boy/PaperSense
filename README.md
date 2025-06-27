<h1>
  <img src="https://cdn-icons-png.flaticon.com/512/2541/2541988.png" alt="Logo" width="30" style="vertical-align: middle;">
  Papersense
</h1>
*Search smarter, Discover deeper.*

---

## 🚀 Overview

**PaperSense** is an intelligent semantic search engine for arXiv papers. Instead of relying on keyword or summary matches, PaperSense uses cutting-edge embeddings and neural search to help you find the most relevant academic papers—based on *meaning*, not just text.

Whether you're a researcher, student, or curious mind, PaperSense helps you explore the arXiv like never before.

- Demo Video - Check out Papersense in action on [Youtube](https://www.youtube.com)
- DevTo Article - My experience building Papersense [DevTo]()

---

## 🔍 Features

- 🔎 **Semantic Search**: Understands the context of your queries using large language models and vector embeddings.
- 🧬 **Supports Natural Language Queries**: Ask questions like *"papers on diffusion models in climate forecasting"*.
- 📚 **Real-Time arXiv Data**: Keeps your search results current with arXiv's latest updates.
- 🌐 **Clean Web UI**: Intuitive interface to search, explore, and read abstracts.
- 📈 **Ranking by Relevance**: Results ranked by semantic closeness—not just keyword count.
- 🧠 **Paper-Specific Chatbot**: Powered by MindsDB AI agents, enabling intelligent, context-aware conversations with individual research papers.


---

## 🛠️ Tech Stack

- **Frontend**: Javascript
- **Backend**: Python (FastAPI)
- **Embeddings**: OpenAI
- **Search Engine**: MindsDB & ChromaDB
- **Data Source**: [arXiv API](https://arxiv.org/help/api)
- **Python Linter** : [ruff](https://docs.astral.sh/ruff/)

---

## ⚙️ Installation

**Before running the application, go over the configuration settings once**

There are 2 ways to install.

## High Level Architecture

![architecture](assests/architecture.svg)

#### Manual Installation

1. Clone the repository

```bash
git clone https://github.com/Better-Boy/PaperSense
cd papersense
```

2. Install the required packages

```bash
pip install -r requirements.txt
```

3. Set your API keys as an environment variable

```bash
export OPENAI_API_KEY=your_key_here
```

Then run the server:

```bash
python run_webapp.py
```

#### Docker Installation

```bash
git clone https://github.com/Better-Boy/PaperSense
cd papersense
export OPENAI_API_KEY=your_key_here
docker-compose up --build
```

#### Configuration Settings

Refer [YAML Config Settings][/assests/yaml_config.md]

These settings are important for running and testing the app.

## 💡 Example Query

> “Recent breakthroughs in graph neural networks for molecular property prediction”

➡️ **PaperSense** returns the most relevant papers—even if those exact words don’t appear—because it understands your query semantically.

## Best practices followed

- Modular code
- Logging
- Config driven
- Benchmark and Stress testing
- Detailed documentation in README
- [ruff](https://github.com/astral-sh/ruff) linting and formatting

## Testing

For detailed instructions on benchmark testing refer [Benchmark](/assests/benchmark.md)
For detailed instructions on stress testing refer [Stress](/assests/stress.md)

## Quest Checklist

Refer [checklist](assests/checklist.md)

## 🧪 Roadmap

- [ ] Author-based filtering
- [ ] Citation graph view
- [ ] Personalized recommendations
- [ ] Save & tag favorite papers

---

### 🙏 Acknowledgments

```markdown

- [arXiv.org](https://arxiv.org/)
- [OpenAI](https://openai.com/)
- [MindsDB](https://mindsdb.com/)
```
