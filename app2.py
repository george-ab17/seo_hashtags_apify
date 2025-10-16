from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# Import your hashtag generation modules
from scraper import scrape_url
from keyword_extractor import extract_keywords
from hashtag_generator import generate_hashtags
from apify_trending_for_hashtags import get_trending_hashtags_for_list
import google.generativeai as genai

# Optional fallback scraper
try:
    from fallback_scraper import scrape_url_fallback
except Exception:
    scrape_url_fallback = None

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Create logs directory if it doesn't exist
LOGS_DIR = "logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

def normalize_item(item):
    """Convert dict-like items to readable string"""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in ("title", "text", "query", "q", "searchQuery"):
            if key in item and isinstance(item[key], str) and item[key].strip():
                return item[key].strip()
        if "url" in item and isinstance(item["url"], str):
            try:
                from urllib.parse import urlparse, parse_qs
                p = urlparse(item["url"])
                qs = parse_qs(p.query)
                if "q" in qs and qs["q"]:
                    return qs["q"][0]
            except Exception:
                pass
        return str(item)
    return str(item)

def select_top_hashtags(trending_hashtags, keywords, content):
    """Use Gemini LLM to select top 20 most relevant hashtags"""
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
        hashtags_llm = [
            tag.strip().replace(' ', '') if tag.strip().startswith('#') 
            else '#' + tag.strip().replace(' ', '') 
            for tag in response.text.split(",") if tag.strip()
        ]
        return hashtags_llm[:20]
    except Exception as e:
        print(f"Gemini LLM hashtag selection error: {e}")
        return trending_hashtags[:20]

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/generate-hashtags', methods=['POST'])
def generate_hashtags_api():
    """API endpoint for generating hashtags"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        provided_keywords = data.get('provided_keywords')

        # Validate URL
        if not url:
            return jsonify({"error": "URL is required"}), 400

        print(f"\n[INFO] Processing URL: {url}")

        # Step 1: Scrape URL
        content = scrape_url(url)
        if not content.strip():
            print("[INFO] Primary scraper returned empty — attempting fallback scraper...")
            if scrape_url_fallback:
                try:
                    content = scrape_url_fallback(url)
                except Exception as e:
                    print(f"[ERROR] Fallback scraper exception: {e}")
            
            if not content.strip():
                return jsonify({
                    "error": "No content could be scraped from the URL by either scraper. Please check the site or try another URL."
                }), 400

        # Step 2: Get keywords
        if provided_keywords:
            keywords = provided_keywords
        else:
            keywords = extract_keywords(content)

        # Normalize keywords
        keywords = [normalize_item(k) for k in keywords]

        # Step 3: Generate hashtags using Gemini LLM
        hashtags_gemini = generate_hashtags((keywords, content))
        hashtags_gemini = [normalize_item(h) for h in hashtags_gemini]

        print('\n=== Pipeline inputs (pre-Apify) ===')
        print('Extracted keywords (normalized):')
        for i, k in enumerate(keywords, 1):
            print(f"  {i}. {k}")
        print('\nGemini-generated hashtags (normalized):')
        for i, h in enumerate(hashtags_gemini, 1):
            print(f"  {i}. {h}")

        # Step 4: Use Apify to get trending hashtags
        apify_key = os.getenv("APIFY_API_TOKEN")
        trending_hashtags = []
        if apify_key:
            # Combine, filter, and dedupe
            combined = [q for q in (keywords + hashtags_gemini) if isinstance(q, str) and q.strip()]
            seen = set()
            query_list = []
            for q in combined:
                nq = q.strip()
                if nq not in seen:
                    seen.add(nq)
                    query_list.append(nq)

            print('\nQueries to be sent to Apify (normalized + deduped):')
            for i, q in enumerate(query_list, 1):
                print(f"  {i}. {q}")

            trending_hashtags = get_trending_hashtags_for_list(query_list)
        else:
            print("[WARNING] APIFY_API_TOKEN not found. Skipping trending hashtags fetch.")

        # Step 5: Use Gemini to select top 20 hashtags
        if trending_hashtags:
            trending_hashtags = select_top_hashtags(trending_hashtags, keywords, content)
        else:
            print("[WARNING] No trending hashtags found from Apify.")

        # Step 6: Prepare final result
        result = {
            "url": url,
            "used_keywords": keywords,
            "apify_trending_hashtags": trending_hashtags,
            "timestamp": datetime.now().isoformat()
        }

        # Step 7: Save to logs
        log_filename = os.path.join(LOGS_DIR, f"hashtag_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(log_filename, 'w') as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        print(f"\n[INFO] Results saved to {log_filename}")

        return jsonify(result), 200

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Handle logout (redirect to login page)"""
    return jsonify({"message": "Logged out successfully"}), 200

@app.route('/history', methods=['GET'])
def history():
    """Get list of all previous runs"""
    try:
        logs = []
        if os.path.exists(LOGS_DIR):
            for filename in sorted(os.listdir(LOGS_DIR), reverse=True):
                if filename.endswith('.json'):
                    filepath = os.path.join(LOGS_DIR, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        logs.append({
                            "filename": filename,
                            "data": data
                        })
        return jsonify({"logs": logs}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs/<filename>', methods=['GET'])
def get_log(filename):
    """Get specific log file"""
    try:
        filepath = os.path.join(LOGS_DIR, filename)
        if not os.path.exists(filepath):
            return jsonify({"error": "Log not found"}), 404
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    print("[INFO] Starting Hashtag Generator Flask App...")
    app.run(debug=True, host='0.0.0.0', port=5000)