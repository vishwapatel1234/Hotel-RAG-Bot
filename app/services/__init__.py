"""
StayChat Hotel Assistant - Services Package Initializer
Implements dynamic namespace merging of /ai/services/ into the /app/services/ package namespace.
"""

from pathlib import Path

# Identify the core AI services directory path
AI_SERVICES_DIR = Path(__file__).resolve().parent.parent.parent / "ai" / "services"

# Append it to the package search paths to merge both physical directories
if str(AI_SERVICES_DIR) not in __path__:
    __path__.append(str(AI_SERVICES_DIR))
