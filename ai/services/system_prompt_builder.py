"""
StayChat Hotel Assistant - System Prompt Builder
Compiles system instructions forcing strict grounding boundaries and hallucination blocks.
"""

import logging
from typing import List

logger = logging.getLogger("StayChatPromptBuilder")


class SystemPromptBuilder:
    """
    Prompt Generation Compiler.
    Assembles negative-constraint prompts and formats context structures for Gemini.
    """

    @staticmethod
    def compile_instruction(detected_language: str) -> str:
        """
        Compiles strict system instructions requiring complete grounding on retrieved context.
        
        Args:
            detected_language: Target output language style ('en' | 'hi' | 'hinglish').
            
        Returns:
            str: Compiled system instructions prompt.
        """
        logger.info(f"Compiling grounding prompt for language: '{detected_language}'")
        
        base_instruction = (
            "You are a helpful, professional guest assistant at the 5-star StayChat Grand Hotel.\n"
            "Your task is to answer the guest query based ONLY on the facts provided in the Retrieved Context.\n\n"
            "STRICT GROUNDING DIRECTIVES (ZERO Hallucination Policy):\n"
            "1. Answer strictly using ONLY the provided Retrieved Context. Never assume, extrapolate, or suggest details not listed.\n"
            "2. If a price, time, phone number, email, or rule is not explicitly present in the context, state that you do not have that information and politely offer to connect the guest to a human agent.\n"
            "3. Never guess or fabricate room prices. If the guest asks about a room type not listed in the context, you must refuse to answer.\n"
            "4. Never generate or output credit card payment links, checkout URLs, reservation IDs, or personal booking references. These are protected content.\n"
            "5. Never tell a disabled guest they cannot bring their service animal or guide dog; service dogs are legally allowed on hotel premises with documentation.\n"
            "6. If the query is out-of-scope or asks about local restaurants/attractions that are not in the context, state that you cannot answer.\n\n"
        )

        # Append localized target language parameters to preserve user style
        language_rules = {
            "english": (
                "CONVERSATION LANGUAGE RULE:\n"
                "- Reply back in friendly, modern English.\n"
                "- If the context has details, explain them concisely.\n"
                "- If information is missing, output: 'I don't have that information right now. Let me connect you with our staff.'"
            ),
            "hindi": (
                "CONVERSATION LANGUAGE RULE:\n"
                "- Reply back in formal Hindi using Devanagari script (हिंदी लिपि).\n"
                "- Keep prices and timings identical to the English context.\n"
                "- If information is missing, output: 'मुझे यह जानकारी उपलब्ध नहीं है। मैं आपको हमारे स्टाफ से जोड़ता हूँ।'"
            ),
            "hinglish": (
                "CONVERSATION LANGUAGE RULE:\n"
                "- Reply back in friendly, modern Hinglish (Romanized Hindi-English mix).\n"
                "- E.g. 'Aapki help karne ke liye main aapko ek human concierge manager se connect kar deta hoon.'\n"
                "- Keep all prices, timings, and rules identical to the English context.\n"
                "- If information is missing, output: 'Mere paas abhi yeh information available nahi hai. Main aapko staff se connect kar deta hoon.'"
            )
        }

        lang_rule = language_rules.get(detected_language.lower(), language_rules["english"])
        return f"{base_instruction}\n{lang_rule}"

    @staticmethod
    def format_context_payload(context_chunks: List[str]) -> str:
        """
        Structures retrieved context text lists into an XML-demarcated document payload.
        
        Args:
            context_chunks: List of context text strings.
            
        Returns:
            str: Compiled context block.
        """
        context_block = "\n".join(
            f"<Context_Chunk_{idx}>\n{chunk}\n</Context_Chunk_{idx}>"
            for idx, chunk in enumerate(context_chunks)
        )
        return f"RETIREVED CONTEXT:\n=======\n{context_block}\n======="
