from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

SECRET_PATTERNS = {
    "api_key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "jwt": re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    "private_key": re.compile(r"-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----"),
    "token": re.compile(r"tok_[A-Za-z0-9]{16,}"),
}

PII_PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "phone": re.compile(r"\+?[0-9][0-9\-() ]{7,}[0-9]"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "address": re.compile(r"\b\d{1,5} [A-Za-z0-9 .-]+ (Street|St|Avenue|Ave|Road|Rd|Lane|Ln)\b"),
}


@dataclass(frozen=True)
class RedactionResult:
    payload: dict[str, Any]
    redactions: list[str]


REDACTION_TOKEN = "[REDACTED]"


def _scrub_text(text: str, patterns: dict[str, re.Pattern[str]], redactions: list[str]) -> str:
    scrubbed = text
    for label, pattern in patterns.items():
        if pattern.search(scrubbed):
            redactions.append(label)
            scrubbed = pattern.sub(REDACTION_TOKEN, scrubbed)
    return scrubbed


def redact_payload(payload: dict[str, Any]) -> RedactionResult:
    redactions: list[str] = []

    def scrub(value: Any) -> Any:
        if isinstance(value, str):
            value = _scrub_text(value, SECRET_PATTERNS, redactions)
            value = _scrub_text(value, PII_PATTERNS, redactions)
            return value
        if isinstance(value, dict):
            return {key: scrub(item) for key, item in value.items()}
        if isinstance(value, list):
            return [scrub(item) for item in value]
        return value

    return RedactionResult(payload=scrub(payload), redactions=sorted(set(redactions)))
