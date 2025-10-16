from scraper import scrape_url
# optional fallback scraper (non-fatal if missing)
try:
    from fallback_scraper import scrape_url_fallback
except Exception:
    scrape_url_fallback = None
from keyword_extractor import extract_keywords
from hashtag_generator import generate_hashtags
from utils import save_json
from apify_trending_for_hashtags import get_trending_hashtags_for_list
import os
from dotenv import load_dotenv

def main(url, provided_keywords=None):
    # Load environment variables
    load_dotenv()
    # Step 1: Scrape URL
    content = scrape_url(url)
    if not content.strip():
        print("[INFO] Primary scraper returned empty or failed — attempting fallback scraper...")
        if scrape_url_fallback:
            try:
                content = scrape_url_fallback(url)
            except Exception as e:
                print(f"[ERROR] Fallback scraper exception: {e}")
        if not content.strip():
            print("Error: No content could be scraped from the URL by either scraper. Please check the site or try another URL.")
            return

    # Step 2: Get keywords
    if provided_keywords:
        keywords = provided_keywords
    else:
        keywords = extract_keywords(content)

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
    hashtags_gemini = generate_hashtags((keywords, content))
    hashtags_gemini = [normalize_item(h) for h in hashtags_gemini]

    # --- Debug: show pipeline inputs ---
    print('\n=== Pipeline inputs (pre-Apify) ===')
    print('Extracted keywords (normalized):')
    for i, k in enumerate(keywords, 1):
        print(f"  {i}. {k}")

    print('\nGemini-generated hashtags (normalized):')
    for i, h in enumerate(hashtags_gemini, 1):
        print(f"  {i}. {h}")

    # Step 4: Use Apify to get all trending hashtags for all keywords and Gemini hashtags
    apify_key = os.getenv("APIFY_API_TOKEN")
    trending_hashtags = []
    if apify_key:
        # Combine, filter empty, dedupe, and ensure readable strings
        combined = [q for q in (keywords + hashtags_gemini) if isinstance(q, str) and q.strip()]
        # Deduplicate while preserving readability
        seen = set()
        query_list = []
        for q in combined:
            nq = q.strip()
            if nq not in seen:
                seen.add(nq)
                query_list.append(nq)

        # Debug: show final query list that will be processed by Apify
        print('\nQueries to be sent to Apify (normalized + deduped):')
        for i, q in enumerate(query_list, 1):
            print(f"  {i}. {q}")

        trending_hashtags = get_trending_hashtags_for_list(query_list)
    # Step 5: Use Gemini LLM to select the top 20 most relevant trending hashtags
    if trending_hashtags:
        def select_top_hashtags(trending_hashtags, keywords, content):
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            prompt = (
                "You are an expert SEO auditor and social media strategist.\n"
                "Given the following list of trending hashtags, keywords, and company page content, "
                "select the 20 most relevant, currently trending hashtags for a company SEO audit report.\n"
                "All hashtags must meet company standards: professional, SEO-friendly, and suitable for enterprise use.\n"
                "Avoid generic, unrelated, or overused hashtags.\n"
                "Return only the hashtags, separated by commas, no extra text.\n\n"
                f"Trending Hashtags:\n{', '.join(trending_hashtags)}\n\n"
                f"Keywords:\n{', '.join(keywords)}\n\n"
                f"Page Content:\n{content}\n"
            )
            try:
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(prompt, generation_config={"temperature": 0})
                hashtags_llm = [tag.strip().replace(' ', '') if tag.strip().startswith('#') else '#' + tag.strip().replace(' ', '') for tag in response.text.split(",") if tag.strip()]
                return hashtags_llm[:20]
            except Exception as e:
                print(f"Gemini LLM hashtag selection error: {e}")
                return trending_hashtags[:20]
        trending_hashtags = select_top_hashtags(trending_hashtags, keywords, content)
    else:
        print("Warning: No trending hashtags found from SerpApi.")

    # Step 6: Prepare final JSON output (only url, keywords, and Apify trending hashtags)
    result = {
        "url": url,
        "used_keywords": keywords,
        "apify_trending_hashtags": trending_hashtags
    }

    # Step 7: Save JSON
    save_json(result)

    # Also print to console
    import json
    print(json.dumps(result, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    # Get URL from user
    url = input("Enter URL to scrape: ")
    keywords_input = input("Enter keywords (comma-separated, or press Enter to skip): ").strip()
    if keywords_input:
        user_keywords = [kw.strip() for kw in keywords_input.split(",")]
    else:
        user_keywords = None
    main(url, user_keywords)