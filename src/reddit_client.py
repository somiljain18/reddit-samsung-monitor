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

    def fetch_new_posts(self, subreddit: str = "technology", limit: int = 25, after: Optional[int] = None) -> List[Dict[str, Any]]:
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

        print(f"Fetching new posts from r/{subreddit} with limit {limit} and after {after}")
        posts = []

        # Enhanced debug logging
        from datetime import datetime
        after_readable = datetime.fromtimestamp(after).strftime('%Y-%m-%d %H:%M:%S UTC') if after else "None"
        logger.info(f"🔍 DEBUG: Starting fetch from r/{subreddit}")
        logger.info(f"🔍 DEBUG: Request params - limit: {limit}, after timestamp: {after} ({after_readable})")
        logger.info(f"🔍 DEBUG: Request URL: {url}")

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            logger.debug(f"🔍 DEBUG: HTTP Status: {response.status_code}")
            logger.debug(f"🔍 DEBUG: Response headers: {dict(response.headers)}")

            data = response.json()

            if 'data' not in data or 'children' not in data['data']:
                logger.warning(f"❌ DEBUG: Unexpected response structure from Reddit API")
                logger.debug(f"🔍 DEBUG: Response structure: {list(data.keys()) if data else 'None'}")
                return posts

            total_posts_fetched = len(data['data']['children'])
            logger.info(f"🔍 DEBUG: Reddit returned {total_posts_fetched} total posts")

            filtered_count = 0
            for i, post in enumerate(data['data']['children']):
                if post['kind'] == 't3':  # 't3' indicates a link/post
                    post_data = self._extract_post_data(post['data'])
                    post_time_readable = datetime.fromtimestamp(post_data['created_utc']).strftime('%Y-%m-%d %H:%M:%S UTC')

                    logger.debug(f"🔍 DEBUG: Post {i+1}: ID={post_data['post_id']}, "
                               f"created_utc={post_data['created_utc']} ({post_time_readable}), "
                               f"title='{post_data['title'][:50]}...'")

                    # Filter posts newer than the 'after' timestamp if provided
                    if after is None or post_data['created_utc'] > after:
                        posts.append(post_data)
                        logger.debug(f"✅ DEBUG: Post {post_data['post_id']} included (newer than filter)")
                    else:
                        filtered_count += 1
                        logger.debug(f"❌ DEBUG: Post {post_data['post_id']} filtered out (older than {after})")

            logger.info(f"🔍 DEBUG: Total posts after filtering: {len(posts)}, filtered out: {filtered_count}")
            logger.info(f"✅ Fetched {len(posts)} new posts from r/{subreddit} (out of {total_posts_fetched} total)")

            # Respect rate limits
            time.sleep(self.rate_limit_delay)

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error fetching from Reddit: {e}")
        except ValueError as e:
            logger.error(f"❌ JSON parsing error: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error while fetching posts: {e}")
            import traceback
            logger.debug(f"🔍 DEBUG: Full traceback: {traceback.format_exc()}")

        return posts

    def fetch_posts_from_multiple_subreddits(self, subreddits: List[str], limit_per_subreddit: int = 25, after_timestamps: Optional[Dict[str, int]] = None) -> List[Dict[str, Any]]:
        """
        Fetch new posts from multiple subreddits.

        Args:
            subreddits: List of subreddit names to fetch from
            limit_per_subreddit: Maximum number of posts to fetch per subreddit
            after_timestamps: Dict mapping subreddit names to timestamp filters

        Returns:
            List of post dictionaries from all subreddits combined
        """
        all_posts = []
        after_timestamps = after_timestamps or {}

        logger.info(f"🔄 DEBUG: Starting multi-subreddit fetch from {len(subreddits)} subreddits: {', '.join(subreddits)}")

        for subreddit in subreddits:
            after_time = after_timestamps.get(subreddit, None)
            logger.info(f"📂 DEBUG: Fetching from r/{subreddit} (after: {after_time})")

            try:
                posts = self.fetch_new_posts(
                    subreddit=subreddit,
                    limit=limit_per_subreddit,
                    after=after_time
                )

                logger.info(f"✅ DEBUG: Got {len(posts)} posts from r/{subreddit}")
                all_posts.extend(posts)

            except Exception as e:
                logger.error(f"❌ DEBUG: Failed to fetch from r/{subreddit}: {e}")

        # Sort by created_utc timestamp (newest first)
        all_posts.sort(key=lambda x: x.get('created_utc', 0), reverse=True)

        logger.info(f"🎯 DEBUG: Total posts from all subreddits: {len(all_posts)}")
        return all_posts

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