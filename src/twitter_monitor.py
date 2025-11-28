"""Twitter hashtag monitoring service."""

import logging
import time
import signal
import sys
from typing import List, Optional
from datetime import datetime

from .twitter_client import TwitterClient
from .twitter_models import TwitterTweet, TwitterMonitorStats, TwitterConfig
from .database import Database


logger = logging.getLogger(__name__)


class TwitterMonitor:
    """Twitter hashtag monitoring service."""

    def __init__(self, config: Optional[TwitterConfig] = None):
        """Initialize Twitter monitor with configuration."""
        self.config = config or TwitterConfig.from_env()
        self.stats = TwitterMonitorStats(hashtags_monitored=self.config.hashtags)
        self.client: Optional[TwitterClient] = None
        self.database: Optional[Database] = None
        self.running = False
        self._skip_connection_test = False  # Can be set to skip API test

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def initialize(self) -> bool:
        """Initialize all components."""
        try:
            # Validate configuration
            if not self.config.validate_config():
                logger.error("❌ Configuration validation failed")
                return False

            # Set up logging
            self._setup_logging()

            # Initialize database
            logger.info("🔧 Initializing database connection...")
            self.database = Database(
                host=self.config.db_host,
                user=self.config.db_user,
                password=self.config.db_password,
                database=self.config.db_name,
                port=self.config.db_port
            )

            if not self.database.connect():
                logger.error("❌ Failed to connect to database")
                return False

            # Create Twitter tables
            if not self.database.create_twitter_tables():
                logger.error("❌ Failed to create Twitter tables")
                return False

            # Initialize Twitter client
            logger.info("🐦 Initializing Twitter API client...")
            self.client = TwitterClient(
                bearer_token=self.config.bearer_token,
                user_agent=self.config.user_agent
            )

            # Test Twitter API connection (skip if requested to conserve rate limits)
            if not self._skip_connection_test:
                logger.info("🐦 Testing X API connection...")
                if not self.client.test_connection():
                    logger.warning("⚠️ X API connection test failed - continuing anyway (may be rate limited)")
                    logger.info("💡 Use --skip-connection-test flag to conserve rate limits")
            else:
                logger.info("⚠️ Skipping X API connection test to conserve rate limits")

            logger.info("✅ All components initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False

    def _setup_logging(self):
        """Set up logging configuration."""
        import os
        from pathlib import Path

        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # Configure logging
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)

        # File handler
        file_handler = logging.FileHandler(log_dir / "twitter_monitor.log")
        file_handler.setFormatter(logging.Formatter(log_format))

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(log_format))

        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        logger.info(f"📋 Logging configured - Level: {self.config.log_level}")

    def run_once(self) -> int:
        """Run a single monitoring cycle."""
        try:
            logger.info("🚀 Starting single Twitter monitoring cycle...")

            # Get the latest tweet ID from database for incremental fetching
            since_id = self.database.get_latest_tweet_id()
            if since_id:
                logger.info(f"🔍 Fetching tweets since ID: {since_id}")
            else:
                logger.info("🔍 No previous tweets found, fetching recent tweets")

            # Fetch tweets for all hashtags
            tweets = self.client.search_hashtags(
                hashtags=self.config.hashtags,
                max_results=self.config.max_results,
                since_id=since_id
            )

            if not tweets:
                logger.info("📭 No new tweets found")
                return 0

            logger.info(f"📥 Processing {len(tweets)} tweets...")

            # Convert and store tweets
            new_tweets_count = 0
            for tweet_data in tweets:
                try:
                    # Create TwitterTweet model
                    tweet = TwitterTweet.from_twitter_data(tweet_data)

                    # Insert into database
                    if self.database.insert_tweet(tweet.to_dict()):
                        new_tweets_count += 1
                        self.stats.last_tweet_id = tweet.tweet_id

                except Exception as e:
                    logger.error(f"❌ Error processing tweet: {e}")
                    self.stats.add_error()

            # Update statistics
            self.stats.add_fetch_result(len(tweets), new_tweets_count)

            logger.info(f"✅ Monitoring cycle completed - "
                       f"Fetched: {len(tweets)}, New: {new_tweets_count}")

            return new_tweets_count

        except Exception as e:
            logger.error(f"❌ Error in monitoring cycle: {e}")
            self.stats.add_error()
            return -1

    def run(self):
        """Run continuous monitoring."""
        if not self.initialize():
            logger.error("❌ Failed to initialize Twitter monitor")
            sys.exit(1)

        self.running = True
        logger.info(f"🐦 Starting Twitter hashtag monitoring...")
        logger.info(f"📋 Configuration:")
        logger.info(f"   🏷️  Hashtags: {self.config.hashtags}")
        logger.info(f"   ⏱️  Poll interval: {self.config.poll_interval}s")
        logger.info(f"   📊 Max results per fetch: {self.config.max_results}")

        try:
            while self.running:
                cycle_start = time.time()

                # Run monitoring cycle
                new_tweets = self.run_once()

                if new_tweets < 0:
                    logger.error("❌ Monitoring cycle failed, continuing...")

                # Log statistics every 5 minutes
                if self.stats.get_runtime_seconds() % 300 < self.config.poll_interval:
                    self._log_statistics()

                # Calculate sleep time to maintain polling interval
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, self.config.poll_interval - cycle_duration)

                if sleep_time > 0:
                    logger.debug(f"💤 Sleeping for {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                else:
                    logger.warning(f"⚠️ Cycle took {cycle_duration:.1f}s, "
                                 f"longer than poll interval ({self.config.poll_interval}s)")

        except KeyboardInterrupt:
            logger.info("🛑 Keyboard interrupt received, shutting down...")
        except Exception as e:
            logger.error(f"❌ Unexpected error in monitoring loop: {e}")
        finally:
            self._cleanup()

    def _log_statistics(self):
        """Log current monitoring statistics."""
        total_tweets_in_db = self.database.get_tweet_count()

        logger.info("📊 === TWITTER MONITORING STATISTICS ===")
        logger.info(f"🏃 Runtime: {self.stats.get_runtime_seconds()}s")
        logger.info(f"📥 Tweets fetched this session: {self.stats.total_tweets_fetched}")
        logger.info(f"💾 New tweets stored this session: {self.stats.new_tweets_saved}")
        logger.info(f"📊 Total tweets in database: {total_tweets_in_db}")
        logger.info(f"⚠️ Errors encountered: {self.stats.errors_count}")
        logger.info(f"🚫 Rate limit hits: {self.stats.rate_limit_hits}")
        logger.info(f"📈 Average tweets per minute: {self.stats.get_tweets_per_minute():.1f}")
        logger.info(f"🏷️ Hashtags monitored: {', '.join([f'#{tag}' for tag in self.stats.hashtags_monitored])}")

        if self.stats.last_tweet_id:
            logger.info(f"🆔 Latest tweet ID: {self.stats.last_tweet_id}")

        logger.info("=======================================")

    def _cleanup(self):
        """Clean up resources."""
        logger.info("🧹 Performing cleanup...")

        # Log final statistics
        self._log_statistics()

        # Close database connection
        if self.database:
            self.database.disconnect()

        logger.info("✅ Twitter monitor shutdown complete")

    def get_stats(self) -> TwitterMonitorStats:
        """Get current monitoring statistics."""
        return self.stats