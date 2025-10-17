"""
dedupe_filter.py

Utilities to normalize, deduplicate, and filter keyword lists before sending to Apify.
This module is safe, pure-Python, and has no external side effects.

Functions:
- normalize_text(s): lowercase, trim, remove extra spaces
- normalize_items(items): convert many input types to strings and normalize
- dedupe_preserve_order(items): remove exact duplicates preserving order
- filter_generic(items, stop_words=None, min_len=2): remove overly generic or short tokens

Usage:
- from tools.dedupe_filter import normalize_items, dedupe_preserve_order, filter_generic

"""
import re
from typing import Iterable, List

GENERIC_STOP_WORDS = {"the", "a", "an", "and", "or", "to", "in", "on", "for", "with", "of"}


def normalize_text(s: str) -> str:
    s = s or ""
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_items(items: Iterable) -> List[str]:
    out = []
    for it in items:
        if it is None:
            continue
        if isinstance(it, str):
            t = normalize_text(it)
            if t:
                out.append(t)
            continue
        if isinstance(it, dict):
            # common fields
            for key in ("title", "text", "query", "q", "searchQuery", "name"):
                if key in it and isinstance(it[key], str) and it[key].strip():
                    out.append(normalize_text(it[key]))
                    break
            else:
                out.append(normalize_text(str(it)))
            continue
        # fallback
        out.append(normalize_text(str(it)))
    return out


def dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    out = []
    for it in items:
        if it in seen:
            continue
        seen.add(it)
        out.append(it)
    return out


def filter_generic(items: Iterable[str], stop_words: Iterable[str] = None, min_len: int = 2) -> List[str]:
    stop = set(GENERIC_STOP_WORDS)
    if stop_words:
        stop.update(w.lower().strip() for w in stop_words)
    out = []
    for it in items:
        t = it.strip()
        if len(t) < min_len:
            continue
        if t.lower() in stop:
            continue
        out.append(t)
    return out


# Quick test
if __name__ == "__main__":
    samples = ["SEO", " seo ", {"title": "Content Marketing"}, "and", "a"]
    n = normalize_items(samples)
    n = dedupe_preserve_order(n)
    n = filter_generic(n)
    print(n)
