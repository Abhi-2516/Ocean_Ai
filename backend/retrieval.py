# backend/retrieval.py
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

import chromadb
from chromadb.config import Settings, DEFAULT_TENANT, DEFAULT_DATABASE
import openai

# Configuration
PERSIST_DIRECTORY = "./chroma_db"
COLLECTION_NAME = "knowledge_base"
DEFAULT_TOPK = 3
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")  # change when you have another model

# Init Chroma persistent client
client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)
collection = client.get_collection(name=COLLECTION_NAME)

# Init OpenAI if key present
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
def retrieve_topk(query: str, top_k: int = DEFAULT_TOPK) -> List[Dict[str, Any]]:
    """
    Query Chroma collection and return a list of dicts:
      [{'doc_id': str, 'document': text, 'metadata': {...}, 'distance': float}, ...]
    Note: Chroma's query include arg must not request 'ids' (new API).
    We reconstruct a stable doc_id from metadata (source + chunk_index).
    """
    if not collection:
        return []

    res = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]  # no 'ids'
    )

    docs = []
    if res and len(res.get("documents", [])) > 0:
        documents = res["documents"][0]
        metadatas = res["metadatas"][0]
        distances = res.get("distances", [[]])[0]
        for i, doc in enumerate(documents):
            meta = metadatas[i] if i < len(metadatas) else {}
            # Reconstruct a stable id using metadata (falls back to index)
            src = meta.get("source", "unknown_source")
            idx = meta.get("chunk_index", i)
            doc_id = f"{src}__{idx}"
            docs.append({
                "doc_id": doc_id,
                "document": doc,
                "metadata": meta,
                "distance": distances[i] if i < len(distances) else None
            })
    return docs


def build_rag_prompt(query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
    """
    Build a clear prompt for the LLM containing:
      - a short instruction
      - the retrieved chunks with source metadata
      - the user query
    """
    header = ("You are an assistant that MUST use only the provided context to answer. "
              "If the context does not support an assertion, say 'Insufficient evidence in provided documents.'\n\n")
    context_lines = []
    for i, c in enumerate(retrieved_chunks, 1):
        src = c.get("metadata", {}).get("source", "unknown_source")
        idx = c.get("metadata", {}).get("chunk_index", "")
        context_lines.append(f"--- Chunk {i} (source: {src}, chunk_index: {idx}) ---\n{c.get('document')}\n")

    context_str = "\n".join(context_lines) if context_lines else "No context retrieved.\n"
    instruction = ("\n\nInstructions:\n1) Provide a one-line concise answer.\n"
                   "2) Then list up to 3 evidence bullets quoting the supporting chunk (include source filenames).\n"
                   "3) If you cannot answer from the context, say exactly: 'Insufficient evidence in provided documents.'\n")

    prompt = header + "CONTEXT:\n" + context_str + "\nUSER QUERY:\n" + query + "\n" + instruction
    return prompt

def call_llm(prompt: str, max_tokens: int = 400) -> Dict[str, str]:
    """
    Call OpenAI ChatCompletion and return {'ok':True, 'answer':str} or error info.
    If OPENAI_API_KEY is not set, return a helpful message indicating missing key.
    """
    if not OPENAI_API_KEY:
        return {"ok": False, "error": "OPENAI_API_KEY not configured. Set it in .env to get LLM answers."}

    try:
        resp = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.0,
        )
        answer = resp["choices"][0]["message"]["content"].strip()
        return {"ok": True, "answer": answer}
    except Exception as e:
        return {"ok": False, "error": str(e)}
