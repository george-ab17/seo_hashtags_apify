# SEO Hashtag Generator with Trending Analysis

A powerful Python tool that generates trending and relevant hashtags for SEO optimization using AI and real-time search data.

## Features

- Extracts relevant keywords from webpage content
- Generates SEO-optimized hashtags using Google's Gemini AI
- Verifies hashtag trending status using Apify's Google Search Scraper
- Multiple fallback scraping mechanisms for reliable content extraction
- Smart content filtering and relevance checking
- Enterprise-grade output suitable for professional use

## Requirements

- Python 3.7+
- Google Gemini API key
- Apify API token

## Installation

1. Clone the repository
2. Install required packages:
```bash
pip install -r requirements.txt
```
3. Create a `.env` file with your API keys:
```
GEMINI_API_KEY="your_gemini_api_key"
APIFY_API_TOKEN="your_apify_token"
```

## Usage

Run the main script:
```bash
python main.py
```

You'll be prompted to:
1. Enter a URL to analyze
2. Optionally provide custom keywords

The script will:
- Scrape the webpage content
- Extract relevant keywords
- Generate and verify trending hashtags
- Save results to `output.json`

## Components

- `main.py`: Primary script orchestrating the workflow
- `scraper.py`: Main web content scraper
- `fallback_scraper.py`: Robust fallback scraping mechanisms
- `keyword_extractor.py`: AI-powered keyword extraction
- `hashtag_generator.py`: Hashtag generation using Gemini AI
- `apify_trending_for_hashtags.py`: Trending verification using Apify

## Output

Results are saved in `output.json` with:
- Original URL
- Extracted keywords
- Verified trending hashtags

## Error Handling

- Multiple fallback mechanisms for content scraping
- Robust error handling for API failures
- Automatic retries for failed requests

## License

MIT License