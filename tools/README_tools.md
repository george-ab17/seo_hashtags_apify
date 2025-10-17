Tools README

This folder contains three helper scripts you can use to speed up Apify calls and avoid redundant requests.

Files:
- apify_parallel.py: parallel requester wrapper using ThreadPoolExecutor. Adjust APIFY_ENDPOINT and payload to match your project.
- dedupe_filter.py: normalization, dedupe_preserve_order, and filter_generic utilities to reduce queries before sending to Apify.
- cache.py: FileCache class (JSON file store) with TTL to cache responses per-query.

Suggested integration (theory, no code changes to main.py here):
1. Normalize and dedupe queries
   from tools.dedupe_filter import normalize_items, dedupe_preserve_order, filter_generic
   raw = keywords + gemini_hashtags
   norm = normalize_items(raw)
   norm = dedupe_preserve_order(norm)
   norm = filter_generic(norm, stop_words=['company', 'enterprise'], min_len=3)

2. Check cache
   from tools.cache import FileCache
   cache = FileCache('tools/cache_store.json', default_ttl=86400)
   to_query = []
   cached_results = {}
   for q in norm:
       v = cache.get(q)
       if v is not None:
           cached_results[q] = v
       else:
           to_query.append(q)

3. Fetch remaining queries in parallel
   from tools.apify_parallel import fetch_all_parallel
   fresh = fetch_all_parallel(to_query, api_key, max_workers=6)

4. Merge fresh results and cache them
   for q, res in fresh.items():
       if res is not None:
           cache.set(q, res)

5. Build final results list from cached_results + fresh

Notes and safety:
- All helpers are isolated in the `tools/` folder and do not modify your existing code.
- Run them separately first to test. They are defensive: failed API calls return None and don't raise.
- Tune `max_workers` to 4-8 depending on your internet and Apify rate limits.

If you want, I can implement the integration directly into `main.py` or create an `integration_example.py` that wires everything together. Say which you prefer.
