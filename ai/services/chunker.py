"""
StayChat Hotel Assistant - Ingestion System Chunker
Performs atomic semantic node chunking, token-deduplication, and context-enrichment.
"""

import hashlib
import logging
from typing import Dict, Any, List, Set

logger = logging.getLogger("StayChatChunker")


class SemanticChunker:
    """
    Atomic Semantic Node Chunker.
    Parses categories in isolation to prevent context leakage, maps records to subsections,
    and applies a Jaccard token-deduplication filter to eliminate redundancy bloat.
    """

    def __init__(self, deduplication_threshold: float = 0.65) -> None:
        """
        Initializes the chunker.
        
        Args:
            deduplication_threshold: Jaccard similarity limit above which chunks are skipped as redundant.
        """
        self.deduplication_threshold = deduplication_threshold

    @staticmethod
    def _determine_subsection(text: str) -> str:
        """Helper to map a fact to its granular sub-topic using keyword heuristics."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["cancell", "no-show", "refund"]):
            return "cancellation"
        if any(kw in text_lower for kw in ["check-in", "check-out", "late", "early", "hour"]):
            return "hours"
        if any(kw in text_lower for kw in ["breakfast", "dinner", "lunch", "dine", "dining", "kitchen", "lounge", "buffet"]):
            return "dining"
        if any(kw in text_lower for kw in ["pool", "swimming", "gym", "fitness", "spa", "sauna", "steam"]):
            return "recreation"
        if any(kw in text_lower for kw in ["wifi", "internet", "high-speed"]):
            return "internet"
        if any(kw in text_lower for kw in ["airport", "taxi", "metro", "transfer", "chauffeur", "car"]):
            return "transportation"
        if any(kw in text_lower for kw in ["card", "visa", "mastercard", "amex", "rupay", "upi", "cash", "payment"]):
            return "payments"
        if any(kw in text_lower for kw in ["cost", "price", "charge", "₹", "fee"]):
            return "pricing"
        if any(kw in text_lower for kw in ["room", "suite", "bed", "guest", "accommodat"]):
            return "rooms"
        return "general"

    @staticmethod
    def _get_tokens(text: str) -> Set[str]:
        """Extracts normalized alphanumeric lowercase tokens from text."""
        words = text.lower().replace("₹", "").replace("-", " ").split()
        return {w.strip(".,;:?!()\"'") for w in words if len(w) > 2}

    def _is_redundant(self, new_text: str, processed_chunks: List[Dict[str, Any]]) -> bool:
        """
        Calculates token-based Jaccard similarity to determine if a record is redundant.
        
        Args:
            new_text: New fact text under check.
            processed_chunks: List of already constructed chunk dictionaries.
            
        Returns:
            bool: True if Jaccard similarity exceeds threshold.
        """
        new_tokens = self._get_tokens(new_text)
        if not new_tokens:
            return False

        for chunk in processed_chunks:
            # We compare with the original raw text to test raw semantic duplication
            existing_tokens = self._get_tokens(chunk.get("raw_text", ""))
            if not existing_tokens:
                continue

            intersection = new_tokens.intersection(existing_tokens)
            union = new_tokens.union(existing_tokens)
            similarity = len(intersection) / len(union)

            if similarity > self.deduplication_threshold:
                logger.debug(f"Redundancy filtered: Similarity {similarity:.2f} > {self.deduplication_threshold}")
                return True

        return False

    def chunk_dataset(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Ingests the parsed JSON dictionary and converts array fields into contextually self-contained chunks.
        
        Args:
            data: Verified raw JSON database directory.
            
        Returns:
            List[Dict]: Structured chunk records list.
        """
        hotel_name = data.get("hotel_name", "StayChat Grand Hotel")
        
        # Priority mapping: Ingest core facts first so duplicates in general arrays (faq) are skipped
        target_categories = [
            "rooms", "amenities", "restaurants", "policies",
            "transportation", "payments", "services", "general_information", "faq"
        ]
        
        chunks: List[Dict[str, Any]] = []
        skipped_count = 0

        # Ingest top-level metadata values as generic factual chunks
        location = data.get("location", "")
        if location:
            loc_record = f"The hotel address is located at: {location}"
            loc_content = f"[Hotel: {hotel_name}] [Category: general_information] [Subsection: general] {loc_record}"
            chunks.append({
                "chunk_id": hashlib.sha256(loc_content.encode("utf-8")).hexdigest(),
                "category": "general_information",
                "subsection": "general",
                "content": loc_content,
                "raw_text": loc_record,
                "hotel_name": hotel_name,
                "content_length": len(loc_record)
            })

        for category in target_categories:
            records = data.get(category, [])
            logger.info(f"Chunking category '{category}' ({len(records)} entries)...")

            for record in records:
                # 1. Enforce Token Deduplication only on 'faq' category to avoid dropping distinct core facts
                if category == "faq" and self._is_redundant(record, chunks):
                    skipped_count += 1
                    continue

                # 2. Determine subsection category
                subsection = self._determine_subsection(record)

                # 3. Contextual Enrichment: prepends subject & metadata to make the text self-contained
                contextual_content = f"[Hotel: {hotel_name}] [Category: {category}] [Subsection: {subsection}] {record}"

                # 4. Generate deterministic chunk ID hash
                chunk_id = hashlib.sha256(contextual_content.encode("utf-8")).hexdigest()

                # 5. Build rigid chunk payload
                chunk_payload = {
                    "chunk_id": chunk_id,
                    "category": category,
                    "subsection": subsection,
                    "content": contextual_content,
                    # Retained internally for auditing / deduplication reference
                    "raw_text": record,
                    "hotel_name": hotel_name,
                    "content_length": len(record)
                }

                chunks.append(chunk_payload)

        logger.info(
            f"Chunking completed. Compiled {len(chunks)} unique semantic facts. "
            f"Filtered out {skipped_count} redundant duplicates."
        )
        return chunks
