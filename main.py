from keyword_extractor import extract_keywords
from hashtag_generator import generate_hashtags
from utils import save_json
from apify_trending_for_hashtags import get_trending_hashtags_for_list
import os
from dotenv import load_dotenv

def main(topic, provided_keywords=None):
    # Load environment variables
    load_dotenv()
    if not topic.strip():
        print("Error: Topic cannot be empty")
        return

    # Step 2: Get keywords
    if provided_keywords:
        keywords = provided_keywords
    else:
        keywords = extract_keywords(topic)

    # Normalize helper: convert dict-like items to best readable string
    def normalize_item(item):
        # If already a string, return trimmed
        if isinstance(item, str):
            return item.strip()
        # If dict, try common fields
        if isinstance(item, dict):
            for key in ("title", "text", "query", "q", "searchQuery"):
                if key in item and isinstance(item[key], str) and item[key].strip():
                    return item[key].strip()
            # If URL present, try to extract 'q' param or path
            if "url" in item and isinstance(item["url"], str):
                try:
                    from urllib.parse import urlparse, parse_qs
                    p = urlparse(item["url"])
                    qs = parse_qs(p.query)
                    if "q" in qs and qs["q"]:
                        return qs["q"][0]
                except Exception:
                    pass
            # Fallback to string representation
            return str(item)
        # Other types: convert to string
        return str(item)

    # Convert and normalize keywords to readable strings
    keywords = [normalize_item(k) for k in keywords]

    # Step 3: Generate hashtags using Gemini LLM
    hashtags_gemini = generate_hashtags((keywords, topic))
    hashtags_gemini = [normalize_item(h) for h in hashtags_gemini]

    # --- Debug: show pipeline inputs ---
    print('\n=== Pipeline inputs (pre-Apify) ===')
    print('Extracted keywords :')
    for i, k in enumerate(keywords, 1):
        print(f"  {i}. {k}")

    # Step 4: Use Apify to validate only the Gemini-generated hashtags
    apify_key = os.getenv("APIFY_API_TOKEN")
    trending_hashtags = []
    # Prepare defaults for full list and stats
    full_sorted_list = []
    total_unique = 0
    total_duration = 0.0
    avg = 0.0

    if apify_key:
        # Only use Gemini hashtags for Apify validation
        query_list = [h.strip() for h in hashtags_gemini if isinstance(h, str) and h.strip()]

        print('\nSending Gemini hashtags to Apify for validation:')
        for i, q in enumerate(query_list, 1):
            print(f"  {i}. {q}")

        trending_result = get_trending_hashtags_for_list(query_list)
        # The apify function returns (top_list, full_sorted_list, total_unique, total_duration, avg)
        if isinstance(trending_result, tuple) and len(trending_result) >= 2:
            trending_hashtags, full_sorted, total_unique, total_duration, avg = trending_result

            # Print only summary (no full hashtag list in console)
            print(f"\nFinished processing all queries in {total_duration:.2f} seconds")
            print(f"Average time per query: {avg:.2f} seconds")
            print(f"Total unique hashtags found: {total_unique}\n")

            # Prepare full sorted list for JSON (hashtag + count) but do not print all to console
            full_sorted_list = [{"hashtag": tag, "count": count} for tag, count in full_sorted]
        else:
            # backward compatibility: if function returns simple list
            trending_hashtags = trending_result
    else:
        print("\nNote: Apify validation unavailable (possibly due to API limits).")
        trending_hashtags = []

    # Step 6: Prepare final JSON output (topic, keywords, and Apify trending hashtags)
    # Full result saved to disk (includes full list and stats)
    result_full = {
        "topic": topic,
        "used_keywords": keywords,
        "apify_trending_hashtags": trending_hashtags,
        "apify_trending_hashtags_all": full_sorted_list,
        "apify_total_unique": total_unique,
        "apify_total_duration": total_duration,
        "apify_avg_time_per_query": avg
    }

    # Minimal result to show in console (what you requested)
    result_minimal = {
        "topic": topic,
        "used_keywords": keywords,
        "apify_trending_hashtags": trending_hashtags
    }

    # Step 7: Save full JSON
    save_json(result_full)

    # Print the minimal JSON to console for quick view
    import json
    print(json.dumps(result_minimal, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    # Get topic from user
    topic = input("Enter a topic to generate hashtags for: ")
    keywords_input = input("Enter keywords (comma-separated, or press Enter to skip): ").strip()
    if keywords_input:
        user_keywords = [kw.strip() for kw in keywords_input.split(",")]
    else:
        user_keywords = None
    main(topic, user_keywords)