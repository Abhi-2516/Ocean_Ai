# backend/vector_store.py
import os
from pathlib import Path
import json
import uuid
from typing import List, Dict, Tuple

from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import numpy as np
from tqdm import tqdm

# Configuration
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
CHUNK_SIZE = 800            # characters per chunk (tweakable)
CHUNK_OVERLAP = 200         # overlap between chunks
PERSIST_DIRECTORY = "./chroma_db"
COLLECTION_NAME = "knowledge_base"

# Initialize embedding model and Chroma client
model = SentenceTransformer(EMBED_MODEL_NAME)
import chromadb
from chromadb.config import Settings, DEFAULT_TENANT, DEFAULT_DATABASE

# Use PersistentClient for local persistent DB (creates PERSIST_DIRECTORY if missing)
client = chromadb.PersistentClient(
    path=PERSIST_DIRECTORY,
    settings=Settings(),
    tenant=DEFAULT_TENANT,
    database=DEFAULT_DATABASE,
)


def parse_file(path: str) -> str:
    """Extract text from supported file types: .html, .md, .txt, .json.
       Returns raw text."""
    p = Path(path)
    suffix = p.suffix.lower()
    text = ""
    if suffix in [".md", ".txt"]:
        text = p.read_text(encoding="utf-8")
    elif suffix == ".html" or suffix == ".htm":
        html = p.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        # Remove script/style
        for s in soup(["script", "style"]):
            s.decompose()
        text = soup.get_text(separator="\n")
    elif suffix == ".json":
        raw = json.loads(p.read_text(encoding="utf-8"))
        # Flatten simple json to string
        text = json.dumps(raw, indent=2)
    else:
        raise ValueError(f"Unsupported file type: {suffix} for file {path}")
    # Normalize whitespace
    return "\n".join([line.strip() for line in text.splitlines() if line.strip()])

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Simple character-wise chunker with overlap."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
        if start < 0:
            start = 0
        if start >= len(text):
            break
    return chunks

def ensure_collection():
    """Get or create chroma collection."""
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        collection = client.create_collection(name=COLLECTION_NAME)
    return collection

def ingest_files(file_paths: List[str]) -> Dict:
    """Main ingestion function: parse files, chunk, embed, and add to Chroma."""
    docs = []
    metadatas = []
    ids = []

    for fp in file_paths:
        print(f"Parsing: {fp}")
        try:
            text = parse_file(fp)
        except Exception as e:
            print(f"Failed to parse {fp}: {e}")
            continue

        chunks = chunk_text(text)
        for i, c in enumerate(chunks):
            doc_id = f"{Path(fp).name}__{i}__{uuid.uuid4().hex[:8]}"
            docs.append(c)
            metadatas.append({"source": Path(fp).name, "chunk_index": i, "origin_path": str(fp)})
            ids.append(doc_id)

    if not docs:
        return {"status": "no_documents", "added": 0}

    print(f"Encoding {len(docs)} chunks with model {EMBED_MODEL_NAME} ...")
    embeddings = model.encode(docs, show_progress_bar=True, convert_to_numpy=True)

    collection = ensure_collection()

    # If the collection already has items with same ids, we should remove them first (idempotency)
    try:
        existing_ids = [m["id"] for m in collection.get(include=["id"]).get("id", [])] if False else []
    except Exception:
        existing_ids = []

    print(f"Adding {len(docs)} chunks to Chroma collection '{COLLECTION_NAME}' (persist dir: {PERSIST_DIRECTORY}) ...")
    collection.add(
        documents=docs,
        metadatas=metadatas,
        ids=ids,
        embeddings=embeddings.tolist() if isinstance(embeddings, np.ndarray) else embeddings
    )

    # Persist DB to disk
    try:
        client.persist()
    except Exception:
        pass

    return {"status": "ok", "added": len(docs)}
