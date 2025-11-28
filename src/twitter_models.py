"""Data models for Twitter tweets and monitoring."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class TwitterTweet(BaseModel):
    """Twitter tweet data model."""

    tweet_id: str = Field(..., description="Unique Twitter tweet ID")
    text: str = Field(..., description="Tweet text content")
    author_id: str = Field(..., description="Twitter user ID of the author")
    author_username: str = Field(default="unknown", description="Twitter username")
    author_name: str = Field(default="Unknown User", description="Display name of the author")
    author_verified: bool = Field(default=False, description="Whether author is verified")
    created_at: str = Field(..., description="ISO timestamp when tweet was created")
    created_utc: int = Field(default=0, description="Unix timestamp when tweet was created")
    lang: str = Field(default="und", description="Tweet language code")
    retweet_count: int = Field(default=0, description="Number of retweets")
    like_count: int = Field(default=0, description="Number of likes")
    reply_count: int = Field(default=0, description="Number of replies")
    quote_count: int = Field(default=0, description="Number of quote tweets")
    conversation_id: str = Field(default="", description="ID of the conversation thread")
    in_reply_to_user_id: str = Field(default="", description="User ID this tweet is replying to")
    hashtags: List[str] = Field(default=[], description="Extracted hashtags from tweet")
    referenced_tweets: List[Dict[str, Any]] = Field(default=[], description="Referenced tweets (retweets, quotes, etc.)")

    def to_dict(self) -> dict:
        """Convert model to dictionary for database insertion."""
        return {
            'tweet_id': self.tweet_id,
            'text': self.text,
            'author_id': self.author_id,
            'author_username': self.author_username,
            'author_name': self.author_name,
            'author_verified': self.author_verified,
            'created_at': self.created_at,
            'created_utc': self.created_utc,
            'lang': self.lang,
            'retweet_count': self.retweet_count,
            'like_count': self.like_count,
            'reply_count': self.reply_count,
            'quote_count': self.quote_count,
            'conversation_id': self.conversation_id,
            'in_reply_to_user_id': self.in_reply_to_user_id,
            'hashtags': ','.join(self.hashtags),  # Store as comma-separated string
            'referenced_tweets': str(self.referenced_tweets) if self.referenced_tweets else ''
        }

    @classmethod
    def from_twitter_data(cls, data: dict) -> 'TwitterTweet':
        """Create TwitterTweet from processed Twitter API data."""
        # Convert Twitter timestamp to Unix timestamp
        created_utc = cls._convert_twitter_timestamp(data.get('created_at', ''))

        return cls(
            tweet_id=data.get('tweet_id', ''),
            text=data.get('text', ''),
            author_id=data.get('author_id', ''),
            author_username=data.get('author_username', 'unknown'),
            author_name=data.get('author_name', 'Unknown User'),
            author_verified=data.get('author_verified', False),
            created_at=data.get('created_at', ''),
            created_utc=created_utc,
            lang=data.get('lang', 'und'),
            retweet_count=data.get('retweet_count', 0),
            like_count=data.get('like_count', 0),
            reply_count=data.get('reply_count', 0),
            quote_count=data.get('quote_count', 0),
            conversation_id=data.get('conversation_id', ''),
            in_reply_to_user_id=data.get('in_reply_to_user_id', ''),
            hashtags=data.get('hashtags', []),
            referenced_tweets=data.get('referenced_tweets', [])
        )

    @staticmethod
    def _convert_twitter_timestamp(twitter_timestamp: str) -> int:
        """Convert Twitter's ISO timestamp to Unix timestamp."""
        try:
            # Twitter returns timestamps like: 2023-01-01T12:00:00.000Z
            dt = datetime.fromisoformat(twitter_timestamp.replace('Z', '+00:00'))
            return int(dt.timestamp())
        except (ValueError, AttributeError):
            return int(datetime.now().timestamp())  # Fallback to current time

    def __str__(self) -> str:
        return f"TwitterTweet(id={self.tweet_id}, text='{self.text[:50]}...', author=@{self.author_username})"

    def __repr__(self) -> str:
        return self.__str__()


