from __future__ import annotations

import re
from dataclasses import dataclass

BEGIN = "<!-- aicj:begin -->"
END = "<!-- aicj:end -->"
BLOCK_RE = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.DOTALL)


@dataclass(frozen=True)
class BlockAction:
    kind: str
    text: str


def has_block(text: str) -> bool:
    return BEGIN in text and END in text


def build_block(reference: str) -> str:
    return f"{BEGIN}\n@{reference}\n{END}\n"


def append_block(text: str, reference: str) -> str:
    if has_block(text):
        return text
    body = text
    if body and not body.endswith("\n"):
        body += "\n"
    return body + build_block(reference)


def remove_block(text: str) -> tuple[str, bool]:
    if not has_block(text):
        return text, False
    return BLOCK_RE.sub("", text), True
