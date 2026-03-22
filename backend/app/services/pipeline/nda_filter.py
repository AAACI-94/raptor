"""NDA filter: cross-cutting concern for content sensitivity."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class NDAFilter:
    """Scans content for potentially sensitive information based on project NDA config."""

    def scan(self, content: str, nda_config: dict | None) -> dict:
        """Scan content for NDA violations.

        Returns: {flagged: bool, flags: [{term, context, suggestion}]}
        """
        if not nda_config:
            return {"flagged": False, "flags": []}

        blocked_terms = nda_config.get("blocked_terms", [])
        mode = nda_config.get("mode", "flag")
        flags = []

        for term in blocked_terms:
            if term.lower() in content.lower():
                # Find context around the match
                idx = content.lower().find(term.lower())
                context = content[max(0, idx - 50):idx + len(term) + 50]
                flags.append({
                    "term": term,
                    "context": context,
                    "suggestion": f"Replace '{term}' with a generalized form",
                })

        # Check generalization rules
        for rule in nda_config.get("generalization_rules", []):
            pattern = rule.get("pattern", "")
            if pattern and re.search(pattern, content, re.IGNORECASE):
                flags.append({
                    "term": pattern,
                    "context": "Pattern match",
                    "suggestion": rule.get("replacement_template", "Generalize this content"),
                })

        if mode == "block" and flags:
            logger.warning("[nda-filter] BLOCKED: %d sensitive items found", len(flags))
        elif flags:
            logger.info("[nda-filter] Flagged: %d potentially sensitive items", len(flags))

        return {"flagged": len(flags) > 0, "flags": flags, "mode": mode}

    def apply_generalizations(self, content: str, nda_config: dict) -> str:
        """Apply automatic generalization rules to content."""
        if nda_config.get("mode") != "auto_generalize":
            return content

        for rule in nda_config.get("generalization_rules", []):
            pattern = rule.get("pattern", "")
            replacement = rule.get("replacement_template", "")
            if pattern and replacement:
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

        return content


# Singleton
nda_filter = NDAFilter()
