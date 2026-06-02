"""
StayChat Hotel Assistant - Pre-Retrieval Protected Content Guardrail
Filters out user requests targeting restricted, sensitive, or personal categories.
"""

import re
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("StayChatProtectedContent")


class ProtectedContentEngine:
    """
    Protected Content Guardrail.
    Scans query strings for patterns requesting PII, checkout URLs, or financial registries.
    """

    def __init__(self) -> None:
        # Regex mappings for highly sensitive entities
        self.rules = {
            # Matches typical card payment, checkout, or transfer link phrases
            "payment_link": [
                r"\b(pay|payment|checkout|transaction)\s+(link|url|page|gateway|site)\b",
                r"\blink\s+to\s+pay\b",
                r"\bpay\s+online\b",
                r"\bupi\s+(id|link|code)\b"
            ],
            # Matches typical reservation numbers or booking references
            "booking_reference": [
                r"\b(booking|reservation|ref|reference|booking_id|bookingid)\s+(number|id|code|details|profile|confirm)\b",
                r"\breservation\s+no\b",
                r"\bconfirm\s+code\b"
            ],
            # Matches guest personal profiles / PII requests
            "guest_information": [
                r"\b(my|guest|customer|user)\s+(record|profile|data|invoice|bill|history|stay)\b",
                r"\bwhat\s+is\s+my\s+(room|email|phone|name)\b",
                r"\bdetails\s+of\s+my\s+stay\b"
            ],
            # Matches internal staff registries or operational shifts
            "internal_staff_info": [
                r"\b(staff|employee|manager|cleaner|chef|concierge)\s+(schedule|shift|phone|email|salary|roster|roster_id)\b",
                r"\bwho\s+is\s+on\s+duty\b",
                r"\bstaff\s+personal\s+number\b"
            ],
            # Matches live inventory requests
            "live_room_availability": [
                r"\b(is|are)\b.*\b(available|vacant|free)\b.*\b(tonight|today|tomorrow|now|currently|live)\b",
                r"\broom\s+availability\b",
                r"\bavailability\s+of\s+rooms\b",
                r"\bany\s+rooms\s+free\b"
            ],
            # Matches discount codes / promo codes / coupons
            "discount_codes": [
                r"\b(discount|promo|coupon|voucher|offer)\s+(code|coupon|id|number)\b",
                r"\bget\s+a\s+discount\b",
                r"\bany\s+promotions\b"
            ],
            # Matches financial records / billing registries
            "financial_records": [
                r"\b(financial|billing|invoice|transaction|ledger|payment)\s+(record|statement|history|report|file|log)\b",
                r"\bhotel\s+revenue\b",
                r"\bfinancial\s+status\b"
            ]
        }

    def inspect_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Scans the query for references to protected entities.
        
        Args:
            query: Raw user message.
            
        Returns:
            Tuple[bool, Optional[str]]: (is_blocked, matched_rule_name)
        """
        query_cleaned = query.lower().strip()
        
        for rule_name, patterns in self.rules.items():
            for pattern in patterns:
                if re.search(pattern, query_cleaned):
                    logger.warning(
                        f"Protected Content Blocked: Query matched rule '{rule_name}' "
                        f"via pattern '{pattern}'."
                    )
                    return True, rule_name

        return False, None
