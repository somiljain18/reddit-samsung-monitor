"""Twitter API client for hashtag monitoring."""

import logging
import requests
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


logger = logging.getLogger(__name__)


class TwitterClient:
    """Twitter API v2 client for hashtag monitoring."""

    def __init__(self, bearer_token: str, user_agent: str = "XHashtagMonitor/1.0"):
        """Initialize X (formerly Twitter) API client."""
        self.bearer_token = bearer_token
        self.user_agent = user_agent
        self.base_url = "https://api.x.com/2"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {bearer_token}',
            'User-Agent': user_agent
        })

    def test_connection(self) -> bool:
        """Test X API connection and authentication."""
        try:
            # Use tweets/search/recent endpoint for testing as it supports Bearer token
            url = f"{self.base_url}/tweets/search/recent"
            params = {'query': 'test', 'max_results': 10}
            response = self.session.get(url, params=params)

            if response.status_code == 200:
                logger.info("✅ X API connection test successful")
                return True
            elif response.status_code == 401:
                logger.error("❌ X API authentication failed - check bearer token")
                logger.error(f"❌ Response: {response.text}")
                return False
            elif response.status_code == 403:
                logger.error("❌ X API access forbidden (403)")
                logger.error(f"❌ Response: {response.text}")
                logger.error("💡 Common causes:")
                logger.error("   - Invalid Bearer token format")
                logger.error("   - Token doesn't have required permissions")
                logger.error("   - Account suspended or restricted")
                logger.error("   - Using wrong API endpoint (try api.x.com instead of api.twitter.com)")
                return False
            else:
                logger.error(f"❌ X API connection test failed: {response.status_code}")
                logger.error(f"❌ Response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error testing X API connection: {e}")
            return False

    def search_hashtags(self, hashtags: List[str], max_results: int = 100,
                       since_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for tweets containing specific hashtags.

        Args:
            hashtags: List of hashtags to search for (without # symbol)
            max_results: Maximum number of tweets to return (10-100)
            since_id: Only return tweets newer than this tweet ID

        Returns:
            List of tweet data dictionaries
        """
        try:
            # Build search query - combine hashtags with OR
            query = " OR ".join([f"#{hashtag}" for hashtag in hashtags])

            # API parameters
            params = {
                'query': query,
                'max_results': min(max_results, 100),  # Twitter API limit
                'tweet.fields': 'id,text,author_id,created_at,public_metrics,context_annotations,lang,conversation_id,in_reply_to_user_id,referenced_tweets',
                'expansions': 'author_id',
                'user.fields': 'username,name,verified,public_metrics'
            }

            if since_id:
                params['since_id'] = since_id

            logger.debug(f"🔍 Searching Twitter for hashtags: {hashtags}")
            logger.debug(f"🔍 Query: {query}")

            url = f"{self.base_url}/tweets/search/recent"
            response = self.session.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                tweets = data.get('data', [])
                users = {user['id']: user for user in data.get('includes', {}).get('users', [])}

                # Process tweets and add user information
                processed_tweets = []
                for tweet in tweets:
                    user_info = users.get(tweet['author_id'], {})

                    processed_tweet = {
                        'tweet_id': tweet['id'],
                        'text': tweet['text'],
                        'author_id': tweet['author_id'],
                        'author_username': user_info.get('username', 'unknown'),
                        'author_name': user_info.get('name', 'Unknown User'),
                        'author_verified': user_info.get('verified', False),
                        'created_at': tweet['created_at'],
                        'lang': tweet.get('lang', 'und'),
                        'retweet_count': tweet.get('public_metrics', {}).get('retweet_count', 0),
                        'like_count': tweet.get('public_metrics', {}).get('like_count', 0),
                        'reply_count': tweet.get('public_metrics', {}).get('reply_count', 0),
                        'quote_count': tweet.get('public_metrics', {}).get('quote_count', 0),
                        'conversation_id': tweet.get('conversation_id', ''),
                        'in_reply_to_user_id': tweet.get('in_reply_to_user_id', ''),
                        'referenced_tweets': tweet.get('referenced_tweets', []),
                        'hashtags': self._extract_hashtags(tweet['text'])
                    }
                    processed_tweets.append(processed_tweet)

                logger.info(f"✅ Retrieved {len(processed_tweets)} tweets for hashtags: {hashtags}")
                return processed_tweets

            elif response.status_code == 429:
                logger.warning("⚠️ X API rate limit exceeded")
                # Extract rate limit info from headers if available
                reset_time = response.headers.get('x-rate-limit-reset', 'unknown')
                remaining = response.headers.get('x-rate-limit-remaining', 'unknown')

                if reset_time != 'unknown':
                    try:
                        import datetime
                        reset_readable = datetime.datetime.fromtimestamp(int(reset_time)).strftime('%H:%M:%S UTC')
                        logger.info(f"🕒 Rate limit resets at: {reset_readable}")
                    except:
                        pass

                logger.info(f"⏳ Remaining requests: {remaining}")
                logger.info("💡 Consider increasing TWITTER_POLL_INTERVAL to avoid rate limits")
                return []
            elif response.status_code == 401:
                logger.error("❌ Twitter API authentication failed")
                return []
            else:
                logger.error(f"❌ Twitter API search failed: {response.status_code} - {response.text}")
                return []

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error searching Twitter hashtags: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error searching Twitter hashtags: {e}")
            return []

    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from tweet text."""
        import re
        hashtag_pattern = r'#(\w+)'
        hashtags = re.findall(hashtag_pattern, text.lower())
        return hashtags

    def _convert_twitter_timestamp(self, twitter_timestamp: str) -> int:
        """Convert Twitter's ISO timestamp to Unix timestamp."""
        try:
            # Twitter returns timestamps like: 2023-01-01T12:00:00.000Z
            dt = datetime.fromisoformat(twitter_timestamp.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except (ValueError, AttributeError) as e:
            logger.error(f"❌ Failed to parse Twitter timestamp '{twitter_timestamp}': {e}")
            return int(time.time())  # Fallback to current time

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status for search endpoint."""
        try:
            url = f"{self.base_url}/tweets/search/recent"
            response = self.session.get(url, params={'query': 'test', 'max_results': 10})

            rate_limit_info = {
                'limit': response.headers.get('x-rate-limit-limit', 'unknown'),
                'remaining': response.headers.get('x-rate-limit-remaining', 'unknown'),
                'reset': response.headers.get('x-rate-limit-reset', 'unknown'),
                'status_code': response.status_code
            }

            # Convert reset timestamp to readable format
            if rate_limit_info['reset'] != 'unknown':
                try:
                    import datetime
                    reset_time = datetime.datetime.fromtimestamp(int(rate_limit_info['reset']))
                    rate_limit_info['reset_readable'] = reset_time.strftime('%Y-%m-%d %H:%M:%S UTC')
                except:
                    rate_limit_info['reset_readable'] = 'unknown'

            logger.info(f"🔍 X API Rate Limit Status:")
            logger.info(f"   📊 Limit: {rate_limit_info['limit']}")
            logger.info(f"   ⚡ Remaining: {rate_limit_info['remaining']}")
            logger.info(f"   🕒 Reset: {rate_limit_info.get('reset_readable', rate_limit_info['reset'])}")

            return rate_limit_info

        except Exception as e:
            logger.error(f"❌ Failed to get rate limit status: {e}")
            return {}