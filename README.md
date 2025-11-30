# Ocean.AI — RAG Testcase & Script Demo

> A lightweight end‑to‑end RAG + Automation demo that:
>
> * ingests text/HTML assets into a local Chroma vector DB
> * retrieves grounding chunks for a query
> * generates grounded testcases (discounts, shipping, etc.)
> * generates runnable Selenium test scripts from a selected testcase (local or via backend)
>
> This README is ready for your repository.

---

## **1. Features**

* Local ingestion into Chroma vector DB using Sentence Transformers.
* RAG-style retrieval for nearest grounding chunks.
* Fully deterministic rule-based testcase generator (no paid LLM required).
* Selenium script generator that auto-detects coupon inputs in checkout HTML.
* Streamlit UI for uploading files, ingestion, querying, testcase and script generation.
* Optional LLM toggle for expansion (if user later adds API keys).

---

## **2. Project Architecture**

```
[Streamlit UI]  <-->  [FastAPI Backend]
                        |
                        +--> [Chroma Vector DB]
                        +--> [Retrieval + RAG]
                        +--> [agent_tools.py]
                        +--> [Selenium Script Generator]
```

---

## **3. Requirements**

### **System**

* Windows / macOS / Linux
* Python 3.10+ recommended
* Google Chrome (for Selenium execution)

### **Python Dependencies**

Installed using:

```
pip install -r requirements.txt
```

Major packages:

* FastAPI
* Uvicorn
* Streamlit
* ChromaDB
* Sentence-Transformers
* Selenium
* Webdriver-Manager
* BeautifulSoup4

---

## **4. Folder Structure**

```
Ocean.AI/
├── assets/                 # uploaded HTML/TXT files
│   ├── example.txt
│   └── checkout.html
│
├── backend/
│   ├── app.py              # FastAPI endpoints
│   ├── ingest_runner.py    # ingestion script
│   ├── retrieval.py        # RAG retrieval logic
│   ├── vector_store.py     # Chroma handling
│   └── agent_tools.py      # testcase + script generator
│
├── streamlit_ui/
│   └── app.py              # Streamlit UI
│
├── tests/
│   └── generated_test_*.py # generated selenium tests
│
├── chroma_db/              # persisted vector DB
├── requirements.txt
└── README.md
```

---

## **5. Local Setup (Windows)**

### **1. Create Virtual Environment**

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### **2. Start Backend**

```
uvicorn backend.app:app --reload --port 8000
```

### **3. Start UI**

Open a second terminal:

```
.\.venv\Scripts\Activate.ps1
streamlit run streamlit_ui/app.py
```

UI opens at: **[http://localhost:8501](http://localhost:8501)**

---

## **6. Phase-based Workflow**

### **Phase 1 — Upload Assets**

Upload files like:

* `checkout.html`
* `example.txt`

### **Phase 2 — Ingest**

Click **Ingest saved assets now** in the UI.
Backend loads files → extracts chunks → stores embeddings in Chroma.

### **Phase 3 — Generate Testcases**

Enter query such as:

```
discount code
```

View:

* Retrieved chunks
* Generated testcases

### **Phase 4 — Generate Selenium Script**

Select a testcase → paste checkout HTML (or use assets) → click generate.
Download generated script automatically.

### **Phase 5 — Run Script**

From terminal:

```
python tests/generated_test_<ID>.py
```

You should see:

```
TEST PASSED: Discount message found on page.
```

---

## **7. API Examples**

### **Generate Testcases**

```
curl -X POST http://127.0.0.1:8000/generate_testcases \
  -H "Content-Type: application/json" \
  -d '{"query":"discount code","top_k":3}'
```

### **Generate Script (PowerShell)**

Create `payload.json` and call:

```
Invoke-RestMethod -Uri "http://127.0.0.1:8000/generate_script" -Method Post -Body (Get-Content payload.json -Raw) -ContentType "application/json"
```

---

## **8. Deployment Options**

### **Streamlit Cloud + Render Backend**

* Deploy backend to Render/Railway/Fly.io
* Deploy Streamlit UI to Streamlit Cloud
* Set `backend_url` in `.streamlit/secrets.toml`:

```
backend_url = "https://your-backend.onrender.com"
```

### **Docker (optional)**

A Dockerfile can be added for full container-based deploy.

---

## **9. Troubleshooting**

### ❌ Backend connection refused

Backend not running. Run:

```
uvicorn backend.app:app --reload --port 8000
```

### ❌ Script returned None

Your HTML file does not contain coupon input fields like:

```
<input id="coupon_input">
<button id="apply_coupon">
```

Add them or paste correct HTML.

### ❌ Unexpected UTF-8 BOM

Re-save file using:

```
[System.IO.File]::WriteAllText("file.json", (Get-Content file.json -Raw), (New-Object System.Text.UTF8Encoding($false)))
```

### ❌ Selenium driver not working

Update Chrome or Webdriver-Manager.

---




