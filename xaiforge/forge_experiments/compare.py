from __future__ import annotations

import difflib
from dataclasses import dataclass


@dataclass(frozen=True)
class DiffSummary:
    score: float
    summary: str


def compare_text(primary: str, secondary: str) -> DiffSummary:
    primary_tokens = _tokenize(primary)
    secondary_tokens = _tokenize(secondary)
    matcher = difflib.SequenceMatcher(a=primary_tokens, b=secondary_tokens)
    score = matcher.ratio()
    chunks = []
    for opcode, a0, a1, b0, b1 in matcher.get_opcodes():
        if opcode == "equal":
            continue
        before = " ".join(primary_tokens[a0:a1])
        after = " ".join(secondary_tokens[b0:b1])
        chunks.append(f"{opcode}: '{before}' -> '{after}'")
    summary = " | ".join(chunks) if chunks else "no_diff"
    return DiffSummary(score=score, summary=summary)


def compare_tool_calls(
    primary: list[dict],
    secondary: list[dict],
) -> dict:
    primary_names = [item.get("name") for item in primary]
    secondary_names = [item.get("name") for item in secondary]
    added = [name for name in secondary_names if name not in primary_names]
    removed = [name for name in primary_names if name not in secondary_names]
    mismatched = []
    for index, primary_call in enumerate(primary):
        if index >= len(secondary):
            continue
        if primary_call.get("arguments") != secondary[index].get("arguments"):
            mismatched.append(
                {
                    "index": index,
                    "primary": primary_call.get("arguments"),
                    "secondary": secondary[index].get("arguments"),
                }
            )
    return {
        "added": added,
        "removed": removed,
        "mismatched": mismatched,
    }


def _tokenize(text: str) -> list[str]:
    return [token for token in text.replace("\n", " ").split(" ") if token]
