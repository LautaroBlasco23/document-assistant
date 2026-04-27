"""Token counting and truncation utilities using tiktoken."""

from functools import lru_cache

import tiktoken


@lru_cache(maxsize=1)
def _encoder() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoder().encode(text or ""))


def truncate_tokens(text: str, max_tokens: int) -> str:
    enc = _encoder()
    ids = enc.encode(text or "")
    if len(ids) <= max_tokens:
        return text
    return enc.decode(ids[:max_tokens])
