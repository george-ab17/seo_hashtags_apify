import requests
from bs4 import BeautifulSoup

def scrape_url(url):
    """
    Fetch and clean content from a URL.
    Returns clean text from headings, paragraphs, and meta tags.
    """
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        print(f"[DEBUG] HTTP status: {response.status_code}")
        if response.status_code != 200:
            print(f"[ERROR] Failed to fetch URL: {url} (HTTP {response.status_code})")
            return ""
        soup = BeautifulSoup(response.text, "html.parser")
        # Extract headings
        headings = " ".join([h.get_text(separator=" ", strip=True) for h in soup.find_all(['h1','h2','h3','h4','h5','h6'])])
        # Extract paragraphs
        paragraphs = " ".join([p.get_text(separator=" ", strip=True) for p in soup.find_all('p')])
        # Extract meta description
        meta = soup.find("meta", attrs={"name": "description"})
        meta_desc = meta["content"] if meta and "content" in meta.attrs else ""
        # Combine all content
        content = " ".join([headings, paragraphs, meta_desc])
        if not content.strip():
            print(f"[WARNING] No content extracted from: {url}")
        return content
    except Exception as e:
        print(f"[ERROR] Exception during scraping {url}: {e}")
        return ""


if __name__ == "__main__":
    url = input("Enter URL to scrape: ").strip()
    scraped_content = scrape_url(url)
    print("\n=== SCRAPED CONTENT ===\n")
    print(scraped_content)
