"""
StayChat Hotel Assistant - Ingestion System Configuration
Defines environment variables, model configurations, filesystem paths, and index settings.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Base Directory Paths
ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
FAISS_DIR = ROOT_DIR / "faiss_index"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
FAISS_DIR.mkdir(parents=True, exist_ok=True)

# Load environment settings from .env file (checks workspace root first, then local ai/ dir)
workspace_env = ROOT_DIR.parent / ".env"
local_env = ROOT_DIR / ".env"
if workspace_env.exists():
    load_dotenv(dotenv_path=workspace_env)
else:
    load_dotenv(dotenv_path=local_env)


class Config:
    """Strongly-typed central configuration store for the ingestion system."""

    def __init__(self) -> None:
        # Authentication & API Keys
        self.api_key: str = self._load_required_env("GEMINI_API_KEY")
        self.app_env: str = os.getenv("APP_ENV", "development")

        # Filesystem Path Declarations
        self.kb_path: Path = DATA_DIR / "hotel_kb.json"
        self.index_path: Path = FAISS_DIR / "hotel.index"
        self.metadata_path: Path = FAISS_DIR / "metadata.json"

        # Model Declarations
        self.embedding_model: str = "models/embedding-001"
        self.embedding_dimension: int = 768  # embedding-001 default dimensions
        self.batch_size: int = 16
        
        # FAISS Index Configuration
        # Supported: "flat_l2" | "hnsw"
        self.index_type: str = os.getenv("FAISS_INDEX_TYPE", "flat_l2")
        self.hnsw_m: int = 16  # HNSW graph connection degree parameter

    @staticmethod
    def _load_required_env(key: str) -> str:
        """Loads a mandatory environment variable, providing a clean runtime error if absent."""
        value = os.getenv(key)
        if not value:
            # Check if running in a mock context or test phase
            if "pytest" in sys.modules:
                return "mock_key"
            raise EnvironmentError(
                f"Missing critical API Key: The environment variable '{key}' is required "
                "to proceed. Please create a '.env' file in the root workspace and define it."
            )
        return value


# Global Configuration Instance
config = Config()
