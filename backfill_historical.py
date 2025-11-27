#!/usr/bin/env python3
"""
Historical Backfill Script for Reddit Posts

This script attempts to fill gaps in historical Reddit data by using
multiple Reddit API endpoints and sorting methods to get older posts.
"""

import os
import sys
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
import psycopg2

# Add src directory to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.database import Database
from src.reddit_client import RedditClient
from src.models import RedditPost
from src.config import load_environment, get_config_from_env


class HistoricalBackfillClient:
    """Extended Reddit client for historical data collection."""

    def __init__(self, user_agent: str = None):
        self.user_agent = user_agent or 'RedditHistoricalBackfill/1.0'
        self.base_url = "https://www.reddit.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent
        })
        self.rate_limit_delay = 2

    def fetch_top_posts(self, subreddit: str, time_filter: str = "all", limit: int = 100, after: str = None) -> List[Dict[str, Any]]:
        """
        Fetch top posts from a subreddit with time filtering.

        Args:
            subreddit: Subreddit name
            time_filter: Time filter (hour, day, week, month, year, all)
            limit: Number of posts to fetch (max 100)
            after: Pagination token

        Returns:
            List of post dictionaries
        """
        url = f"{self.base_url}/r/{subreddit}/top.json"
        params = {
            't': time_filter,
            'limit': min(limit, 100),
            'raw_json': 1
        }

        if after:
            params['after'] = after

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            posts = []

            if 'data' in data and 'children' in data['data']:
                for post in data['data']['children']:
                    if post['kind'] == 't3':
                        post_data = self._extract_post_data(post['data'])
                        posts.append(post_data)

                # Return pagination info
                after_token = data['data'].get('after')
                return posts, after_token

            time.sleep(self.rate_limit_delay)

        except Exception as e:
            logging.error(f"Error fetching top posts from r/{subreddit}: {e}")

        return [], None

    def fetch_hot_posts(self, subreddit: str, limit: int = 100, after: str = None) -> List[Dict[str, Any]]:
        """Fetch hot posts from a subreddit."""
        url = f"{self.base_url}/r/{subreddit}/hot.json"
        params = {
            'limit': min(limit, 100),
            'raw_json': 1
        }

        if after:
            params['after'] = after

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            posts = []

            if 'data' in data and 'children' in data['data']:
                for post in data['data']['children']:
                    if post['kind'] == 't3':
                        post_data = self._extract_post_data(post['data'])
                        posts.append(post_data)

                after_token = data['data'].get('after')
                return posts, after_token

            time.sleep(self.rate_limit_delay)

        except Exception as e:
            logging.error(f"Error fetching hot posts from r/{subreddit}: {e}")

        return [], None

    def _extract_post_data(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data from a Reddit post."""
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
            'subreddit': post.get('subreddit', '')
        }


class HistoricalBackfill:
    """Main class for historical data backfill operations."""

    def __init__(self):
        self.database = None
        self.client = None
        self.existing_post_ids: Set[str] = set()

    def initialize(self):
        """Initialize database and client connections."""
        try:
            # Load environment and config
            load_environment()
            config = get_config_from_env()

            # Setup logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler(),
                    logging.FileHandler('logs/backfill.log')
                ]
            )

            # Initialize database
            self.database = Database(
                host=config.db_host,
                user=config.db_user,
                password=config.db_password,
                database=config.db_name,
                port=config.db_port
            )

            if not self.database.connect():
                raise Exception("Failed to connect to database")

            # Initialize Reddit client
            self.client = HistoricalBackfillClient(config.user_agent)

            # Load existing post IDs to avoid duplicates
            self.load_existing_post_ids()

            logging.info("Historical backfill initialized successfully")
            return True

        except Exception as e:
            logging.error(f"Failed to initialize: {e}")
            return False

    def load_existing_post_ids(self):
        """Load existing post IDs from database to avoid duplicates."""
        try:
            query = "SELECT post_id FROM samsung_posts"
            cursor = self.database.connection.cursor()
            cursor.execute(query)

            self.existing_post_ids = {row[0] for row in cursor.fetchall()}
            logging.info(f"Loaded {len(self.existing_post_ids)} existing post IDs")

        except Exception as e:
            logging.error(f"Error loading existing post IDs: {e}")
            self.existing_post_ids = set()

    def backfill_subreddit_comprehensive(self, subreddit: str, max_posts_per_method: int = 1000):
        """
        Comprehensive backfill for a subreddit using multiple methods.

        Args:
            subreddit: Subreddit name to backfill
            max_posts_per_method: Maximum posts to fetch per method
        """
        logging.info(f"🚀 Starting comprehensive backfill for r/{subreddit}")
        print(f"🚀 Starting comprehensive backfill for r/{subreddit}")

        total_new_posts = 0

        # Method 1: Top posts of all time
        logging.info("📈 Fetching top posts of all time...")
        print("📈 Fetching top posts of all time...")
        new_posts = self.fetch_with_pagination(
            subreddit,
            "top_all",
            max_posts_per_method
        )
        total_new_posts += new_posts

        # Method 2: Top posts by time periods
        time_periods = ["year", "month", "week"]
        for period in time_periods:
            logging.info(f"📈 Fetching top posts from past {period}...")
            print(f"📈 Fetching top posts from past {period}...")
            new_posts = self.fetch_with_pagination(
                subreddit,
                f"top_{period}",
                max_posts_per_method // 3
            )
            total_new_posts += new_posts

        # Method 3: Hot posts (current trending)
        logging.info("🔥 Fetching hot posts...")
        print("🔥 Fetching hot posts...")
        new_posts = self.fetch_with_pagination(
            subreddit,
            "hot",
            max_posts_per_method // 2
        )
        total_new_posts += new_posts

        logging.info(f"✅ Backfill complete for r/{subreddit}! Added {total_new_posts} new posts")
        print(f"✅ Backfill complete for r/{subreddit}! Added {total_new_posts} new posts")

        return total_new_posts

    def fetch_with_pagination(self, subreddit: str, method: str, max_posts: int) -> int:
        """
        Fetch posts with pagination support.

        Args:
            subreddit: Subreddit name
            method: Fetch method (top_all, top_year, etc., hot)
            max_posts: Maximum posts to fetch

        Returns:
            Number of new posts added
        """
        new_posts_count = 0
        after_token = None
        fetched_count = 0

        while fetched_count < max_posts:
            # Determine fetch method
            if method.startswith("top_"):
                time_filter = method.split("_")[1]
                posts, after_token = self.client.fetch_top_posts(
                    subreddit,
                    time_filter=time_filter,
                    limit=min(100, max_posts - fetched_count),
                    after=after_token
                )
            elif method == "hot":
                posts, after_token = self.client.fetch_hot_posts(
                    subreddit,
                    limit=min(100, max_posts - fetched_count),
                    after=after_token
                )
            else:
                logging.error(f"Unknown method: {method}")
                break

            if not posts:
                logging.info(f"No more posts available for {method}")
                break

            # Process posts
            batch_new_posts = 0
            for post_data in posts:
                post_id = post_data.get('post_id', '')

                # Skip if we already have this post
                if post_id in self.existing_post_ids:
                    continue

                # Convert to RedditPost model and store
                try:
                    reddit_post = RedditPost.from_reddit_data(post_data)

                    if self.database.insert_post(reddit_post.to_dict()):
                        batch_new_posts += 1
                        new_posts_count += 1
                        self.existing_post_ids.add(post_id)

                        # Log every 10th post
                        if new_posts_count % 10 == 0:
                            post_time = datetime.fromtimestamp(reddit_post.created_utc).strftime('%Y-%m-%d %H:%M:%S')
                            logging.info(f"  ✅ {new_posts_count} posts added | Latest: {post_time} | {reddit_post.title[:50]}...")

                except Exception as e:
                    logging.error(f"Error processing post {post_id}: {e}")

            fetched_count += len(posts)

            # Log progress
            logging.info(f"  📊 {method}: Fetched {len(posts)} posts, {batch_new_posts} new, {fetched_count}/{max_posts} total")
            print(f"  📊 {method}: Fetched {len(posts)} posts, {batch_new_posts} new, {fetched_count}/{max_posts} total")

            # Check if we should continue
            if not after_token or len(posts) == 0:
                logging.info(f"  🏁 {method}: No more posts available (after_token: {after_token})")
                break

            # Rate limiting
            time.sleep(self.client.rate_limit_delay)

        return new_posts_count

    def get_current_stats(self, subreddit: str = None):
        """Get current database statistics."""
        try:
            if subreddit:
                query = """
                SELECT
                    subreddit,
                    MIN(to_timestamp(created_utc)) AS earliest_post,
                    MAX(to_timestamp(created_utc)) AS latest_post,
                    COUNT(*) AS total_posts
                FROM samsung_posts
                WHERE subreddit = %s
                GROUP BY subreddit
                """
                cursor = self.database.connection.cursor()
                cursor.execute(query, (subreddit,))
            else:
                query = """
                SELECT
                    subreddit,
                    MIN(to_timestamp(created_utc)) AS earliest_post,
                    MAX(to_timestamp(created_utc)) AS latest_post,
                    COUNT(*) AS total_posts
                FROM samsung_posts
                GROUP BY subreddit
                ORDER BY subreddit
                """
                cursor = self.database.connection.cursor()
                cursor.execute(query)

            results = cursor.fetchall()

            print("\n📊 Current Database Stats:")
            print("-" * 80)
            for row in results:
                subreddit_name, earliest, latest, count = row
                print(f"r/{subreddit_name:12} | {count:6} posts | {earliest} → {latest}")
            print("-" * 80)

            return results

        except Exception as e:
            logging.error(f"Error getting stats: {e}")
            return []

    def shutdown(self):
        """Clean up connections."""
        if self.database:
            self.database.disconnect()
        logging.info("Backfill shutdown complete")


def main():
    """Main entry point for historical backfill."""
    if len(sys.argv) < 2:
        print("Usage: python backfill_historical.py <subreddit> [max_posts_per_method]")
        print("Example: python backfill_historical.py samsung 1000")
        sys.exit(1)

    subreddit = sys.argv[1]
    max_posts_per_method = int(sys.argv[2]) if len(sys.argv) > 2 else 1000

    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    backfill = HistoricalBackfill()

    try:
        if not backfill.initialize():
            print("❌ Failed to initialize backfill system")
            sys.exit(1)

        # Show current stats
        print("📊 Stats before backfill:")
        backfill.get_current_stats()

        # Run backfill
        start_time = datetime.now()
        total_new_posts = backfill.backfill_subreddit_comprehensive(subreddit, max_posts_per_method)
        end_time = datetime.now()

        # Show final stats
        print(f"\n📊 Stats after backfill:")
        backfill.get_current_stats()

        duration = (end_time - start_time).total_seconds()
        print(f"\n🎉 Backfill Summary:")
        print(f"   📈 Total new posts added: {total_new_posts}")
        print(f"   ⏱️  Total time: {duration:.1f} seconds")
        print(f"   🚀 Average rate: {total_new_posts / duration if duration > 0 else 0:.2f} posts/second")

    except KeyboardInterrupt:
        print("\n🛑 Backfill interrupted by user")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")
    finally:
        backfill.shutdown()


if __name__ == "__main__":
    main()