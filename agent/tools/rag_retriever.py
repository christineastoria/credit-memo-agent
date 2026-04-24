"""
RAG retriever tool for searching internal research documents.

Loads markdown files from data/internal_docs/ into a Chroma vector store
and provides semantic search over them. This simulates an internal
knowledge base of prior credit research, committee notes, and analyst memos.
"""

import os
import glob

import chromadb
from langchain.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

# Path to internal research documents
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "internal_docs")

# Module-level variable — initialized by init_vector_store() before agent runs
_vector_store = None


def init_vector_store():
    """Load internal docs into a Chroma vector store.

    Must be called once at startup (from main.py) before the agent runs,
    so the vector store is ready when the tool is invoked in a thread.
    """
    global _vector_store

    # Read all markdown files from the internal docs directory
    docs_path = os.path.abspath(DOCS_DIR)
    md_files = glob.glob(os.path.join(docs_path, "*.md"))

    documents = []
    for filepath in md_files:
        with open(filepath, "r") as f:
            content = f.read()
        # Store the filename as metadata so we can cite the source
        documents.append({
            "content": content,
            "metadata": {
                "source": os.path.basename(filepath),
                "type": "internal_research"
            }
        })

    # Split documents into chunks for better retrieval precision
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )

    texts = []
    metadatas = []
    for doc in documents:
        chunks = splitter.split_text(doc["content"])
        for chunk in chunks:
            texts.append(chunk)
            metadatas.append(doc["metadata"])

    # Create an in-memory Chroma vector store with OpenAI embeddings
    client = chromadb.EphemeralClient()
    _vector_store = Chroma.from_texts(
        texts=texts,
        metadatas=metadatas,
        embedding=OpenAIEmbeddings(),
        client=client,
        collection_name="internal_research",
    )

    print(f"RAG vector store initialized with {len(texts)} chunks from {len(md_files)} documents.")


@tool
def rag_search(query: str) -> str:
    """Search internal research documents for prior analysis, credit notes,
    and committee memos relevant to a borrower or topic.

    Use this for:
    - Prior credit reviews for a borrower
    - Internal analyst notes and recommendations
    - Historical risk assessments
    - Previous committee decisions
    """
    if _vector_store is None:
        return "Error: Vector store not initialized. Call init_vector_store() first."

    # Retrieve the top 4 most relevant chunks
    results = _vector_store.similarity_search(query, k=4)

    if not results:
        return "No relevant internal documents found."

    # Format results with source attribution for citation tracking
    output_parts = []
    for i, doc in enumerate(results, 1):
        source = doc.metadata.get("source", "unknown")
        output_parts.append(
            f"[Internal Doc {i} — {source}]\n{doc.page_content}"
        )

    return "\n\n---\n\n".join(output_parts)
