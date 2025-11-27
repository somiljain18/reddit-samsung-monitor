#!/usr/bin/env python3
"""Simple test script to verify Reddit API connectivity."""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.reddit_client import RedditClient
from src.config import setup_logging

def test_reddit_api():
    """Test Reddit API connection and data fetching."""
    setup_logging("INFO")

    print("Testing Reddit API connection...")

    # Initialize Reddit client
    client = RedditClient()

    # Test connection
    if not client.test_connection():
        print("✗ Failed to connect to Reddit API")
        return False

    print("✓ Successfully connected to Reddit API")

    # Get subreddit info
    subreddit_info = client.get_subreddit_info("samsung")
    if subreddit_info:
        print(f"✓ r/samsung info: {subreddit_info['subscribers']} subscribers")
        print(f"  Title: {subreddit_info['title']}")
    else:
        print("✗ Failed to get subreddit info")
        return False

    # Fetch some posts
    print("Fetching recent posts...")
    posts = client.fetch_new_posts("samsung", limit=5)

    if posts:
        print(f"✓ Fetched {len(posts)} posts from r/samsung")
        for i, post in enumerate(posts[:3], 1):
            print(f"  {i}. {post['title'][:80]}...")
            print(f"     Author: {post['author']}, Score: {post['score']}")
    else:
        print("✗ Failed to fetch posts")
        return False

    print("\n✓ All Reddit API tests passed!")
    return True

if __name__ == "__main__":
    success = test_reddit_api()
    sys.exit(0 if success else 1)