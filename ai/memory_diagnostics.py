"""
StayChat Hotel Assistant - Memory Diagnostics Telemetry Tool
Allows inspection and auditing of active conversation memory limits.
"""

import sys
from pathlib import Path
from typing import Dict, Any

# Adjust path to configure absolute imports
sys.path.append(str(Path(__file__).resolve().parent))

from services.session_manager import SessionManager
from services.memory_service import MemoryService


class MemoryDiagnostics:
    """
    Memory Diagnostics Engine.
    Compiles operational telemetry for session counts, turn limits, and language contexts.
    """

    @staticmethod
    def get_diagnostics(session_id: str, memory_service: MemoryService) -> Dict[str, Any]:
        """
        Compiles structural diagnostics metrics on memory load state.
        
        Returns:
            Dict: Contains session_id, messages_in_memory, language, and memory_used.
        """
        report = memory_service.get_memory_diagnostics(session_id)
        
        # Conforming exactly to the STEP 10 spec:
        return {
            "session_id": report["session_id"],
            "messages_in_memory": report["messages_in_memory"],
            "language": report["language"],
            "memory_used": report["memory_used"]
        }


def run_diagnostics_demo() -> None:
    """Executes a diagnostic verification sweep over a mock session."""
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=========================================================")
    print("      StayChat Conversation Memory Diagnostics")
    print("=========================================================")

    session_manager = SessionManager(timeout_seconds=1800)
    memory_service = MemoryService(session_manager=session_manager, max_exchanges=10)

    session_id = "diagnostics-test-session"
    
    # Reset existing
    session_manager.delete_session(session_id)
    
    # 1. Inspect empty session state
    print("\n1. Inspecting empty session:")
    diagnostics = MemoryDiagnostics.get_diagnostics(session_id, memory_service)
    print(f"Diagnostics: {diagnostics}")

    # 2. Add some exchanges (English and Hinglish mix)
    print("\n2. Adding messages to session...")
    memory_service.add_message(session_id, "user", "Do you have suites?", intent="booking_inquiry", language="english")
    memory_service.add_message(session_id, "assistant", "Yes, we offer Executive Suites for ₹12000.", intent="booking_inquiry", language="english")
    memory_service.add_message(session_id, "user", "Pool hai?", intent="amenity_question", language="hinglish")
    memory_service.add_message(session_id, "assistant", "Haan, rooftop infinity pool subah 7 se raat 10 baje tak chalta hai.", intent="amenity_question", language="hinglish")

    # 3. Inspect active session state
    print("\n3. Inspecting active session state:")
    diagnostics = MemoryDiagnostics.get_diagnostics(session_id, memory_service)
    print(f"Diagnostics: {diagnostics}")
    
    # Get extended details for developer validation
    extended = memory_service.get_memory_diagnostics(session_id)
    print(f"Extended Metrics: {extended}")
    
    print("\nFormatted prompt context payload:")
    print("-" * 45)
    print(memory_service.format_history_for_context(session_id))
    print("-" * 45)

    # Clean up
    session_manager.delete_session(session_id)
    print("\nDiagnostics sweep completed successfully.")


if __name__ == "__main__":
    run_diagnostics_demo()
