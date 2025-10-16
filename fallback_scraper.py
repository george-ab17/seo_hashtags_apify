"""fallback_scraper.py

Robust fallback scraper. Use this when the main `scraper.py` returns empty or HTTP 403/401.

Behavior:
- Try multiple common browser User-Agent headers via requests.Session
- If requests keep failing with 403/401, try the Jina text proxy (https://r.jina.ai/http://<url>)
- If still failing and selenium is available, attempt a headless browser render (requires chromedriver/geckodriver)
- Extracts readable text using BeautifulSoup, preferring <article>, long <div>, and <p> content

This file intentionally does not modify `scraper.py`.
"""

import time
import re
import urllib3
from typing import Optional

import requests
from bs4 import BeautifulSoup

urllib3.disable_warnings()

DEFAULT_HEADERS = [
    # Chrome on Windows
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    },
    # Mobile Chrome
    {
        "User-Agent": "Mozilla/5.0 (Linux; Android 12; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Mobile Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    },
    # Firefox
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:116.0) Gecko/20100101 Firefox/116.0",
        "Accept-Language": "en-US,en;q=0.9",
    },
]


def extract_text_from_html(html: str) -> str:
    """Extract readable textual content from HTML. Returns a cleaned string."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove scripts, styles, noscript
    for tag in soup(["script", "style", "noscript", "iframe", "header", "footer", "svg"]):
        tag.decompose()

    # Prefer <article>
    article = soup.find("article")
    if article:
        texts = [p.get_text(separator=" ", strip=True) for p in article.find_all(["p", "h1", "h2", "h3"]) if p.get_text(strip=True)]
        if texts:
            return "\n\n".join(texts)

    # Otherwise, find the largest div by text length
    candidates = soup.find_all(["div", "main", "section"])
    best = None
    best_len = 0
    for c in candidates:
        text = c.get_text(separator=" ", strip=True)
        ln = len(text)
        if ln > best_len:
            best_len = ln
            best = text

    if best and best_len > 200:
        return re.sub(r"\s+", " ", best).strip()

    # Fallback: join paragraphs
    paragraphs = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]
    if paragraphs:
        return "\n\n".join(paragraphs)

    # Last resort: meta description or title
    desc = None
    meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if meta and meta.get("content"):
        desc = meta.get("content").strip()
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    if desc:
        return desc
    if title:
        return title
    return ""


def scrape_url_fallback(url: str, max_attempts: int = 3, timeout: int = 15, use_selenium_if_needed: bool = True) -> str:
    """Try several strategies to fetch and return the page text for `url`.

    Returns cleaned text (possibly empty string if nothing could be extracted).
    """
    session = requests.Session()

    # Normalize URL
    url = url.strip()
    if not url.startswith("http"):
        url = "http://" + url

    # 1) Try rotating headers with requests
    for attempt in range(1, max_attempts + 1):
        headers = DEFAULT_HEADERS[(attempt - 1) % len(DEFAULT_HEADERS)]
        try:
            resp = session.get(url, headers=headers, timeout=timeout, allow_redirects=True, verify=False)
        except Exception as e:
            resp = None
            last_exc = e
        else:
            last_exc = None

        if resp is not None and resp.status_code == 200 and "text/html" in (resp.headers.get("Content-Type") or ""):
            text = extract_text_from_html(resp.text)
            if text and len(text) > 50:
                return text
        # If 403/401, try next header immediately
        time.sleep(1)

    # 2) Try Jina text proxy (works for many sites as a quick fallback)
    try:
        proxy_url = f"https://r.jina.ai/http://{url.lstrip('http://').lstrip('https://')}"
        resp = session.get(proxy_url, timeout=timeout, allow_redirects=True, verify=False)
        if resp.status_code == 200 and resp.text:
            # Jina returns plain text already
            if len(resp.text.strip()) > 50:
                return resp.text.strip()
    except Exception:
        pass

    # 3) Optional: try Selenium headless rendering if installed and enabled
    if use_selenium_if_needed:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            # Prevent some sites from blocking by adding UA
            options.add_argument(f"--user-agent={DEFAULT_HEADERS[0]['User-Agent']}")

            driver = webdriver.Chrome(options=options)
            try:
                driver.set_page_load_timeout(timeout)
                driver.get(url)
                time.sleep(2)
                html = driver.page_source
                text = extract_text_from_html(html)
                if text and len(text) > 50:
                    return text
            finally:
                try:
                    driver.quit()
                except Exception:
                    pass
        except Exception as e:
            # Selenium not installed or driver not present; just ignore
            pass

    # If all else fails, return empty string
    return ""


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fallback scraper: extract readable text from a URL")
    parser.add_argument("url", nargs="?", help="URL to scrape")
    parser.add_argument("--no-selenium", action="store_true", help="Don't try Selenium fallback")
    args = parser.parse_args()

    if not args.url:
        args.url = input("Enter URL to scrape: ").strip()

    text = scrape_url_fallback(args.url, use_selenium_if_needed=not args.no_selenium)
    if text:
        print("\n=== SCRAPED CONTENT ===\n")
        print(text)
    else:
        print("\nFailed to extract content. Consider enabling Selenium fallback or check site blocking (HTTP 403).")
