# 🧠 PaperSense  
**Semantic Search for Scientific Papers on arXiv**  
*Search smarter. Discover deeper.*

---

![papersense-banner](https://cdn-icons-png.flaticon.com/512/2541/2541988.png) <!-- Optional: Add a banner -->

## 🚀 Overview

**PaperSense** is an intelligent semantic search engine for arXiv papers. Instead of relying on keyword or summary matches, PaperSense uses cutting-edge embeddings and neural search to help you find the most relevant academic papers—based on *meaning*, not just text.

Whether you're a researcher, student, or curious mind, PaperSense helps you explore the arXiv like never before.

---

## 🔍 Features

- 🔎 **Semantic Search**: Understands the context of your queries using large language models and vector embeddings.
- 🧬 **Supports Natural Language Queries**: Ask questions like *"papers on diffusion models in climate forecasting"*.
- 📚 **Real-Time arXiv Data**: Keeps your search results current with arXiv's latest updates.
- 🌐 **Clean Web UI**: Intuitive interface to search, explore, and read abstracts.
- 📈 **Ranking by Relevance**: Results ranked by semantic closeness—not just keyword count.

---

## 🛠️ Tech Stack

- **Frontend**: Javascript
- **Backend**: Python (FastAPI)
- **Embeddings**: OpenAI
- **Search Engine**: MindsDB & ChromaDB
- **Data Source**: [arXiv API](https://arxiv.org/help/api)

---

## ⚙️ Installation

```bash
git clone https://github.com/Better-Boy/PaperSense
cd papersense
pip install -r requirements.txt
```

Set your API keys as an environment variable

```bash
export OPENAI_API_KEY=your_key_here
```

Then run the server:

```bash
python main.py
```

## 💡 Example Query

> “Recent breakthroughs in graph neural networks for molecular property prediction”

➡️ **PaperSense** returns the most relevant papers—even if those exact words don’t appear—because it understands your query semantically.

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
