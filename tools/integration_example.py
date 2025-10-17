"""
integration_example.py

Safe integration example that wires together:
- dedupe_filter.normalize_items, dedupe_preserve_order, filter_generic
- cache.FileCache
- apify_parallel.fetch_all_parallel

Provides:
- get_trending_hashtags_with_tools(query_list, api_key, cache_path, max_workers)

This function is defensive: it uses cache where available, fetches remaining queries in parallel, caches fresh results, and returns a merged mapping of query -> response.

It is meant as a drop-in replacement for `get_trending_hashtags_for_list` behavior but kept separate so you can test it safely.

"""
from typing import List, Dict, Any, Optional
from tools.dedupe_filter import normalize_items, dedupe_preserve_order, filter_generic
from tools.cache import FileCache
from tools.apify_parallel import fetch_all_parallel
import logging
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_trending_hashtags_with_tools(raw_queries: List[str], api_key: str, cache_path: str = 'tools/cache_store.json', max_workers: int = 6, min_len: int = 2) -> Dict[str, Optional[dict]]:
    """Normalize, dedupe, cache-check, parallel-fetch, cache-store, and return mapping query->response.

    Returns a dict where each original normalized query maps to either the cached/fresh response (dict) or None if fetch failed.
    """
    if not raw_queries:
        return {}

    # 1. Normalize
    normalized = normalize_items(raw_queries)
    normalized = [q for q in normalized if q]
    # 2. Filter generic and short
    filtered = filter_generic(normalized, min_len=min_len)
    # 3. Dedupe preserve order
    to_process = dedupe_preserve_order(filtered)

    # 4. Setup cache
    cache = FileCache(cache_path, default_ttl=24*3600)

    # 5. Separate cached and to-query
    cached_results: Dict[str, Any] = {}
    need_query: List[str] = []
    for q in to_process:
        v = cache.get(q)
        if v is not None:
            cached_results[q] = v
        else:
            need_query.append(q)

    logger.info(f"{len(cached_results)} cached, {len(need_query)} to query")

    # 6. Parallel fetch remaining
    fresh_results = {}
    if need_query:
        fresh_results = fetch_all_parallel(need_query, api_key, max_workers=max_workers)
        # store successful results
        for q, res in fresh_results.items():
            if res is not None:
                try:
                    cache.set(q, res)
                except Exception:
                    logger.debug('Failed to cache result for ' + q)

    # 7. Merge and return
    merged = {**cached_results, **(fresh_results or {})}
    # Ensure all requested queries exist in keys
    for q in to_process:
        if q not in merged:
            merged[q] = None
    return merged


# CLI demo
if __name__ == '__main__':
    import os
    sample = ["SEO", "marketing", "content marketing", "SEO", "the"]
    key = os.getenv('APIFY_API_TOKEN') or 'demo_key'
    out = get_trending_hashtags_with_tools(sample, key, cache_path='tools/cache_store.json', max_workers=4)
    import json
    print(json.dumps(out, indent=2))
