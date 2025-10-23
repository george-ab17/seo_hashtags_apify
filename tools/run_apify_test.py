import sys
from pathlib import Path

# Ensure project root is on sys.path so local modules can be imported
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apify_trending_for_hashtags import get_trending_hashtags_for_list


if __name__ == '__main__':
    queries = [
        'Artificial Intelligence',
        'SEO',
        'Digital Marketing'
    ]
    print('Running test queries:', queries)
    try:
        tags = get_trending_hashtags_for_list(queries)
        print('Returned hashtags:', tags)
    except Exception as e:
        print('Error while running Apify test:', e)
