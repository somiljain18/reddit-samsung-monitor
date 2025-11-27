"""Reddit API client for fetching posts."""

import requests
import logging
import time
from typing import List, Dict, Any, Optional
import os


logger = logging.getLogger(__name__)


class RedditClient:
    """Reddit API client for fetching posts from subreddits."""

    def __init__(self, user_agent: Optional[str] = None):
        """Initialize Reddit client."""
        self.user_agent = user_agent or os.getenv('USER_AGENT', 'RedditSamsungMonitor/1.0')
        self.base_url = "https://www.reddit.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent
        })
        self.rate_limit_delay = 2  # Minimum delay between requests in seconds

    def fetch_new_posts(self, subreddit: str = "samsung", limit: int = 25, after: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch new posts from a subreddit.

        Args:
            subreddit: The subreddit to fetch from (default: samsung)
            limit: Maximum number of posts to fetch (default: 25)
            after: Unix timestamp to fetch posts after (for pagination)

        Returns:
            List of post dictionaries
        """
        url = f"{self.base_url}/r/{subreddit}/new.json"
        params = {
            'limit': min(limit, 100),  # Reddit API max is 100
            'raw_json': 1  # Prevent HTML encoding
        }

        posts = []

        try:
            logger.debug(f"Fetching posts from r/{subreddit} with limit {limit}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            if 'data' not in data or 'children' not in data['data']:
                logger.warning(f"Unexpected response structure from Reddit API")
                return posts

            for post in data['data']['children']:
                if post['kind'] == 't3':  # 't3' indicates a link/post
                    post_data = self._extract_post_data(post['data'])

                    # Filter posts newer than the 'after' timestamp if provided
                    if after is None or post_data['created_utc'] > after:
                        posts.append(post_data)

            logger.info(f"Fetched {len(posts)} posts from r/{subreddit}")

            # Respect rate limits
            time.sleep(self.rate_limit_delay)

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch posts from Reddit: {e}")
        except ValueError as e:
            logger.error(f"Failed to parse JSON response: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while fetching posts: {e}")

        return posts

    def _extract_post_data(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant data from a Reddit post.

        Args:
            post: Raw post data from Reddit API

        Returns:
            Cleaned post data dictionary
        """
        return {
            'post_id': post.get('id', ''),
            'title': post.get('title', ''),
            'author': post.get('author', '[deleted]'),
            'created_utc': int(post.get('created_utc', 0)),
            'score': post.get('score', 0),
            'num_comments': post.get('num_comments', 0),
            'url': post.get('url', ''),
            'selftext': post.get('selftext', ''),
            'permalink': f"https://reddit.com{post.get('permalink', '')}" if post.get('permalink') else '',
            'subreddit': post.get('subreddit', 'samsung')
        }

    def test_connection(self) -> bool:
        """
        Test the connection to Reddit API.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            response = self.session.get(f"{self.base_url}/r/samsung/new.json?limit=1", timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'data' in data and 'children' in data['data']:
                logger.info("Successfully connected to Reddit API")
                return True
            else:
                logger.error("Unexpected response structure from Reddit API")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to Reddit API: {e}")
            return False

    def get_subreddit_info(self, subreddit: str = "samsung") -> Optional[Dict[str, Any]]:
        """
        Get information about a subreddit.

        Args:
            subreddit: The subreddit name

        Returns:
            Subreddit information or None if failed
        """
        try:
            url = f"{self.base_url}/r/{subreddit}/about.json"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            if 'data' in data:
                return {
                    'display_name': data['data'].get('display_name', subreddit),
                    'subscribers': data['data'].get('subscribers', 0),
                    'title': data['data'].get('title', ''),
                    'public_description': data['data'].get('public_description', ''),
                    'active_user_count': data['data'].get('active_user_count', 0)
                }
        except Exception as e:
            logger.error(f"Failed to get subreddit info for r/{subreddit}: {e}")

        return None