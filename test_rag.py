import sys
from pathlib import Path
import logging
logging.basicConfig(level=logging.DEBUG)

ai_dir = Path("ai").resolve()
sys.path.append(str(ai_dir))

from services.embedding_service import EmbeddingService
from services.retrieval_service import RetrievalService
from config import config

print("Loading services...")
embedder = EmbeddingService(api_key=config.api_key, model_name=config.embedding_model)
retriever = RetrievalService(embedding_service=embedder)

print("Running retrieve for: What are the prices for the Standard and Deluxe rooms?")
res = retriever.retrieve("What are the prices for the Standard and Deluxe rooms?")
print("Result:", res)

print("\nRunning retrieve for: Location of the Hotel?")
res2 = retriever.retrieve("Location of the Hotel?")
print("Result2:", res2)
