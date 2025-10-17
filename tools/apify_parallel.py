"""
apify_parallel.py

Safe, standalone wrapper to call an Apify-like API in parallel.
This script does NOT modify your project files. Use it as a drop-in helper.

Functions:
- fetch_for_query(session, api_key, query): low-level single request (requests.Session expected)
- fetch_all_parallel(queries, api_key, max_workers=8, session=None, timeout=30): parallel runner

Usage (example at bottom):
- Import fetch_all_parallel and call with your list of queries. It returns a dict mapping query -> result or None on error.

Note: adapt the APIFY_ENDPOINT and request payload to match your existing `get_trending_hashtags_for_list` expectations.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import time
import logging
from typing import List, Dict, Optional

APIFY_ENDPOINT = "https://api.apify.com/v2/actor-tasks/YOUR_TASK_ID/runs"  # placeholder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_for_query(session: requests.Session, api_key: str, query: str, timeout: int = 30) -> Optional[dict]:
    """Perform a single API call for `query`. Returns parsed JSON or None on error."""
    try:
        # Replace with the actual endpoint and params your project uses
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {"query": query}
        resp = session.post(APIFY_ENDPOINT, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.debug(f"Error fetching query '{query}': {e}")
        return None


def fetch_all_parallel(queries: List[str], api_key: str, max_workers: int = 8, session: requests.Session = None, timeout: int = 30) -> Dict[str, Optional[dict]]:
    """Run requests in parallel and return a mapping from query -> response (or None on error).

    Safety: This function never raises for individual request failures; it logs and returns None for failed queries.
    """
    if session is None:
        session = requests.Session()

    results: Dict[str, Optional[dict]] = {q: None for q in queries}
    start = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(fetch_for_query, session, api_key, q, timeout): q for q in queries}
        for fut in as_completed(futures):
            q = futures[fut]
            try:
                results[q] = fut.result()
            except Exception as e:
                logger.debug(f"Unhandled exception for query '{q}': {e}")
                results[q] = None
    logger.info(f"Completed {len(queries)} queries in {time.time()-start:.2f}s")
    return results


# Simple CLI example (won't run on import)
if __name__ == "__main__":
    import os
    test_queries = ["seo", "marketing", "content marketing", "digital marketing"]
    api_key = os.getenv("APIFY_API_TOKEN") or "your_api_key_here"
    out = fetch_all_parallel(test_queries, api_key, max_workers=4)
    print(out)
