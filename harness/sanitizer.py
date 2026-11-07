"""
Sanitizer and Local JSON Repair Engine with Strict Brevity Trimmer.
Extracts and repairs JSON, removes conversational fluff, and enforces extreme brevity.
"""

from __future__ import annotations
import json
import re
from typing import Any, Dict, Optional, Tuple
from harness.schemas import StructuredOutput


CONVERSATIONAL_FLUFF_PATTERNS = [
    r"^(?:sure(?:ly)?|certainly|of course|hello|hi|hey)[,!.]?\s*",
    r"^(?:as requested|i have (?:completed|finished|implemented|created)|here is(?: the)?)[,!.]?\s*",
    r"^(?:i apologize(?: for)?|sorry(?: for)?)[,!.]?\s*",
    r"^(?:i am happy to help|let me know if you need)[,!.]?\s*",
]


class OutputSanitizer:
    """Extracts, repairs, and validates StructuredOutput from raw agent strings."""

    @staticmethod
    def extract_json_block(text: str) -> Optional[str]:
        """Extracts JSON substring from markdown code blocks or curly braces."""
        if not text or not text.strip():
            return None

        # 1. Try markdown code block ```json ... ``` or ``` ... ```
        code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if code_block_match:
            candidate = code_block_match.group(1).strip()
            if candidate.startswith("{") and candidate.endswith("}"):
                return candidate

        # 2. Find outermost curly braces { ... }
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return text[start_idx : end_idx + 1].strip()

        return None

    @classmethod
    def local_repair_json(cls, raw_json: str) -> str:
        """Applies deterministic regex rules to fix common LLM JSON syntax bugs."""
        cleaned = raw_json.strip()

        # Remove trailing commas before closing braces/brackets: ,} -> } and ,] -> ]
        cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)

        # Fix single quotes around keys or string values to double quotes
        cleaned = re.sub(r"(?<=[{\s,])'([a-zA-Z0-9_]+)'\s*:", r'"\1":', cleaned)
        cleaned = re.sub(r':\s*\'([^\'\\]*(?:\\.[^\'\\]*)*)\'', r': "\1"', cleaned)

        # Replace python True/False/None with true/false/null
        cleaned = re.sub(r"\bTrue\b", "true", cleaned)
        cleaned = re.sub(r"\bFalse\b", "false", cleaned)
        cleaned = re.sub(r"\bNone\b", "null", cleaned)

        return cleaned

    @classmethod
    def trim_conversational_fluff(cls, text: str, max_chars: int = 250) -> str:
        """Removes conversational pleasantries and enforces strict brevity."""
        cleaned = text.strip()
        for pattern in CONVERSATIONAL_FLUFF_PATTERNS:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

        # Enforce max length
        if len(cleaned) > max_chars:
            cleaned = cleaned[: max_chars - 3].rstrip() + "..."
        return cleaned

    @classmethod
    def parse_structured_output(
        cls,
        raw_text: str,
        enforce_brevity: bool = True,
        max_summary_chars: int = 250,
        max_feedback_chars: int = 1000,
    ) -> Tuple[Optional[StructuredOutput], Optional[str]]:
        """
        Parses raw text into StructuredOutput with optional zero-fluff brevity trimming.
        """
        json_candidate = cls.extract_json_block(raw_text)
        if not json_candidate:
            return None, "No JSON object found in output. Ensure output contains a valid JSON block."

        parsed_dict: Optional[Dict[str, Any]] = None

        # Attempt 1: Direct JSON parse
        try:
            data = json.loads(json_candidate)
            if isinstance(data, dict):
                parsed_dict = data
        except json.JSONDecodeError:
            pass

        # Attempt 2: Local Repair
        if parsed_dict is None:
            repaired = cls.local_repair_json(json_candidate)
            try:
                data = json.loads(repaired)
                if isinstance(data, dict):
                    parsed_dict = data
                else:
                    return None, "Parsed JSON is not an object/dictionary."
            except json.JSONDecodeError as err:
                return None, f"JSON syntax error could not be repaired locally: {str(err)}"

        output = StructuredOutput.from_dict(parsed_dict)

        # Enforce Extreme Brevity (Rule 4)
        if enforce_brevity:
            output.summary = cls.trim_conversational_fluff(output.summary, max_chars=max_summary_chars)
            if output.review_feedback:
                output.review_feedback = cls.trim_conversational_fluff(output.review_feedback, max_chars=max_feedback_chars)

        return output, None
