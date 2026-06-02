"""
StayChat Hotel Assistant - Retrieval Confidence Auditor
Evaluates hybrid confidence metrics based on Vector Similarity (70%) and Category Relevance (30%).
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("StayChatConfidence")


class ConfidenceEngine:
    """
    Hybrid Confidence Engine.
    Combines lexical/semantic intent relevance with vector distances to validate RAG retrieval safety.
    """

    def __init__(self, confidence_threshold: float = 0.70) -> None:
        """
        Initializes the Confidence Engine.
        
        Args:
            confidence_threshold: Combined minimum score required to approve context as safe.
        """
        self.confidence_threshold = confidence_threshold

    @staticmethod
    def predict_expected_category(query: str) -> Optional[str]:
        """
        Heuristically maps query tokens to expected category arrays to audit relevance.
        
        Args:
            query: User's search query.
            
        Returns:
            Optional[str]: Predicted category name or None if generic.
        """
        query_lower = query.lower()
        
        # 1. Cancellation and critical rules -> policies
        if any(kw in query_lower for kw in ["cancell", "refund", "no-show", "pet", "smoke", "identification", "deposit"]):
            return "policies"
        
        # 2. Pricing and accommodations -> rooms
        if any(kw in query_lower for kw in ["room", "suite", "bed", "cost", "price", "₹", "standard", "deluxe", "executive", "family"]):
            return "rooms"
            
        # 3. Swimming, gym, or operational hours -> amenities
        if any(kw in query_lower for kw in ["pool", "swimming", "gym", "fitness", "spa", "sauna", "steam", "valet", "housekeeping"]):
            return "amenities"
            
        # 4. Dining operations -> restaurants
        if any(kw in query_lower for kw in ["breakfast", "dinner", "lunch", "harbor", "dining", "kitchen", "lounge", "buffet"]):
            return "restaurants"
            
        # 5. airport or metro transfers -> transportation
        if any(kw in query_lower for kw in ["airport", "transfer", "taxi", "metro", "chauffeur", "car"]):
            return "transportation"
            
        # 6. Payment cards or cash -> payments
        if any(kw in query_lower for kw in ["card", "visa", "mastercard", "amex", "rupay", "upi", "cash", "payment"]):
            return "payments"
            
        # 7. Concierge and hosting services -> services
        if any(kw in query_lower for kw in ["wedding", "corporate", "event", "printing", "photocopy", "lost", "desk", "tour"]):
            return "services"

        return None

    def evaluate(self, query: str, top_match: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates the two-factor hybrid confidence score for a retrieved chunk.
        
        Formula:
            Final Score = (0.70 * Vector Similarity) + (0.30 * Category Relevance)
            
        Args:
            query: Standalone search query.
            top_match: The highest-scoring chunk returned by the index retriever.
            
        Returns:
            Dict: Confidence report containing 'status', 'final_score', and metadata.
        """
        vector_similarity = top_match.get("score", 0.0)
        chunk_category = top_match.get("category", "")
        
        # 1. Predict Target Category
        expected_category = self.predict_expected_category(query)
        
        # 2. Calculate Category Relevance (30% weight)
        # Category aliases representing semantically overlapping categories to prevent false refusals
        aliases = {
            "policies": ["policies", "general_information", "faq", "rooms", "payments"],
            "rooms": ["rooms", "general_information", "faq", "amenities", "policies", "restaurants"],
            "amenities": ["amenities", "general_information", "faq", "services", "transportation", "rooms"],
            "restaurants": ["restaurants", "general_information", "faq", "dining", "rooms"],
            "transportation": ["transportation", "general_information", "faq", "amenities"],
            "services": ["services", "general_information", "faq", "amenities", "policies"],
            "payments": ["payments", "general_information", "faq", "pricing", "policies"]
        }

        # If expected category is None (neutral generic), or if chunk is a general FAQ, or matches expected alias
        if expected_category is None:
            category_relevance = 1.0
            logger.debug("Query mapped to generic category. Neutral Category Relevance applied.")
        elif chunk_category in ("faq", "general_information"):
            category_relevance = 1.0
            logger.debug(f"Retrieved general-topic chunk category '{chunk_category}' approved as relevant.")
        elif expected_category in aliases and chunk_category in aliases[expected_category]:
            category_relevance = 1.0
            logger.debug(f"Category Relevance MATCH (via Alias): Expected '{expected_category}' -> Chunk '{chunk_category}'")
        elif chunk_category == expected_category:
            category_relevance = 1.0
            logger.debug(f"Category Relevance MATCH: Query expected '{expected_category}' -> Chunk category '{chunk_category}'")
        else:
            category_relevance = 0.0
            logger.warning(f"Category Relevance MISMATCH: Query expected '{expected_category}' -> Chunk category '{chunk_category}'")

        # 3. Compute hybrid score
        final_score = (0.70 * vector_similarity) + (0.30 * category_relevance)
        logger.info(f"Hybrid Score calculated: {final_score:.3f} (Vector Similarity: {vector_similarity:.2f}, Cat Relevance: {category_relevance:.1f})")

        # 4. Enforce Confidence Threshold Check
        if final_score >= self.confidence_threshold:
            return {
                "status": "high_confidence",
                "final_score": final_score,
                "vector_similarity": vector_similarity,
                "category_relevance": category_relevance,
                "expected_category": expected_category,
                "retrieved_category": chunk_category
            }
        else:
            reason = (
                f"Insufficient evidence found. Hybrid confidence score ({final_score:.2f}) "
                f"is below system threshold ({self.confidence_threshold:.2f})."
            )
            logger.warning(f"Confidence check failed: {reason}")
            return {
                "status": "low_confidence",
                "reason": reason,
                "final_score": final_score,
                "vector_similarity": vector_similarity,
                "category_relevance": category_relevance,
                "expected_category": expected_category,
                "retrieved_category": chunk_category
            }
