"""
StayChat Hotel Assistant - Ingestion System Embedding Service
Interfaces with the Gemini API to request high-performance float vector embeddings.
"""

import time
import random
import logging
from typing import List
import google.generativeai as genai
from google.api_core import exceptions

logger = logging.getLogger("StayChatEmbeddings")


class EmbeddingService:
    """
    Embedding Generation Engine.
    Exposes high-speed vectorized conversions using Gemini text-embedding-004.
    Implements robust error handling and exponential backoff retry parameters.
    """

    def __init__(self, api_key: str, model_name: str = "models/text-embedding-004") -> None:
        """
        Initializes the Embedding Service.
        
        Args:
            api_key: Gemini API credential string.
            model_name: Active text embedding model string.
        """
        self.model_name = model_name
        
        # Configure Gemini API credentials
        if api_key != "mock_key":
            genai.configure(api_key=api_key)
            logger.info("Successfully configured Gemini API credentials.")
        else:
            logger.warning("Initializing with mock credentials. API calls will be simulated.")

    def _get_embedding_with_retry(self, text: str, max_retries: int = 5) -> List[float]:
        """
        Requests embedding vector for a single text, applying exponential backoff retry on failure.
        
        Args:
            text: Query string.
            max_retries: Limit on retry attempts before raising fatal error.
            
        Returns:
            List[float]: Vector array of floats.
        """
        attempt = 0
        while attempt < max_retries:
            try:
                response = genai.embed_content(
                    model=self.model_name,
                    content=text,
                    task_type="retrieval_document"  # Essential for documents being indexed
                )
                return response["embedding"]
            except (exceptions.GoogleAPICallError, exceptions.RetryError) as e:
                attempt += 1
                if attempt >= max_retries:
                    logger.error(f"Fatal Gemini API Error: Max retries ({max_retries}) reached. Detail: {e}")
                    raise e
                
                # Exponential backoff with jitter formula
                backoff_time = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Gemini API rate boundary or transient error encountered: {e}. "
                    f"Retrying in {backoff_time:.2f} seconds (Attempt {attempt}/{max_retries})..."
                )
                time.sleep(backoff_time)
            except Exception as e:
                logger.error(f"Unexpected error during embedding call: {e}")
                raise e
        
        raise RuntimeError("Embedding call failed to execute.")

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 16
    ) -> List[List[float]]:
        """
        Generates embeddings for a list of texts in batches to maximize API throughput.
        
        Args:
            texts: List of text strings to embed.
            batch_size: Size of batches to group.
            
        Returns:
            List[List[float]]: List of float vector arrays.
        """
        logger.info(f"Generating embeddings for {len(texts)} chunks in batches of {batch_size}...")
        embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.debug(f"Processing embedding batch {i // batch_size + 1} ({len(batch)} items)...")
            
            try:
                # Call batch embedding API
                response = genai.embed_content(
                    model=self.model_name,
                    content=batch,
                    task_type="retrieval_document"
                )
                # Parse batch embeddings list
                batch_embeddings = response["embedding"]
                embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.warning(f"Batch embedding failed: {e}. Falling back to sequential retry pipeline...")
                # Sequential fallback retry in case batch contains too large characters or rate-limits
                for text in batch:
                    vector = self._get_embedding_with_retry(text)
                    embeddings.append(vector)

        logger.info(f"Batch embedding generation complete. Vector list count: {len(embeddings)}.")
        return embeddings
