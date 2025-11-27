"""Data models for Reddit posts."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class RedditPost(BaseModel):
    """Reddit post data model."""

    post_id: str = Field(..., description="Unique Reddit post ID")
    title: str = Field(..., description="Post title")
    author: str = Field(default="[deleted]", description="Post author username")
    created_utc: int = Field(..., description="Unix timestamp when post was created")
    score: int = Field(default=0, description="Post upvote score")
    num_comments: int = Field(default=0, description="Number of comments")
    url: str = Field(default="", description="Post URL")
    selftext: str = Field(default="", description="Post self-text content")
    permalink: str = Field(default="", description="Reddit permalink to post")
    subreddit: str = Field(default="samsung", description="Subreddit name")

    def to_dict(self) -> dict:
        """Convert model to dictionary for database insertion."""
        return {
            'post_id': self.post_id,
            'title': self.title,
            'author': self.author,
            'created_utc': self.created_utc,
            'score': self.score,
            'num_comments': self.num_comments,
            'url': self.url,
            'selftext': self.selftext,
            'permalink': self.permalink,
            'subreddit': self.subreddit
        }

    @classmethod
    def from_reddit_data(cls, data: dict) -> 'RedditPost':
        """Create RedditPost from raw Reddit API data."""
        return cls(
            post_id=data.get('post_id', ''),
            title=data.get('title', ''),
            author=data.get('author', '[deleted]'),
            created_utc=data.get('created_utc', 0),
            score=data.get('score', 0),
            num_comments=data.get('num_comments', 0),
            url=data.get('url', ''),
            selftext=data.get('selftext', ''),
            permalink=data.get('permalink', ''),
            subreddit=data.get('subreddit', 'samsung')
        )

    def __str__(self) -> str:
        return f"RedditPost(id={self.post_id}, title='{self.title[:50]}...', author={self.author})"

    def __repr__(self) -> str:
        return self.__str__()


class MonitorStats(BaseModel):
    """Statistics for the monitoring session."""

    total_posts_fetched: int = Field(default=0, description="Total posts fetched in session")
    new_posts_saved: int = Field(default=0, description="New posts saved to database")
    errors_count: int = Field(default=0, description="Number of errors encountered")
    start_time: datetime = Field(default_factory=datetime.now, description="Session start time")
    last_fetch_time: Optional[datetime] = Field(default=None, description="Last successful fetch time")
    last_post_time: Optional[int] = Field(default=None, description="Unix timestamp of most recent post")

    def add_fetch_result(self, posts_fetched: int, new_posts: int):
        """Update stats after a fetch operation."""
        self.total_posts_fetched += posts_fetched
        self.new_posts_saved += new_posts
        self.last_fetch_time = datetime.now()

    def add_error(self):
        """Increment error count."""
        self.errors_count += 1

    def get_runtime_seconds(self) -> int:
        """Get total runtime in seconds."""
        return int((datetime.now() - self.start_time).total_seconds())

    def __str__(self) -> str:
        runtime = self.get_runtime_seconds()
        return (f"MonitorStats(runtime={runtime}s, fetched={self.total_posts_fetched}, "
                f"saved={self.new_posts_saved}, errors={self.errors_count})")


class Config(BaseModel):
    """Application configuration model."""

    db_host: str = Field(default="localhost", description="Database host")
    db_user: str = Field(default="adgear", description="Database user")
    db_password: str = Field(default="", description="Database password")
    db_name: str = Field(default="metadataservice", description="Database name")
    db_port: int = Field(default=6432, description="Database port")

    subreddits: List[str] = Field(default=["samsung", "technology"], description="List of subreddits to monitor")
    poll_interval: int = Field(default=60, description="Polling interval in seconds")
    batch_size: int = Field(default=25, description="Number of posts to fetch per request")

    log_level: str = Field(default="INFO", description="Logging level")
    user_agent: str = Field(default="RedditMultiMonitor/1.0", description="User agent for requests")

    @classmethod
    def from_env(cls) -> 'Config':
        """Create config from environment variables."""
        import os

        # Parse subreddits from environment variable (comma-separated)
        subreddits_env = os.getenv('SUBREDDITS', 'samsung,technology')
        subreddits = [sub.strip() for sub in subreddits_env.split(',') if sub.strip()]

        return cls(
            db_host=os.getenv('DB_HOST', 'localhost'),
            db_user=os.getenv('DB_USER', 'adgear'),
            db_password=os.getenv('DB_PASSWORD', ''),
            db_name=os.getenv('DB_NAME', 'metadataservice'),
            db_port=int(os.getenv('DB_PORT', '6432')),

            subreddits=subreddits,
            poll_interval=int(os.getenv('POLL_INTERVAL', '60')),
            batch_size=int(os.getenv('BATCH_SIZE', '25')),

            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            user_agent=os.getenv('USER_AGENT', 'RedditMultiMonitor/1.0')
        )