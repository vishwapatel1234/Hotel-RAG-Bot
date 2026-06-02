"""
StayChat Hotel Assistant - Ingestion System Metadata Store
Compiles and serializes structured metadata maps for RAG audit and filtering loops.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger("StayChatMetadataStore")


class MetadataStore:
    """
    Metadata Registry Store.
    Compiles, structures, and serializes chunk metadata dictionaries to disk.
    """

    def __init__(self, output_path: Path) -> None:
        """
        Initializes the metadata store.
        
        Args:
            output_path: Target filesystem path to save metadata.json.
        """
        self.output_path = output_path
        # Ensure parent directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def generate_and_save(
        self,
        chunks: List[Dict[str, Any]],
        source_filename: str = "hotel_kb.json"
    ) -> None:
        """
        Processes a list of chunks, extracts the metadata schema, and serializes as JSON.
        
        Args:
            chunks: Chunks structures created by the chunker.
            source_filename: Original name of the raw knowledge source.
        """
        logger.info(f"Compiling metadata profiles for {len(chunks)} chunks...")
        
        metadata_map: Dict[str, Dict[str, Any]] = {}
        created_timestamp = datetime.utcnow().isoformat() + "Z"

        for idx, chunk in enumerate(chunks):
            chunk_id = chunk["chunk_id"]
            
            # Formulate the rigid metadata payload required by the system spec
            metadata_payload = {
                "chunk_id": chunk_id,
                "category": chunk["category"],
                "subsection": chunk["subsection"],
                "source_file": source_filename,
                "created_at": created_timestamp,
                "content_length": chunk["content_length"],
                "raw_text": chunk.get("raw_text", ""),
                # Store the contextual content string directly in metadata to allow easy text retrieval
                "content": chunk["content"]
            }
            
            # Map index number to payload to align exactly with FAISS vector indices
            metadata_map[str(idx)] = metadata_payload

        try:
            logger.info(f"Writing metadata registry file to: {self.output_path}")
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(metadata_map, f, indent=2, ensure_ascii=False)
            logger.info("Metadata file written successfully.")
        except Exception as e:
            logger.error(f"Failed to write metadata registry file: {e}")
            raise e
