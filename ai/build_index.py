"""
StayChat Hotel Assistant - Ingestion System Orchestrator
Coordinates the complete ETL ingestion loop, compiles the FAISS index, and saves metadata.
"""

import sys
import logging
import numpy as np
import faiss
from pathlib import Path

from config import config
from services.validator import KnowledgeBaseValidator, DataValidationError
from services.chunker import SemanticChunker
from services.embedding_service import EmbeddingService
from services.metadata_store import MetadataStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("StayChatIngestionPipeline")


def run_pipeline() -> None:
    """Coordinates and executes the end-to-end data ingestion and vector indexing pipeline."""
    logger.info("Starting StayChat RAG Ingestion Pipeline...")
    
    # 1. Load and Validate Raw Knowledge Base
    try:
        raw_data = KnowledgeBaseValidator.validate_file(config.kb_path)
    except DataValidationError as e:
        logger.error(f"Integrity Check Failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected file error: {e}")
        sys.exit(1)

    # 2. Semantic Chunking & Token-Deduplication
    chunker = SemanticChunker(deduplication_threshold=0.65)
    chunks = chunker.chunk_dataset(raw_data)
    
    if not chunks:
        logger.error("Abort Ingestion: No valid unique facts compiled after chunking phase.")
        sys.exit(1)

    # 3. Generate Vector Embeddings
    chunk_texts = [chunk["content"] for chunk in chunks]
    
    # Check if we should execute in Real API vs. Developer Mock mode
    is_mock = config.api_key == "your-gemini-api-key-here" or config.api_key == "mock_key"
    
    if is_mock:
        logger.warning(
            "Gemini API key is placeholder or missing. "
            "Running ingestion in DEVELOPER MOCK MODE with synthetic vectors."
        )
        # Generate synthetic float vectors of dimension 768 using uniform distribution
        vectors = [list(np.random.uniform(-0.1, 0.1, config.embedding_dimension)) for _ in chunks]
    else:
        logger.info("Initializing active Google Gemini embedding service...")
        try:
            embedder = EmbeddingService(api_key=config.api_key, model_name=config.embedding_model)
            vectors = embedder.generate_embeddings_batch(chunk_texts, batch_size=config.batch_size)
        except Exception as e:
            logger.error(f"API Vectorization Failed: {e}", exc_info=True)
            sys.exit(1)

    # 4. Generate & Save Metadata Registry
    meta_store = MetadataStore(output_path=config.metadata_path)
    meta_store.generate_and_save(chunks, source_filename=config.kb_path.name)

    # 5. Build and Persist FAISS CPU Index
    logger.info("Building FAISS vector index...")
    
    # Convert lists to float32 numpy matrix
    vectors_matrix = np.array(vectors).astype("float32")
    
    # Instantiate the recommended IndexFlatL2 (ideal for small facts database, 100% recall)
    index = faiss.IndexFlatL2(config.embedding_dimension)
    
    # Add vectors to index
    logger.info(f"Adding {vectors_matrix.shape[0]} vectors of dimension {vectors_matrix.shape[1]} to index...")
    index.add(vectors_matrix)
    
    # Save the index file locally
    try:
        logger.info(f"Serializing and saving FAISS index to: {config.index_path}")
        faiss.write_index(index, str(config.index_path))
    except Exception as e:
        logger.error(f"Failed to serialize FAISS index: {e}")
        sys.exit(1)

    # 6. Output Ingestion Success Summary
    print("\n" + "=" * 57)
    print("                 INDEX BUILT SUCCESSFULLY")
    print("=" * 57)
    print(f"Total chunks processed : {len(chunks)}")
    print(f"Embedding dimensions   : {config.embedding_dimension}")
    print(f"FAISS Index file size  : {config.index_path.stat().st_size} bytes")
    print(f"Metadata registry size : {config.metadata_path.stat().st_size} bytes")
    if is_mock:
        print("Pipeline Status        : SUCCESSFUL (Developer Mock Mode)")
    else:
        print("Pipeline Status        : SUCCESSFUL (Production Real Vector Index)")
    print("=" * 57 + "\n")


if __name__ == "__main__":
    run_pipeline()
