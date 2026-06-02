"""
StayChat Hotel Assistant - Pluggable Session Store
Defines a unified Base interface and implements interchangeable File and Redis session stores.
Toggled via the 'SESSION_STORE' environment variable ('file' | 'redis').
"""

import os
import json
import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("StayChatSessionManager")


class BaseSessionManager(ABC):
    """
    Abstract Base Class defining the rigid interface for session stores.
    Adheres to the Dependency Inversion Principle (SOLID).
    """

    @abstractmethod
    def create_session(self, session_id: str) -> Dict[str, Any]:
        """Instantiates a new session profile."""
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Retrieves an active session profile, raising KeyError on expiration/absence."""
        pass

    @abstractmethod
    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """Persists the session profile details."""
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """Removes a session completely from storage."""
        pass

    @abstractmethod
    def prune_expired_sessions(self) -> int:
        """Sweeps and purges expired sessions from persistence."""
        pass


class FileSessionManager(BaseSessionManager):
    """
    File-based Session Manager Adapter.
    Zero-config local JSON file persistence.
    """

    def __init__(self, session_dir: Path, timeout_seconds: int = 1800) -> None:
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = timeout_seconds

    def _get_session_path(self, session_id: str) -> Path:
        sanitized_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
        return self.session_dir / f"sess_{sanitized_id}.json"

    def create_session(self, session_id: str) -> Dict[str, Any]:
        now = time.time()
        session_data = {
            "session_id": session_id,
            "created_at": now,
            "last_activity": now,
            "messages": []
        }
        self.save_session(session_id, session_data)
        return session_data

    def get_session(self, session_id: str) -> Dict[str, Any]:
        session_path = self._get_session_path(session_id)
        if not session_path.exists():
            raise KeyError(f"Session '{session_id}' does not exist.")

        try:
            with open(session_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)
        except json.JSONDecodeError:
            self.delete_session(session_id)
            raise KeyError(f"Session '{session_id}' was corrupted and has been deleted.")

        now = time.time()
        elapsed = now - session_data.get("last_activity", 0)

        if elapsed > self.timeout_seconds:
            self.delete_session(session_id)
            raise KeyError(f"Session '{session_id}' has expired due to inactivity.")

        session_data["last_activity"] = now
        self.save_session(session_id, session_data)
        return session_data

    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        session_path = self._get_session_path(session_id)
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

    def delete_session(self, session_id: str) -> None:
        session_path = self._get_session_path(session_id)
        if session_path.exists():
            session_path.unlink()

    def prune_expired_sessions(self) -> int:
        now = time.time()
        deleted_count = 0
        for file_path in self.session_dir.glob("sess_*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                elapsed = now - session_data.get("last_activity", 0)
                if elapsed > self.timeout_seconds:
                    file_path.unlink()
                    deleted_count += 1
            except Exception:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception:
                    pass
        return deleted_count


class RedisSessionManager(BaseSessionManager):
    """
    Redis-based Session Manager Adapter.
    Centralized in-memory cache supporting automatic TTL eviction.
    """

    def __init__(self, host: str, port: int, db: int, timeout_seconds: int = 1800) -> None:
        try:
            import redis
        except ImportError as e:
            logger.critical("Dependency missing: 'redis' package is required for RedisSessionManager. Run 'pip install redis'.")
            raise ImportError("Missing required library: 'redis'. Please run 'pip install redis' to connect to Redis.") from e
            
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.timeout_seconds = timeout_seconds
        
        # Test connection instantly
        self.client.ping()
        logger.info(f"Connected successfully to Redis at {host}:{port} (DB {db}).")

    def _get_key(self, session_id: str) -> str:
        return f"staychat:session:{session_id}"

    def create_session(self, session_id: str) -> Dict[str, Any]:
        now = time.time()
        session_data = {
            "session_id": session_id,
            "created_at": now,
            "last_activity": now,
            "messages": []
        }
        self.save_session(session_id, session_data)
        return session_data

    def get_session(self, session_id: str) -> Dict[str, Any]:
        key = self._get_key(session_id)
        raw_data = self.client.get(key)
        
        if not raw_data:
            raise KeyError(f"Session '{session_id}' does not exist or has expired in Redis.")
            
        session_data = json.loads(raw_data)
        session_data["last_activity"] = time.time()
        self.save_session(session_id, session_data)
        return session_data

    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        key = self._get_key(session_id)
        # Store serialized JSON and set Redis TTL expiration automatically!
        self.client.setex(
            name=key,
            time=self.timeout_seconds,
            value=json.dumps(session_data, ensure_ascii=False)
        )

    def delete_session(self, session_id: str) -> None:
        key = self._get_key(session_id)
        self.client.delete(key)

    def prune_expired_sessions(self) -> int:
        # Redis handles key eviction automatically via TTL, no manual prune sweep needed!
        logger.info("Redis Session Store: Skipping manual prune. Key eviction is managed natively by Redis TTL.")
        return 0


class SessionManager(BaseSessionManager):
    """
    Unified Session Manager Router Factory.
    Routes all operations to either the FileSessionManager or RedisSessionManager based on .env configuration.
    Maintains complete API compatibility with the rest of the application.
    """

    def __init__(self, session_dir: Optional[Path] = None, timeout_seconds: int = 1800) -> None:
        self.timeout_seconds = timeout_seconds
        
        # Load store type from environment variable ('file' or 'redis')
        self.store_type = os.getenv("SESSION_STORE", "file").strip().lower()
        
        if self.store_type == "redis":
            logger.info("Initializing active REDIS Session Store adapter...")
            host = os.getenv("REDIS_HOST", "localhost").strip()
            port = int(os.getenv("REDIS_PORT", "6379").strip())
            db = int(os.getenv("REDIS_DB", "0").strip())
            
            try:
                self.adapter: BaseSessionManager = RedisSessionManager(
                    host=host,
                    port=port,
                    db=db,
                    timeout_seconds=timeout_seconds
                )
            except Exception as e:
                logger.error(
                    f"Redis Connection Failed: {e}. "
                    "Falling back to FileSessionManager for safety and zero-downtime execution!"
                )
                self.store_type = "file"
                self.adapter = self._init_file_adapter(session_dir)
        else:
            self.adapter = self._init_file_adapter(session_dir)

    def _init_file_adapter(self, session_dir: Optional[Path]) -> FileSessionManager:
        logger.info("Initializing active FILE Session Store adapter...")
        if session_dir is None:
            session_dir = Path(__file__).resolve().parent.parent.parent / "data" / "sessions"
        return FileSessionManager(session_dir=session_dir, timeout_seconds=self.timeout_seconds)

    # Base delegation methods routing calls dynamically to the active adapter
    def create_session(self, session_id: str) -> Dict[str, Any]:
        return self.adapter.create_session(session_id)

    def get_session(self, session_id: str) -> Dict[str, Any]:
        return self.adapter.get_session(session_id)

    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        self.adapter.save_session(session_id, session_data)

    def delete_session(self, session_id: str) -> None:
        self.adapter.delete_session(session_id)

    def prune_expired_sessions(self) -> int:
        return self.adapter.prune_expired_sessions()

    # Shared helper method to add message turns (compatible with existing code)
    def add_message_to_session(
        self,
        session_id: str,
        role: str,
        content: str,
        intent: str = "unknown",
        language: str = "english"
    ) -> Dict[str, Any]:
        try:
            session = self.get_session(session_id)
        except KeyError:
            session = self.create_session(session_id)

        now = time.time()
        message_node = {
            "role": role,
            "content": content,
            "timestamp": now,
            "intent": intent,
            "language": language
        }
        
        session["messages"].append(message_node)
        session["last_activity"] = now
        
        self.save_session(session_id, session)
        logger.debug(f"Added message turn to store ({self.store_type}): role='{role}' in session='{session_id}'")
        return session
