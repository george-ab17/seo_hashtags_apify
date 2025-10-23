import os
import re
import time
import sys
import io
import ast
import logging
from contextlib import contextmanager
from datetime import datetime
from apify_client import ApifyClient

# ------------- Configuration -------------
# Tune these if you need fewer/more retries or longer timeouts
APIFY_CALL_RETRIES = 3
APIFY_CALL_BACKOFF_SECONDS = 2
# Max pages per query passed to the actor (keeps each actor run short)
MAX_PAGES_PER_QUERY = 1
# -----------------------------------------

# Minimal logging for the script; suppress noisy libraries
logging.getLogger().setLevel(logging.ERROR)
for logger_name in ("apify", "playwright", "urllib3"):
    logging.getLogger(logger_name).setLevel(logging.ERROR)

@contextmanager
def suppress_stdout_stderr():
    """Temporarily redirect stdout and stderr to devnull."""
    new_stdout, new_stderr = io.StringIO(), io.StringIO()
    old_stdout, old_stderr = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_stdout, new_stderr
        yield
    finally:
        sys.stdout, sys.stderr = old_stdout, old_stderr

def _try_literal_eval(s):
    """Safely parse a string that might contain a Python literal dict."""
    try:
        parsed = ast.literal_eval(s)
        return parsed
    except Exception:
        return None

def normalize_query_item(tag):
    """
    Normalize an input tag (string, dict, or stringified dict) into a clean text query.
    Priority:
      - If string: trimmed string
      - If dict: title, text, query, q, searchQuery, snippet fields
      - If contains 'url' extract ?q= param
      - If string looks like a dict, try literal_eval then apply dict rules
      - Regex fallback: extract 'title' or ?q= from the string
      - Fallback: str(tag)
    """
    # If it's already a string, trim and return
    if isinstance(tag, str):
        s = tag.strip()
        # try parse stringified dict first if it looks like one
        if s.startswith("{") and ":" in s:
            parsed = _try_literal_eval(s)
            if isinstance(parsed, dict):
                return normalize_query_item(parsed)
            # regex fallback: extract title or q param
            import re, urllib.parse
            m = re.search(r"(?:'|\")?title(?:'|\")?\s*:\s*(?:'|\")([^'\"]+)(?:'|\")", s)
            if m:
                return m.group(1).strip()
            m2 = re.search(r"[?&]q=([^&\s]+)", s)
            if m2:
                return urllib.parse.unquote_plus(m2.group(1)).strip()
        return s

    # If it's a dict, try common fields
    if isinstance(tag, dict):
        for key in ("title", "text", "query", "q", "searchQuery", "snippet"):
            if key in tag and isinstance(tag[key], str) and tag[key].strip():
                return tag[key].strip()
        # try extracting q from url
        if "url" in tag and isinstance(tag["url"], str):
            try:
                from urllib.parse import urlparse, parse_qs, unquote_plus
                p = urlparse(tag["url"])
                qs = parse_qs(p.query)
                if "q" in qs and qs["q"]:
                    return unquote_plus(qs["q"][0]).strip()
                # fallback to path
                if p.path and p.path.strip("/"):
                    return p.path.strip("/").replace("-", " ").replace("_", " ")
            except Exception:
                pass
        # fallback to str(tag) as last resort
        return str(tag)

    # Other types: return stringified form
    try:
        return str(tag)
    except Exception:
        return ""

