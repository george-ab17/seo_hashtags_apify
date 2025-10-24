# SEO Hashtag Generator with Trending Analysis

A powerful Python tool that generates trending and relevant hashtags for SEO optimization using AI and real-time search data.

## Features

- Extracts relevant keywords from the provided topic/content
- Generates SEO-optimized hashtags using Google's Gemini AI (now returns up to 13 hashtags)
- Verifies hashtag trending status using Apify's scrapers (Google Search, Twitter, Instagram)
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

You'll be prompted to enter a topic (not a URL) and optionally provide custom keywords.

The script will:
- Extract relevant keywords for the topic
- Generate up to 13 SEO-friendly hashtags using Gemini
- Verify trending status across supported platforms via Apify
- Save results to `output.json`

## Components

- `main.py`: Primary script orchestrating the workflow
-- `hashtag_generator.py`: Hashtag generation using Gemini AI
-- `apify_trending_for_hashtags.py`: Trending verification using Apify
- `keyword_extractor.py`: AI-powered keyword extraction
- `hashtag_generator.py`: Hashtag generation using Gemini AI
- `apify_trending_for_hashtags.py`: Trending verification using Apify

## Output

Results are saved in `output.json` with:
- Topic
- Extracted keywords
- Verified trending hashtags (up to 13)

## Error Handling

- Robust error handling for API failures and retry logic for Apify calls

Note: Reddit scraping was removed due to availability of the previous actor. Current Apify-supported scrapers used are Google Search, Twitter, and Instagram.

## License

MIT License