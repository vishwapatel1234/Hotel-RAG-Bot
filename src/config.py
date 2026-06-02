"""
StayChat Grand Hotel Assistant - Configuration Manager
Provides a strongly-typed wrapper around environment variables and system settings.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Base Directory Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT_DIR / "Dataset" / "hotel_data.json"
INDEX_DIR = ROOT_DIR / "data" / "faiss_index"
INDEX_PATH = INDEX_DIR / "index.faiss"
METADATA_PATH = INDEX_DIR / "index_metadata.pkl"

# Load environment variables
load_dotenv(dotenv_path=ROOT_DIR / ".env")


@dataclass(frozen=True)
class ModelSettings:
    """Hyperparameters and configuration settings for Gemini models."""
    generation_model: str = "gemini-1.5-flash"
    embedding_model: str = "text-embedding-004"
    default_temperature: float = 0.2
    guardrail_temperature: float = 0.0
    max_output_tokens: int = 512


@dataclass(frozen=True)
class RAGSettings:
    """Settings controlling chunking, retrieval limits, and confidence bounds."""
    similarity_threshold: float = float(os.getenv("FAISS_SIMILARITY_THRESHOLD", "0.65"))
    top_k: int = int(os.getenv("TOP_K_RESULTS", "4"))
    max_history_turns: int = int(os.getenv("MAX_HISTORY_TURNS", "6"))


class Config:
    """Central configuration class loading values safely with strict boundaries."""

    def __init__(self):
        self.api_key: str = self._load_required_env("GEMINI_API_KEY")
        self.env: str = os.getenv("APP_ENV", "development")
        self.models: ModelSettings = ModelSettings()
        self.rag: RAGSettings = RAGSettings()
        self.DATASET_PATH = DATASET_PATH
        self.INDEX_PATH = INDEX_PATH
        self.METADATA_PATH = METADATA_PATH
        
        # Ensure data storage directories exist
        INDEX_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _load_required_env(key: str) -> str:
        """Loads a mandatory environment variable or raises a descriptive error."""
        value = os.getenv(key)
        if not value:
            raise EnvironmentError(
                f"Missing critical configuration: '{key}' must be defined in your .env file. "
                "Please duplicate .env.example to .env and populate the required keys."
            )
        return value


# Global configuration instance
config = Config()
