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
# Max pages/items per query passed to the actors
MAX_PAGES_PER_QUERY = 1
MAX_TWEETS_PER_QUERY = 10
MAX_INSTAGRAM_POSTS = 10

# Apify actor IDs
ACTORS = {
    'google': 'apify/google-search-scraper',
    'twitter': 'quacker/twitter-scraper',
    'instagram': 'apify/instagram-hashtag-scraper'
}
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
    For each hashtag/keyword, search across multiple platforms using Apify actors:
    - Google Search (for web content)
    - Twitter/X (for social media trends)
    
    Args:
      hashtags: iterable of strings/dicts (keywords or hashtags)
      num_results: reserved for compatibility (not used)

    Returns:
      List[str] - unique hashtags found across all platforms (e.g., '#AI', '#MachineLearning')
    """
    api_key = os.getenv("APIFY_API_TOKEN")
    if not api_key:
        raise ValueError("APIFY_API_TOKEN not set in environment variables.")

    client = ApifyClient(api_key)
    hashtag_pattern = re.compile(r"#\w+")
    trending = {}

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

        # Call the actors with retries and suppress stdout/stderr
        run_google = None
        run_twitter = None
        run_instagram = None
        last_exc = None

        # Google Search - with retries
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
                    run_google = client.actor(ACTORS['google']).call(run_input=run_input)
                break
            except Exception as exc:
                print(f"Google Search attempt {attempt} failed: {exc}")
                if attempt == APIFY_CALL_RETRIES:
                    print(f"Google Search failed after {APIFY_CALL_RETRIES} attempts")
                sleep_time = APIFY_CALL_BACKOFF_SECONDS * (2 ** (attempt - 1))
                time.sleep(sleep_time)

        # Twitter Search - with retries
        for attempt in range(1, APIFY_CALL_RETRIES + 1):
            try:
                twitter_input = {
                    "searchTerms": [search_phrase],
                    "maxItems": MAX_TWEETS_PER_QUERY,
                }
                with suppress_stdout_stderr():
                    run_twitter = client.actor(ACTORS['twitter']).call(run_input=twitter_input)
                break
            except Exception as exc:
                print(f"Twitter Search attempt {attempt} failed: {exc}")
                if attempt == APIFY_CALL_RETRIES:
                    print(f"Twitter Search failed after {APIFY_CALL_RETRIES} attempts")
                sleep_time = APIFY_CALL_BACKOFF_SECONDS * (2 ** (attempt - 1))
                time.sleep(sleep_time)
                    
        
        # Instagram Search - with retries
        for attempt in range(1, APIFY_CALL_RETRIES + 1):
            try:
                instagram_input = {
                    "hashtags": [search_phrase.replace(' ', '')],
                    "limit": MAX_INSTAGRAM_POSTS,
                    "searchType": "hashtag",
                    "resultsType": "posts"
                }
                with suppress_stdout_stderr():
                    run_instagram = client.actor(ACTORS['instagram']).call(run_input=instagram_input)
                break
            except Exception as exc:
                print(f"Instagram Search attempt {attempt} failed: {exc}")
                if attempt == APIFY_CALL_RETRIES:
                    print(f"Instagram Search failed after {APIFY_CALL_RETRIES} attempts")
                sleep_time = APIFY_CALL_BACKOFF_SECONDS * (2 ** (attempt - 1))
                time.sleep(sleep_time)
        # Check if all searches failed
        if not any([run_google, run_twitter, run_instagram]):
            print(f"All platform searches failed for '{search_input}'")
            continue

        # Process results from all platforms
        try:
            # Google results
            google_items = []
            if run_google and run_google.get("defaultDatasetId"):
                google_items = list(client.dataset(run_google.get("defaultDatasetId")).iterate_items())
            
            # Twitter results
            twitter_items = []
            if run_twitter and run_twitter.get("defaultDatasetId"):
                twitter_items = list(client.dataset(run_twitter.get("defaultDatasetId")).iterate_items())
            
            # Instagram results
            instagram_items = []
            if run_instagram and run_instagram.get("defaultDatasetId"):
                instagram_items = list(client.dataset(run_instagram.get("defaultDatasetId")).iterate_items())
            
        except Exception as exc:
            print(f"Failed to read datasets for '{search_input}': {exc}")
            continue

        # Process Google results
        for item in google_items:
            # Organic results
            organic = item.get("organicResults") or []
            for result in organic:
                # Title & snippet & description and other text fields
                for field in ("title", "snippet", "description", "plainText", "text"):
                    val = result.get(field) if isinstance(result, dict) else None
                    if isinstance(val, str):
                        for m in hashtag_pattern.findall(val):
                            trending[m] = trending.get(m, 0) + 1
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
                        trending[m] = trending.get(m, 0) + 1

            # Some actors provide aiMode/aiOverview fields; scan them safely
            for ai_field in ("aiOverview", "aiModeResults", "aiOverviews"):
                ai_val = item.get(ai_field)
                if isinstance(ai_val, str):
                    for m in hashtag_pattern.findall(ai_val):
                        trending[m] = trending.get(m, 0) + 1
                elif isinstance(ai_val, list):
                    for sub in ai_val:
                        if isinstance(sub, str):
                            for m in hashtag_pattern.findall(sub):
                                trending[m] = trending.get(m, 0) + 1
                
        # Process Twitter results
        for tweet in twitter_items:
            # Extract hashtags from tweet text and description
            text = tweet.get('full_text', '') or tweet.get('text', '')
            for m in hashtag_pattern.findall(text):
                trending[m] = trending.get(m, 0) + 2  # Weight Twitter mentions more
            # Also check tweet entities if available
            entities = tweet.get('entities', {})
            if entities and 'hashtags' in entities:
                for hashtag in entities['hashtags']:
                    tag = hashtag.get('text', '')
                    if tag:
                        tag_with_hash = f'#{tag}'
                    trending[tag_with_hash] = trending.get(tag_with_hash, 0) + 2  # Weight Twitter entities more
                        
        # Process Instagram results
        for post in instagram_items:
            # Extract hashtags from post caption
            caption = post.get('caption', '')
            if caption:
                for m in hashtag_pattern.findall(caption):
                    trending[m] = trending.get(m, 0) + 2  # Weight Instagram mentions more
            # Extract related hashtags
            related_tags = post.get('relatedHashtags', []) or post.get('related_hashtags', [])
            for tag in related_tags:
                if isinstance(tag, str):
                    tag_with_hash = f'#{tag.strip().replace("#", "")}'
                    trending[tag_with_hash] = trending.get(tag_with_hash, 0) + 2  # Weight Instagram related tags more
                elif isinstance(tag, dict) and 'name' in tag:
                    tag_with_hash = f'#{tag["name"].strip().replace("#", "")}'
                    trending[tag_with_hash] = trending.get(tag_with_hash, 0) + 2

        q_duration = time.time() - q_start
        print(f"Processed '{search_phrase}' ({processed}/{total_queries}) in {q_duration:.2f}s")

    total_duration = time.time() - start_time
    avg = total_duration / total_queries if total_queries else 0.0
    print(f"\nFinished processing all queries in {total_duration:.2f} seconds")
    print(f"Average time per query: {avg:.2f} seconds")
    print(f"Total unique hashtags found: {len(trending)}\n")

    # Sort hashtags by frequency
    sorted_hashtags = sorted(trending.items(), key=lambda x: x[1], reverse=True)

    # Prepare statistics
    total_unique = len(trending)
    total_duration = time.time() - start_time
    avg = total_duration / total_queries if total_queries else 0.0

    # Return: top-N list, full sorted list (hashtag,count), total unique, total duration, avg per query
    top_n = [hashtag for hashtag, _ in sorted_hashtags[:5]]
    return top_n, sorted_hashtags, total_unique, total_duration, avg