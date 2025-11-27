"""Main monitoring service for Reddit Samsung posts."""

import logging
import time
import sys
from typing import Optional

from .database import Database
from .reddit_client import RedditClient
from .models import RedditPost, MonitorStats
from .config import setup_logging, load_environment, get_config_from_env, validate_config, print_config_summary


logger = logging.getLogger(__name__)


class RedditMonitor:
    """Main service for monitoring Reddit posts."""

    def __init__(self):
        """Initialize the Reddit monitor."""
        self.config = None
        self.database: Optional[Database] = None
        self.reddit_client: Optional[RedditClient] = None
        self.stats = MonitorStats()
        self.running = False

    def initialize(self) -> bool:
        """
        Initialize the monitor with configuration and connections.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load environment and configuration
            load_environment()
            self.config = get_config_from_env()

            # Set up logging
            setup_logging(self.config.log_level)
            logger.info("Reddit Samsung Monitor starting up...")

            # Validate configuration
            if not validate_config(self.config):
                logger.error("Configuration validation failed")
                return False

            print_config_summary(self.config)

            # Initialize database connection
            self.database = Database(
                host=self.config.db_host,
                user=self.config.db_user,
                password=self.config.db_password,
                database=self.config.db_name,
                port=self.config.db_port
            )

            if not self.database.connect():
                logger.error("Failed to connect to database")
                return False

            # Create tables if they don't exist
            if not self.database.create_tables():
                logger.error("Failed to create database tables")
                return False

            # Initialize Reddit client
            self.reddit_client = RedditClient(user_agent=self.config.user_agent)

            # Test Reddit API connection
            if not self.reddit_client.test_connection():
                logger.error("Failed to connect to Reddit API")
                return False

            # Get subreddit info for all configured subreddits
            logger.info(f"🔄 DEBUG: Monitoring {len(self.config.subreddits)} subreddits: {', '.join(self.config.subreddits)}")
            for subreddit in self.config.subreddits:
                subreddit_info = self.reddit_client.get_subreddit_info(subreddit)
                if subreddit_info:
                    logger.info(f"📂 DEBUG: r/{subreddit_info['display_name']} - "
                               f"{subreddit_info['subscribers']} subscribers")
                else:
                    logger.warning(f"⚠️ DEBUG: Could not get info for r/{subreddit}")

            logger.info("Monitor initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize monitor: {e}")
            return False

    def fetch_and_store_posts(self) -> int:
        """
        Fetch new posts and store them in the database.

        Returns:
            Number of new posts stored
        """
        from datetime import datetime
        cycle_start = datetime.now()
        logger.info(f"🔄 DEBUG: Starting fetch cycle at {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # Get the timestamp of the most recent post for each subreddit
            latest_timestamps = self.database.get_latest_post_times_by_subreddit(self.config.subreddits)

            # Fetch new posts from all subreddits
            logger.info(f"🔍 DEBUG: Calling Reddit API for new posts from {len(self.config.subreddits)} subreddits...")
            raw_posts = self.reddit_client.fetch_posts_from_multiple_subreddits(
                subreddits=self.config.subreddits,
                limit_per_subreddit=self.config.batch_size,
                after_timestamps=latest_timestamps
            )

            if not raw_posts:
                logger.info("⚠️ DEBUG: No new posts fetched from Reddit API")
                print("⚠️ DEBUG: No new posts fetched from Reddit API")
                self.stats.add_fetch_result(0, 0)
                return 0

            logger.info(f"🔍 DEBUG: Processing {len(raw_posts)} posts for database storage...")

            # Convert raw posts to RedditPost models and store them
            new_posts_count = 0
            for i, post_data in enumerate(raw_posts, 1):
                try:
                    logger.debug(f"🔍 DEBUG: Processing post {i}/{len(raw_posts)}: {post_data['post_id']}")
                    reddit_post = RedditPost.from_reddit_data(post_data)

                    if self.database.insert_post(reddit_post.to_dict()):
                        new_posts_count += 1
                        logger.info(f"✅ DEBUG: Successfully stored post {new_posts_count}: {reddit_post.post_id} - {reddit_post.title[:80]}...")

                        # Update the most recent post timestamp
                        if self.stats.last_post_time is None or reddit_post.created_utc > self.stats.last_post_time:
                            self.stats.last_post_time = reddit_post.created_utc
                            logger.debug(f"🔍 DEBUG: Updated latest timestamp to {reddit_post.created_utc}")

                except Exception as e:
                    logger.error(f"❌ DEBUG: Failed to process post {post_data.get('post_id', 'unknown')}: {e}")
                    self.stats.add_error()

            # Update statistics
            self.stats.add_fetch_result(len(raw_posts), new_posts_count)

            # Enhanced results logging
            cycle_end = datetime.now()
            cycle_duration = (cycle_end - cycle_start).total_seconds()

            if new_posts_count > 0:
                total_posts = self.database.get_post_count()
                logger.info(f"🎉 DEBUG: Cycle complete! Stored {new_posts_count} new posts in {cycle_duration:.1f}s. "
                           f"Total posts in database: {total_posts}")
            else:
                logger.info(f"⚠️ DEBUG: Cycle complete! No new posts to store (all {len(raw_posts)} posts were duplicates). "
                           f"Cycle took {cycle_duration:.1f}s")

            logger.info(f"📊 DEBUG: Current stats - {self.stats}")
            return new_posts_count

        except Exception as e:
            logger.error(f"❌ DEBUG: Error during fetch and store operation: {e}")
            import traceback
            logger.debug(f"🔍 DEBUG: Full traceback: {traceback.format_exc()}")
            self.stats.add_error()
            return 0

    def run(self) -> None:
        """
        Main monitoring loop.
        """
        if not self.initialize():
            logger.error("Failed to initialize monitor, exiting")
            sys.exit(1)

        self.running = True
        logger.info(f"Starting monitoring loop with {self.config.poll_interval}s intervals...")

        try:
            while self.running:
                logger.debug("Starting fetch cycle...")

                # Fetch and store new posts
                new_posts = self.fetch_and_store_posts()

                # Log periodic statistics
                runtime = self.stats.get_runtime_seconds()
                if runtime % 300 == 0 and runtime > 0:  # Log every 5 minutes
                    logger.info(f"Stats: {self.stats}")

                # Wait for next cycle
                logger.debug(f"Waiting {self.config.poll_interval} seconds until next fetch...")
                time.sleep(self.config.poll_interval)

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        """
        Gracefully shutdown the monitor.
        """
        logger.info("Shutting down Reddit monitor...")
        self.running = False

        # Log final statistics
        logger.info(f"Final stats: {self.stats}")

        # Close database connection
        if self.database:
            self.database.disconnect()

        logger.info("Shutdown complete")

    def run_once(self) -> int:
        """
        Run a single fetch cycle (useful for testing).

        Returns:
            Number of new posts stored
        """
        if not self.initialize():
            logger.error("Failed to initialize monitor")
            return 0

        try:
            return self.fetch_and_store_posts()
        finally:
            self.shutdown()


if __name__ == "__main__":
    monitor = RedditMonitor()
    monitor.run()