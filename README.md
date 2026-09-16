# 🧠 Second Brain — Local AI Knowledge Vault

A fast, 100% offline, and zero-cost personal knowledge management (PKM) workspace inspired by Google's NotebookLM and Tiago Forte's Building a Second Brain (CODE framework).

Unlike traditional RAG tools that dump everything into a vector database, this system enforces a **strict dual-memory architecture**:
- **Episodic / Procedural Memory (SQLite):** Exact dates, deadlines, and structured events queried directly with relational SQL.
- **Associative Semantic Memory (`sqlite-vec`):** Paragraphs and conceptual knowledge embedded into 384-dimensional dense vectors using local FastEmbed ONNX runtime.
- **Cognitive Router:** Classifies user intent (`SCHEDULE`, `CONCEPT`, `WEB`) *before* retrieval.
- **Background Reflex:** An asynchronous listener that extracts temporal deadlines and events from casual conversation without blocking the user.

---

## 🚀 Key Features

- **In-Notes Semantic Search:** Chat directly with your notes using local dense vector retrieval.
- **Autonomous Task Extraction:** Mention *"I have my TCS interview in 10 days"*, and it automatically logs the deadline into SQLite.
- **Free Live Web Search:** Integrated zero-key web search fallback via DuckDuckGo.
- **100% Free & Private:** Runs completely on your local machine using Ollama (`qwen2.5-coder:7b`) and ONNX Runtime. No cloud APIs or subscriptions required.

---

## 🛠️ Tech Stack

- **Backend:** Python, FastAPI, Uvicorn, SQLite3, `sqlite-vec`, `fastembed`, `ddgs`, `ollama`
- **Frontend:** Vanilla HTML5, Tailwind CSS, REST & SSE
- **Package Manager:** `uv`

---

## ⚡ Quick Start

### 1. Prerequisites
- Install [Ollama](https://ollama.com) and pull the model:
  ```bash
  ollama run qwen2.5-coder:7b