def get_trending_hashtags_for_list(hashtags, num_results=1):
    """
    For each hashtag/keyword in `hashtags`, run Apify's Google Search Scraper actor,
    extract hashtags from the actor results, and return a list of unique hashtags.

    Args:
      hashtags: iterable of strings/dicts (keywords or hashtags)
      num_results: reserved for compatibility (not used by this actor wrapper)

    Returns:
      List[str] - unique hashtags found (e.g., '#AI', '#MachineLearning')
    """
    api_key = os.getenv("APIFY_API_TOKEN")
    if not api_key:
        raise ValueError("APIFY_API_TOKEN not set in environment variables.")

    client = ApifyClient(api_key)
    hashtag_pattern = re.compile(r"#\w+")
    trending = set()

    # Only process hashtags from Gemini, not keywords
    normalized = []
    seen = set()
    for item in hashtags:
        # Only process items that start with '#' since we only want hashtags from Gemini
        if isinstance(item, str) and item.startswith('#'):
            q = normalize_query_item(item)
            if not q:
                continue
            q = q.strip()
            if not q:
                continue
            if q not in seen:
                seen.add(q)
                normalized.append(q)

    total_queries = len(normalized)
    if total_queries == 0:
        return []

    print(f"\nStarting hashtag search at {datetime.now().strftime('%H:%M:%S')}")
    print(f"Total queries to process: {total_queries}\n")

    start_time = time.time()
    processed = 0

    for query_text in normalized:
        # remove leading '#' if present (we search keywords, not hashtag tokens)
        search_phrase = query_text.lstrip("#").strip()
        search_input = f"trending hashtags for {search_phrase}"
        processed += 1
        q_start = time.time()

        # Call the actor with retries and suppress actor stdout/stderr
        run = None
        last_exc = None
        for attempt in range(1, APIFY_CALL_RETRIES + 1):
            try:
                run_input = {
                    "queries": search_input,
                    "maxPagesPerQuery": MAX_PAGES_PER_QUERY,
                    "languageCode": "en",
                    "mobileResults": False,
                    "includeUnfilteredResults": True
                }
                with suppress_stdout_stderr():
                    run = client.actor("apify/google-search-scraper").call(run_input=run_input)
                last_exc = None
                break
            except Exception as exc:
                last_exc = exc
                sleep_time = APIFY_CALL_BACKOFF_SECONDS * (2 ** (attempt - 1))
                time.sleep(sleep_time)

        if last_exc and run is None:
            print(f"Apify error for '{search_input}': {last_exc}")
            continue

        # Retrieve dataset items (suppress actor logs)
        dataset_items = []
        try:
            with suppress_stdout_stderr():
                dataset_items = list(client.dataset(run.get("defaultDatasetId", "")).iterate_items())
        except Exception as exc:
            print(f"Failed to read Apify dataset for '{search_input}': {exc}")
            continue

        # Extract hashtags from organicResults, relatedQueries, snippets etc.
        for item in dataset_items:
            # Organic results
            organic = item.get("organicResults") or []
            for result in organic:
                # Title & snippet & description and other text fields
                for field in ("title", "snippet", "description", "plainText", "text"):
                    val = result.get(field) if isinstance(result, dict) else None
                    if isinstance(val, str):
                        for m in hashtag_pattern.findall(val):
                            trending.add(m)
                # Sometimes result fields themselves can be dicts (rare); attempt safe access
                # (we intentionally don't crash if structure is unexpected)

            # Related queries (could be strings or dicts)
            related = item.get("relatedQueries") or []
            for r in related:
                # r may be string or dict with 'text' or 'query'
                if isinstance(r, str):
                    text_to_check = r
                elif isinstance(r, dict):
                    text_to_check = r.get("text") or r.get("query") or r.get("title") or ""
                else:
                    text_to_check = str(r)
                if isinstance(text_to_check, str):
                    for m in hashtag_pattern.findall(text_to_check):
                        trending.add(m)

            # Some actors provide aiMode/aiOverview fields; scan them safely
            for ai_field in ("aiOverview", "aiModeResults", "aiOverviews"):
                ai_val = item.get(ai_field)
                if isinstance(ai_val, str):
                    for m in hashtag_pattern.findall(ai_val):
                        trending.add(m)
                elif isinstance(ai_val, list):
                    for sub in ai_val:
                        if isinstance(sub, str):
                            for m in hashtag_pattern.findall(sub):
                                trending.add(m)

        q_duration = time.time() - q_start
        print(f"Processed '{search_phrase}' ({processed}/{total_queries}) in {q_duration:.2f}s")

    total_duration = time.time() - start_time
    avg = total_duration / total_queries if total_queries else 0.0
    print(f"\nFinished processing all queries in {total_duration:.2f} seconds")
    print(f"Average time per query: {avg:.2f} seconds")
    print(f"Total unique hashtags found: {len(trending)}\n")

    return list(trending)