"""
StayChat Hotel Assistant - Ingestion System Validator
Validates raw knowledge base structure, field consistency, data types, and values.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("StayChatValidator")


class DataValidationError(Exception):
    """Custom exception raised when data integrity or schema validations fail."""
    pass


class KnowledgeBaseValidator:
    """
    Knowledge Base Schema & Semantic Validator.
    Ensures that raw knowledge base source JSON conforms strictly to ingestion standards.
    """

    REQUIRED_SCALAR_FIELDS = {
        "hotel_name": str,
        "location": str,
        "star_rating": int,
        "contact_phone": str,
        "contact_email": str
    }

    REQUIRED_ARRAY_FIELDS = [
        "general_information", "rooms", "amenities", "restaurants",
        "policies", "transportation", "payments", "services", "faq"
    ]

    @classmethod
    def validate_file(cls, file_path: Path) -> Dict[str, Any]:
        """
        Loads raw JSON file, performs integrity validations, and returns verified payload.
        
        Args:
            file_path: Absolute filesystem path to raw JSON file.
            
        Returns:
            Dict: Verified knowledge base dictionary.
            
        Raises:
            DataValidationError: If structural or value validation boundaries are breached.
        """
        logger.info(f"Initiating schema validation on knowledge source: {file_path.name}")
        
        if not file_path.exists():
            raise DataValidationError(f"Critical Ingestion Error: Knowledge base file not found at path: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise DataValidationError(f"Critical Ingestion Error: File at {file_path} is malformed JSON. Detail: {e}")

        if not isinstance(data, dict):
            raise DataValidationError("Critical Ingestion Error: JSON root must be a structured key-value object (dict).")

        cls._validate_scalar_attributes(data)
        cls._validate_array_attributes(data)
        cls._validate_record_values(data)
        
        logger.info("Knowledge source validated successfully. 0 errors detected.")
        return data

    @classmethod
    def _validate_scalar_attributes(cls, data: Dict[str, Any]) -> None:
        """Validates existence and correct type boundaries for primary scalar metadata."""
        for field, expected_type in cls.REQUIRED_SCALAR_FIELDS.items():
            if field not in data:
                raise DataValidationError(f"Schema Violation: Missing required scalar field '{field}' in JSON database.")
            
            value = data[field]
            if not isinstance(value, expected_type):
                raise DataValidationError(
                    f"Type Violation: Required field '{field}' must be of type {expected_type.__name__}. "
                    f"Found type {type(value).__name__} instead."
                )
            
            # Star Rating boundary assertion
            if field == "star_rating" and not (1 <= value <= 5):
                raise DataValidationError(f"Constraint Violation: 'star_rating' must be between 1 and 5. Found: {value}")

    @classmethod
    def _validate_array_attributes(cls, data: Dict[str, Any]) -> None:
        """Validates presence and correct array structures for primary categories."""
        for category in cls.REQUIRED_ARRAY_FIELDS:
            if category not in data:
                raise DataValidationError(f"Schema Violation: Missing required category array '{category}' in JSON database.")
            
            value = data[category]
            if not isinstance(value, list):
                raise DataValidationError(
                    f"Type Violation: Category '{category}' must be a list of text strings. "
                    f"Found type {type(value).__name__} instead."
                )

    @classmethod
    def _validate_record_values(cls, data: Dict[str, Any]) -> None:
        """Asserts that all categories and text records do not contain nulls or whitespace empty lines."""
        for category in cls.REQUIRED_ARRAY_FIELDS:
            records: List[Any] = data[category]
            
            if not records:
                logger.warning(f"Metadata Warning: Category array '{category}' is empty. Proceeding.")
                continue

            for idx, record in enumerate(records):
                if not isinstance(record, str):
                    raise DataValidationError(
                        f"Type Violation: Category '{category}' at index {idx} contains non-string element "
                        f"of type {type(record).__name__}: '{record}'."
                    )
                
                # Check for empty / whitespace only strings
                if not record.strip():
                    raise DataValidationError(
                        f"Value Violation: Category '{category}' contains empty or whitespace-only record "
                        f"at index {idx}."
                    )
