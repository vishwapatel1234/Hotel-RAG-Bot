"""
StayChat Hotel Assistant - Retrieval Engine Service
Handles intent classification, query embeddings, FAISS/Lexical searches, and metadata reconstruction.
"""

import re
import numpy as np
import faiss
import pickle
import json
import logging
from typing import List, Dict, Any, Tuple, Literal
from pathlib import Path

from config import config
from services.embedding_service import EmbeddingService
from services.confidence import ConfidenceEngine

logger = logging.getLogger("StayChatRetrieval")


class RetrievalService:
    """
    Production Retrieval Service Engine.
    Handles early-stage intent routing, vector database querying, and post-search diagnostic audits.
    """

    def __init__(self, embedding_service: EmbeddingService) -> None:
        """
        Initializes the Retrieval Service.
        
        Args:
            embedding_service: Initialized EmbeddingService helper.
        """
        self.embedding_service = embedding_service
        self.confidence_engine = ConfidenceEngine(confidence_threshold=0.70)
        self._index: Any = None
        self._metadata: List[Dict[str, Any]] = []

        # Load database records
        self._initialize_resources()

    def _initialize_resources(self) -> None:
        """Loads FAISS index binary and metadata dictionary registry into memory."""
        logger.info("Initializing vector search indices...")
        
        # Load metadata JSON registry
        if config.metadata_path.exists():
            try:
                with open(config.metadata_path, "r", encoding="utf-8") as f:
                    metadata_dict = json.load(f)
                
                # Reconstruct list from metadata JSON dict keys
                self._metadata = [metadata_dict[str(i)] for i in range(len(metadata_dict))]
                logger.info(f"Loaded {len(self._metadata)} metadata records successfully.")
            except Exception as e:
                logger.error(f"Failed to parse metadata file: {e}")
                
        # Load FAISS index file
        if config.index_path.exists():
            try:
                self._index = faiss.read_index(str(config.index_path))
                logger.info(f"Successfully loaded FAISS CPU Index with {self._index.ntotal} vectors.")
            except Exception as e:
                logger.error(f"Failed to read FAISS index: {e}")
        else:
            logger.warning("FAISS Index FlatL2 file not found on disk. Search will fall back to Lexical Engine.")

    @staticmethod
    def classify_intent(query: str) -> Literal["knowledge_query", "staff_command", "escalation_request"]:
        """
        Filters user inputs, classifying query targets to implement retrieval bypass boundaries.
        
        Args:
            query: Raw user input text.
            
        Returns:
            Literal: Intent category string.
        """
        query_cleaned = query.strip().lower()

        # 1. Check for operational operator commands
        if query_cleaned.startswith("#"):
            return "staff_command"

        # 2. Check for escalation prompts
        escalation_keywords = [
            "talk to human", "connect to staff", "human assistance",
            "manager", "operator", "helpdesk", "support agent", "insan se baat"
        ]
        if any(kw in query_cleaned for kw in escalation_keywords):
            return "escalation_request"

        return "knowledge_query"

    @staticmethod
    def _get_tokens(text: str) -> set:
        """Helper to extract normalized lowercase alphanumeric word tokens, filtering out stop words."""
        # Standard structural stop words to prevent false positive matches on filler vocabulary
        # Includes Romanized Hinglish conversational auxiliary/question particles to prevent token score dilution
        STOP_WORDS = {
            "the", "what", "how", "who", "are", "and", "for", "with", "has", "its", "from", 
            "does", "did", "can", "you", "your", "that", "this", "these", "those", "have", 
            "been", "was", "were", "had", "will", "would", "should", "shall", "may", "might", 
            "must", "about", "above", "after", "again", "against", "all", "any", "both", "each", 
            "few", "more", "most", "other", "some", "such", "than", "too", "very", "hotel", 
            "staychat", "grand", "kitne", "baje", "hai", "kya", "milega", "dikhao", "par", 
            "se", "ko", "mein", "hoga", "sakte", "aap", "kab", "kaha", "ka", "kuch", "he", 
            "batao", "bataiye", "kar", "karein", "hain", "hoon", "dijiye", "much", "many",
            "please", "tell", "give", "show", "details", "information", "available", "time",
            "times", "hour", "hours"
        }
        # Normalize checkout/check-out and checkin/check-in phrases to guarantee syntax alignment
        normalized = text.lower().replace("₹", "").replace("-", " ")
        normalized = normalized.replace("checkout", "check out").replace("checkin", "check in")
        # Normalize airport shuttle to airport transfer
        normalized = normalized.replace("shuttle", "transfer")
        words = normalized.split()
        
        # Strip punctuation including brackets to clean up metadata headers
        tokens = {w.strip(".,;:?!()\"'[]{}") for w in words}
        
        # Apply lightweight stemming to match common noun and verb variants
        stemmed = []
        for word in tokens:
            if not word or len(word) <= 2 or word in STOP_WORDS:
                continue
            if word.endswith("ments") or word.endswith("ment"):
                word = word.replace("ments", "").replace("ment", "") # payments -> pay
            elif word.endswith("ing") and len(word) > 5:
                word = word[:-3] # booking -> book
            elif word.endswith("s") and not word.endswith("ss") and len(word) > 3:
                word = word[:-1] # costs -> cost, rooms -> room
            # Normalize check-in/check-out mappings
            if word in ("checkout", "check-out"):
                word = "check out"
            if word in ("checkin", "check-in"):
                word = "check in"
            
            if word and len(word) > 2 and word not in STOP_WORDS:
                stemmed.append(word)
                
        return set(stemmed)

    def _lexical_search_fallback(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Executes a high-performance local lexical overlap match.
        Used when running in Developer/Mock mode without active Gemini API keys.
        
        Implements Entity Keyword Boosting to solve numerical price confusion.
        """
        logger.debug(f"Executing local lexical fallback search for query: '{query}'")
        
        # Simple query translation for Devanagari characters in mock/lexical fallback mode
        if any(ord(char) >= 0x0900 and ord(char) <= 0x097F for char in query):
            translations = {
                "चेक आउट": "check out",
                "चेक इन": "check in",
                "समय": "time",
                "रूम": "room",
                "कमरा": "room",
                "पूल": "pool",
                "कीमत": "price",
                "किराया": "price"
            }
            translated_query = query
            for hindi_word, eng_word in translations.items():
                if hindi_word in translated_query:
                    translated_query = translated_query.replace(hindi_word, eng_word)
            logger.info(f"Translated Devanagari query '{query}' to '{translated_query}' for lexical matching.")
            query = translated_query

        query_tokens = self._get_tokens(query)
        if not query_tokens:
            return []

        results = []
        query_lower = query.lower()

        # Specific room entity mappings to isolate pricing lookups
        target_entities = {
            "standard": ["standard"],
            "deluxe": ["deluxe"],
            "executive": ["executive"],
            "family": ["family"],
            "suite": ["suite"],
            "presidential": ["presidential"],
            "extra bed": ["extra", "bed"]
        }

        active_room_entities = [
            ent for ent, kws in target_entities.items()
            if all(kw in query_lower for kws in kws for kw in kws)
        ]

        for idx, chunk in enumerate(self._metadata):
            chunk_content = chunk["content"]
            chunk_tokens = self._get_tokens(chunk_content)
            
            intersection = query_tokens.intersection(chunk_tokens)
            if not intersection:
                continue

            score = len(intersection) / len(query_tokens)

            # Apply room keyword boosting & cross-entity penalties to eliminate pricing mix-ups
            for entity in active_room_entities:
                chunk_raw_lower = chunk.get("raw_text", "").lower()
                if entity == "extra bed":
                    if "extra bed" in chunk_raw_lower:
                        score += 5.0
                else:
                    if entity in chunk_raw_lower:
                        score += 10.0
                    elif any(other_room in chunk_raw_lower for other_room in ["standard", "deluxe", "executive", "family", "suite"] if other_room != entity):
                        score -= 5.0  # Penalize cross-matches

            # Apply strict primary room-type isolation to prevent mismatching unlisted/different room types
            primary_rooms = ["standard", "deluxe", "executive", "family", "presidential"]
            active_primaries = [r for r in primary_rooms if r in query_lower]
            chunk_raw_lower = chunk.get("raw_text", "").lower()
            if active_primaries:
                chunk_primaries = [r for r in primary_rooms if r in chunk_raw_lower]
                if chunk_primaries and not any(r in active_primaries for r in chunk_primaries):
                    score -= 20.0

            # Apply strict service-topic isolation (wedding vs corporate event) to prevent cross-matching services
            service_topics = ["wedding", "corporate"]
            active_services = [s for s in service_topics if s in query_lower]
            if active_services:
                if any(s in chunk_raw_lower for s in active_services):
                    score += 10.0
                elif any(other_service in chunk_raw_lower for other_service in service_topics if other_service not in active_services):
                    score -= 20.0

            results.append({
                "chunk_id": chunk["chunk_id"],
                "category": chunk["category"],
                "subsection": chunk["subsection"],
                "content": chunk["content"],
                "raw_text": chunk.get("raw_text", ""),
                "score": score,
                "source_section": f"{chunk['category']}/{chunk['subsection']}"
            })

        # Sort matches by relevance score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Enforce absolute confidence capping [0.0, 1.0] without scaling weak overlap matches
        for item in results:
            item["score"] = min(1.0, max(0.0, item["score"]))

        return results[:top_k]

    def retrieve(self, query: str, top_k: int = 4) -> Dict[str, Any]:
        """
        Coordinates the ingestion classification, embeds query, queries FAISS/Lexical index,
        reconstructs metadata, normalizes scores, and audits with the confidence engine.
        
        Args:
            query: Raw user query string.
            top_k: Number of adjacent documents to return.
            
        Returns:
            Dict: Grounded context list and diagnostic audit results.
        """
        logger.info(f"Retrieve request received: '{query}'")
        
        # 1. Validate Input
        if not query.strip():
            logger.warning("Empty query received. Returning empty retrieval.")
            return {
                "intent": "knowledge_query",
                "chunks": [],
                "diagnostics": {
                    "query": "",
                    "retrieved_chunks": 0,
                    "top_score": 0.0,
                    "threshold": 0.70,
                    "status": "low_confidence",
                    "reason": "Empty search query"
                }
            }

        # 2. Intent-Aware Routing (Bypasses FAISS)
        intent = self.classify_intent(query)
        logger.info(f"Intent classified: '{intent}'")

        if intent != "knowledge_query":
            logger.info("Retrieval bypassed due to operational command or human escalation intent.")
            return {
                "intent": intent,
                "chunks": [],
                "diagnostics": {
                    "query": query,
                    "retrieved_chunks": 0,
                    "top_score": 1.0,
                    "threshold": 0.70,
                    "status": "high_confidence"
                }
            }

        # 3. Vector Similarity Search vs. Lexical Fallback Execution
        # If API key is mock or FAISS is missing, trigger the Lexical engine
        is_mock = config.api_key == "your-gemini-api-key-here" or config.api_key == "mock_key"
        
        if is_mock or self._index is None:
            retrieved_chunks = self._lexical_search_fallback(query, top_k)
        else:
            try:
                # Call Gemini to embed query using task_type='retrieval_query' (Required for query retrieval!)
                import google.generativeai as genai
                response = genai.embed_content(
                    model=config.embedding_model,
                    content=query,
                    task_type="retrieval_query"
                )
                query_vector = np.array(response["embedding"]).astype("float32").reshape(1, -1)
                
                # Execute exhaustive L2 distance similarity search in FAISS
                distances, indexes = self._index.search(query_vector, top_k)
                
                retrieved_chunks = []
                for idx, dist in zip(indexes[0], distances[0]):
                    if idx == -1 or idx >= len(self._metadata):
                        continue
                        
                    # Reconstruct Metadata structure from the mapping
                    chunk = self._metadata[idx]
                    
                    # Convert L2 Euclidean Distance into true Cosine Similarity score
                    # For normalized embeddings, Cosine Similarity = 1 - (L2^2 / 2)
                    normalized_score = 1.0 - (float(dist) / 2.0)
                    
                    retrieved_chunks.append({
                        "chunk_id": chunk["chunk_id"],
                        "category": chunk["category"],
                        "subsection": chunk["subsection"],
                        "content": chunk["content"],
                        "raw_text": chunk.get("raw_text", ""),
                        "score": normalized_score,
                        "source_section": f"{chunk['category']}/{chunk['subsection']}"
                    })
            except Exception as e:
                logger.error(f"Vector search failed: {e}. Falling back to Lexical search...", exc_info=True)
                retrieved_chunks = self._lexical_search_fallback(query, top_k)

        # 4. Check retrieval results count
        if not retrieved_chunks:
            logger.warning("Zero search matches compiled during index search.")
            return {
                "intent": "knowledge_query",
                "chunks": [],
                "diagnostics": {
                    "query": query,
                    "retrieved_chunks": 0,
                    "top_score": 0.0,
                    "threshold": 0.70,
                    "status": "low_confidence",
                    "reason": "No relevant evidence located in knowledge database."
                }
            }

        # 5. Hybrid Confidence Verification
        top_match = retrieved_chunks[0]
        confidence_report = self.confidence_engine.evaluate(query, top_match)
        
        # 6. Compile Retrieval Diagnostic Output
        diagnostics = {
            "query": query,
            "retrieved_chunks": len(retrieved_chunks),
            "top_score": top_match["score"],
            "threshold": self.confidence_engine.confidence_threshold,
            "status": confidence_report["status"],
            "expected_category": confidence_report.get("expected_category"),
            "retrieved_category": confidence_report.get("retrieved_category")
        }
        
        if confidence_report["status"] == "low_confidence":
            diagnostics["reason"] = confidence_report["reason"]

        logger.info(f"Retrieval finalized. Status: {diagnostics['status']} (Top score: {diagnostics['top_score']:.2f})")

        return {
            "intent": "knowledge_query",
            "chunks": retrieved_chunks,
            "diagnostics": diagnostics
        }
