import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env file and configure Gemini API
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def generate_hashtags(keywords):
    """Generate 5 professional, SEO-friendly hashtags using Gemini API.
    
    Args:
        keywords: List of keywords or tuple of (keywords, content)
    
    Returns:
        List of 13 most relevant hashtags
    """
    # Accept both keywords and content
    if isinstance(keywords, tuple) and len(keywords) == 2:
        keywords, content = keywords
    else:
        content = ""
    # Stronger, constrained prompt that instructs the model to stay grounded in the provided
    # keywords/content. We ask for comma-separated hashtags and emphasize not inventing
    # unrelated or generic tags. We also request the model return only the hashtags.
    prompt = f"""
You are an expert SEO auditor and social media strategist. Your only job is to produce
hashtags that are directly derived from the provided Keywords and Page Content. DO NOT
invent unrelated industry terms or generic marketing buzzwords that are not grounded in the
input. Use exact keyword words or short, safe variants of those words (e.g., remove spaces,
use CamelCase) and prefer tokens that appear in the Page Content.

Requirements:
- Return exactly 5 most relevant hashtags, separated by commas.
- Ensure hashtags are highly specific to the topic and keywords.
- Use professional, enterprise-friendly terms.
- Do not include slang, emojis, or unrelated trending topics.

Keywords:
{', '.join(keywords)}

Page Content:
{content}

Output:
"""
    def _clean_hashtag(raw):
        s = raw.strip()
        if not s:
            return None
        # remove surrounding quotes
        s = s.strip("'\"")
        # ensure leading '#'
        if not s.startswith('#'):
            s = '#' + s
        # remove spaces and illegal chars, keep letters/numbers
        import re
        body = re.sub(r'[^0-9A-Za-z]', '', s.lstrip('#'))
        if not body:
            return None
        # CamelCase the hashtag for readability
        body = ''.join(part.capitalize() for part in re.split(r'\s+|[-_]', body))
        return '#' + body

    def _keywords_tokens(keywords_list):
        toks = set()
        import re
        for k in keywords_list:
            if not isinstance(k, str):
                continue
            for w in re.findall(r"[A-Za-z0-9]{3,}", k):
                toks.add(w.lower())
        return toks

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt, generation_config={"temperature": 0})
        raw_tags = [t for t in response.text.split(',')]
        cleaned = []
        for rt in raw_tags:
            h = _clean_hashtag(rt)
            if h and h not in cleaned:
                cleaned.append(h)

        # Validate grounding: at least some hashtags should contain tokens from keywords
        kw_tokens = _keywords_tokens(keywords)
        def _matches_keywords(hashtag):
            low = hashtag.lstrip('#').lower()
            for t in kw_tokens:
                if t in low:
                    return True
            return False

        matched = sum(1 for h in cleaned if _matches_keywords(h))
        # If too few matches, fallback to deterministic generation from keywords
        min_needed = max(3, int(len(cleaned) * 0.3))
        if matched < min_needed:
            # Deterministic fallback: derive hashtags from keywords
            derived = []
            import re
            for k in keywords:
                if not isinstance(k, str):
                    continue
                parts = re.findall(r"[A-Za-z0-9]+", k)
                if not parts:
                    continue
                body = ''.join(p.capitalize() for p in parts)
                tag = '#' + body
                if tag not in derived:
                    derived.append(tag)
                # add a safe variant if space allows
                if len(derived) < 20:
                    variant = '#' + body + 'Tips'
                    if variant not in derived:
                        derived.append(variant)
                if len(derived) >= 5:
                    break
            return derived[:5]

        return cleaned[:5]
    except Exception as e:
        print(f"Gemini hashtag generation error: {e}")
        # deterministic fallback on error
        derived = []
        import re
        for k in keywords:
            if not isinstance(k, str):
                continue
            parts = re.findall(r"[A-Za-z0-9]+", k)
            if not parts:
                continue
            body = ''.join(p.capitalize() for p in parts)
            tag = '#' + body
            if tag not in derived:
                derived.append(tag)
            if len(derived) >= 13:
                break
        return derived[:13]