class TwitterMonitorStats(BaseModel):
    """Statistics for the Twitter monitoring session."""

    total_tweets_fetched: int = Field(default=0, description="Total tweets fetched in session")
    new_tweets_saved: int = Field(default=0, description="New tweets saved to database")
    errors_count: int = Field(default=0, description="Number of errors encountered")
    start_time: datetime = Field(default_factory=datetime.now, description="Session start time")
    last_fetch_time: Optional[datetime] = Field(default=None, description="Last successful fetch time")
    last_tweet_id: Optional[str] = Field(default=None, description="ID of most recent tweet")
    hashtags_monitored: List[str] = Field(default=[], description="List of hashtags being monitored")
    rate_limit_hits: int = Field(default=0, description="Number of times rate limit was hit")

    def add_fetch_result(self, tweets_fetched: int, new_tweets: int):
        """Update stats after a fetch operation."""
        self.total_tweets_fetched += tweets_fetched
        self.new_tweets_saved += new_tweets
        self.last_fetch_time = datetime.now()

    def add_error(self):
        """Increment error count."""
        self.errors_count += 1

    def add_rate_limit_hit(self):
        """Increment rate limit hit count."""
        self.rate_limit_hits += 1

    def get_runtime_seconds(self) -> int:
        """Get total runtime in seconds."""
        return int((datetime.now() - self.start_time).total_seconds())

    def get_tweets_per_minute(self) -> float:
        """Calculate tweets per minute rate."""
        runtime_minutes = self.get_runtime_seconds() / 60
        if runtime_minutes > 0:
            return self.total_tweets_fetched / runtime_minutes
        return 0.0

    def __str__(self) -> str:
        runtime = self.get_runtime_seconds()
        tpm = self.get_tweets_per_minute()
        return (f"TwitterMonitorStats(runtime={runtime}s, fetched={self.total_tweets_fetched}, "
                f"saved={self.new_tweets_saved}, errors={self.errors_count}, "
                f"rate_limit_hits={self.rate_limit_hits}, tpm={tpm:.1f})")


class TwitterConfig(BaseModel):
    """Twitter monitoring configuration model."""

    # Twitter API configuration
    bearer_token: str = Field(..., description="Twitter API Bearer token")
    user_agent: str = Field(default="XHashtagMonitor/1.0", description="User agent for requests")

    # Database configuration
    db_host: str = Field(default="localhost", description="Database host")
    db_user: str = Field(default="adgear", description="Database user")
    db_password: str = Field(default="", description="Database password")
    db_name: str = Field(default="metadataservice", description="Database name")
    db_port: int = Field(default=6432, description="Database port")

    # Monitoring configuration
    hashtags: List[str] = Field(default=["samsung", "technology"], description="List of hashtags to monitor")
    poll_interval: int = Field(default=120, description="Polling interval in seconds (min 120s for rate limits)")
    max_results: int = Field(default=100, description="Maximum tweets to fetch per request (10-100)")

    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")

    @classmethod
    def from_env(cls) -> 'TwitterConfig':
        """Create config from environment variables."""
        import os

        # Parse hashtags from environment variable (comma-separated)
        hashtags_env = os.getenv('TWITTER_HASHTAGS', 'samsung,technology')
        hashtags = [tag.strip().lstrip('#') for tag in hashtags_env.split(',') if tag.strip()]

        bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        if not bearer_token:
            raise ValueError("TWITTER_BEARER_TOKEN environment variable is required")

        return cls(
            bearer_token=bearer_token,
            user_agent=os.getenv('TWITTER_USER_AGENT', 'XHashtagMonitor/1.0'),

            db_host=os.getenv('DB_HOST', 'localhost'),
            db_user=os.getenv('DB_USER', 'adgear'),
            db_password=os.getenv('DB_PASSWORD', ''),
            db_name=os.getenv('DB_NAME', 'metadataservice'),
            db_port=int(os.getenv('DB_PORT', '6432')),

            hashtags=hashtags,
            poll_interval=max(int(os.getenv('TWITTER_POLL_INTERVAL', '120')), 120),  # Min 2 minutes
            max_results=min(max(int(os.getenv('TWITTER_MAX_RESULTS', '100')), 10), 100),  # 10-100 range

            log_level=os.getenv('LOG_LEVEL', 'INFO')
        )

    def validate_config(self) -> bool:
        """Validate configuration settings."""
        errors = []

        if not self.bearer_token:
            errors.append("Twitter Bearer token is required")

        if self.poll_interval < 120:
            errors.append("Poll interval must be at least 120 seconds to respect Twitter rate limits")

        if not (10 <= self.max_results <= 100):
            errors.append("Max results must be between 10 and 100")

        if not self.hashtags:
            errors.append("At least one hashtag must be specified")

        if errors:
            for error in errors:
                print(f"❌ Config error: {error}")
            return False

        return True