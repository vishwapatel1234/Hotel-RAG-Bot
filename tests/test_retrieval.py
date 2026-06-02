"""
StayChat Grand Hotel Assistant - Retrieval Unit Tests
Tests embedding generation interfaces and FAISS vector indexing search metrics.
"""

import pytest
from pathlib import Path
from src.retrieval.embedder import EmbeddingGenerator
from src.retrieval.indexer import FAISSIndexManager


def test_embedder_interface():
    """Validates that the embedder exposes expected interface signatures."""
    embedder = EmbeddingGenerator(api_key="mock_key")
    vector = embedder.embed_query("test query")
    assert isinstance(vector, list)


def test_faiss_indexer_interface(tmp_path):
    """Validates FAISS Indexer interface boundaries under simulated filesystems."""
    embedder = EmbeddingGenerator(api_key="mock_key")
    index_path = tmp_path / "test.faiss"
    metadata_path = tmp_path / "test_meta.pkl"
    
    manager = FAISSIndexManager(
        embedder=embedder,
        index_path=index_path,
        metadata_path=metadata_path
    )
    
    # Check loaded status for non-existent indexes
    assert manager.load_index() is False
