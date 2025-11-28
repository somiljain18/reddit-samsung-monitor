"""Database connection and management module."""

import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any, List
import os


logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL database connection manager."""

    def __init__(self,
                 host: str = None,
                 user: str = None,
                 password: str = None,
                 database: str = None,
                 port: int = None):
        """Initialize database connection parameters."""
        self.host = host or os.getenv('DB_HOST', 'localhost')
        self.user = user or os.getenv('DB_USER', 'adgear')
        self.password = password or os.getenv('DB_PASSWORD', '')
        self.database = database or os.getenv('DB_NAME', 'metadataservice')
        self.port = port or int(os.getenv('DB_PORT', '6432'))
        self.connection: Optional[psycopg2.extensions.connection] = None

    def connect(self) -> bool:
        """Establish database connection."""
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                cursor_factory=RealDictCursor
            )
            logger.info(f"Connected to database {self.database} at {self.host}:{self.port}")
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            return False

    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def create_tables(self):
        """Create the samsung_posts table if it doesn't exist."""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS samsung_posts (
            post_id VARCHAR(20) PRIMARY KEY,
            title TEXT NOT NULL,
            author VARCHAR(100),
            created_utc BIGINT NOT NULL,
            score INTEGER DEFAULT 0,
            num_comments INTEGER DEFAULT 0,
            url TEXT,
            selftext TEXT,
            permalink TEXT,
            subreddit VARCHAR(50) NOT NULL,
            retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(post_id)
        );

        CREATE INDEX IF NOT EXISTS idx_created_utc ON samsung_posts(created_utc);
        CREATE INDEX IF NOT EXISTS idx_retrieved_at ON samsung_posts(retrieved_at);
        """

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(create_table_query)
                self.connection.commit()
                logger.info("Tables created successfully")
                return True
        except psycopg2.Error as e:
            logger.error(f"Failed to create tables: {e}")
            self.connection.rollback()
            return False

    def insert_post(self, post_data: Dict[str, Any]) -> bool:
        """Insert a new post into the database."""
        insert_query = """
        INSERT INTO samsung_posts
        (post_id, title, author, created_utc, score, num_comments, url, selftext, permalink, subreddit)
        VALUES (%(post_id)s, %(title)s, %(author)s, %(created_utc)s, %(score)s, %(num_comments)s,
                %(url)s, %(selftext)s, %(permalink)s, %(subreddit)s)
        ON CONFLICT (post_id) DO NOTHING
        """

        # Enhanced debug logging
        from datetime import datetime
        post_time_readable = datetime.fromtimestamp(post_data['created_utc']).strftime('%Y-%m-%d %H:%M:%S UTC')
        logger.info(f"🔍 DEBUG: Attempting to insert post {post_data['post_id']}")
        logger.debug(f"🔍 DEBUG: Post details - created_utc: {post_data['created_utc']} ({post_time_readable}), "
                    f"title: '{post_data['title'][:100]}...', author: {post_data['author']}")

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(insert_query, post_data)
                self.connection.commit()
                if cursor.rowcount > 0:
                    logger.info(f"✅ DEBUG: Successfully inserted new post: {post_data['post_id']}")
                    return True
                else:
                    logger.info(f"⚠️ DEBUG: Post already exists in database: {post_data['post_id']}")
                    return False
        except psycopg2.Error as e:
            logger.error(f"❌ Database error inserting post {post_data.get('post_id', 'unknown')}: {e}")
            self.connection.rollback()
            return False

    def get_latest_post_time(self) -> Optional[int]:
        """Get the created_utc timestamp of the most recent post."""
        query = "SELECT MAX(created_utc) as latest_time FROM samsung_posts"

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                latest_time = result['latest_time'] if result and result['latest_time'] else 0

                # Enhanced debug logging
                from datetime import datetime
                if latest_time > 0:
                    latest_readable = datetime.fromtimestamp(latest_time).strftime('%Y-%m-%d %H:%M:%S UTC')
                    logger.info(f"🔍 DEBUG: Latest post in database: {latest_time} ({latest_readable})")
                else:
                    logger.info(f"🔍 DEBUG: No posts found in database, using timestamp 0")

                return latest_time
        except psycopg2.Error as e:
            logger.error(f"❌ Failed to get latest post time: {e}")
            return 0

    def get_latest_post_times_by_subreddit(self, subreddits: List[str]) -> Dict[str, int]:
        """Get the latest post timestamp for each subreddit."""
        placeholders = ','.join(['%s'] * len(subreddits))
        query = f"""
        SELECT subreddit, MAX(created_utc) as latest_time
        FROM samsung_posts
        WHERE subreddit IN ({placeholders})
        GROUP BY subreddit
        """

        result_dict = {}

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, subreddits)
                results = cursor.fetchall()

                # Initialize all subreddits with 0
                for subreddit in subreddits:
                    result_dict[subreddit] = 0

                # Update with actual values from database
                for row in results:
                    result_dict[row['subreddit']] = row['latest_time'] or 0

                # Enhanced debug logging with print statements
                from datetime import datetime
                logger.info(f"🔍 DEBUG: Latest timestamps by subreddit:")
                print(f"🕒 DATABASE TIMESTAMPS per subreddit:")
                for subreddit, timestamp in result_dict.items():
                    if timestamp > 0:
                        readable = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
                        logger.info(f"  📂 r/{subreddit}: {timestamp} ({readable})")
                        print(f"   r/{subreddit}: Last post at {readable}")
                    else:
                        logger.info(f"  📂 r/{subreddit}: 0 (no posts)")
                        print(f"   r/{subreddit}: No posts yet (will fetch from beginning)")

                return result_dict

        except psycopg2.Error as e:
            logger.error(f"❌ Failed to get latest post times by subreddit: {e}")
            # Return default values on error
            return {subreddit: 0 for subreddit in subreddits}

    def get_post_count(self) -> int:
        """Get total number of posts in database."""
        query = "SELECT COUNT(*) as count FROM samsung_posts"

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                return result['count'] if result else 0
        except psycopg2.Error as e:
            logger.error(f"Failed to get post count: {e}")
            return 0

    # Twitter-specific methods
    def create_twitter_tables(self):
        """Create the twitter_tweets table if it doesn't exist."""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS twitter_tweets (
            tweet_id VARCHAR(20) PRIMARY KEY,
            text TEXT NOT NULL,
            author_id VARCHAR(20) NOT NULL,
            author_username VARCHAR(50),
            author_name VARCHAR(100),
            author_verified BOOLEAN DEFAULT FALSE,
            created_at VARCHAR(30),
            created_utc BIGINT NOT NULL,
            lang VARCHAR(10) DEFAULT 'und',
            retweet_count INTEGER DEFAULT 0,
            like_count INTEGER DEFAULT 0,
            reply_count INTEGER DEFAULT 0,
            quote_count INTEGER DEFAULT 0,
            conversation_id VARCHAR(20),
            in_reply_to_user_id VARCHAR(20),
            hashtags TEXT,
            referenced_tweets TEXT,
            retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(tweet_id)
        );

        CREATE INDEX IF NOT EXISTS idx_twitter_created_utc ON twitter_tweets(created_utc);
        CREATE INDEX IF NOT EXISTS idx_twitter_retrieved_at ON twitter_tweets(retrieved_at);
        CREATE INDEX IF NOT EXISTS idx_twitter_hashtags ON twitter_tweets(hashtags);
        CREATE INDEX IF NOT EXISTS idx_twitter_author_username ON twitter_tweets(author_username);
        """

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(create_table_query)
                self.connection.commit()
                logger.info("Twitter tables created successfully")
                return True
        except psycopg2.Error as e:
            logger.error(f"Failed to create Twitter tables: {e}")
            self.connection.rollback()
            return False

    def insert_tweet(self, tweet_data: Dict[str, Any]) -> bool:
        """Insert a new tweet into the database."""
        insert_query = """
        INSERT INTO twitter_tweets
        (tweet_id, text, author_id, author_username, author_name, author_verified,
         created_at, created_utc, lang, retweet_count, like_count, reply_count, quote_count,
         conversation_id, in_reply_to_user_id, hashtags, referenced_tweets)
        VALUES (%(tweet_id)s, %(text)s, %(author_id)s, %(author_username)s, %(author_name)s, %(author_verified)s,
                %(created_at)s, %(created_utc)s, %(lang)s, %(retweet_count)s, %(like_count)s, %(reply_count)s, %(quote_count)s,
                %(conversation_id)s, %(in_reply_to_user_id)s, %(hashtags)s, %(referenced_tweets)s)
        ON CONFLICT (tweet_id) DO NOTHING
        """

        # Enhanced debug logging
        from datetime import datetime
        tweet_time_readable = datetime.fromtimestamp(tweet_data['created_utc']).strftime('%Y-%m-%d %H:%M:%S UTC')
        logger.info(f"🔍 DEBUG: Attempting to insert tweet {tweet_data['tweet_id']}")
        logger.debug(f"🔍 DEBUG: Tweet details - created_utc: {tweet_data['created_utc']} ({tweet_time_readable}), "
                    f"text: '{tweet_data['text'][:100]}...', author: @{tweet_data['author_username']}")

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(insert_query, tweet_data)
                self.connection.commit()
                if cursor.rowcount > 0:
                    logger.info(f"✅ DEBUG: Successfully inserted new tweet: {tweet_data['tweet_id']}")
                    return True
                else:
                    logger.info(f"⚠️ DEBUG: Tweet already exists in database: {tweet_data['tweet_id']}")
                    return False
        except psycopg2.Error as e:
            logger.error(f"❌ Database error inserting tweet {tweet_data.get('tweet_id', 'unknown')}: {e}")
            self.connection.rollback()
            return False

    def get_latest_tweet_id(self) -> Optional[str]:
        """Get the tweet_id of the most recent tweet."""
        query = "SELECT tweet_id FROM twitter_tweets ORDER BY created_utc DESC LIMIT 1"

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                latest_id = result['tweet_id'] if result else None

                if latest_id:
                    logger.info(f"🔍 DEBUG: Latest tweet ID in database: {latest_id}")
                else:
                    logger.info(f"🔍 DEBUG: No tweets found in database")

                return latest_id
        except psycopg2.Error as e:
            logger.error(f"❌ Failed to get latest tweet ID: {e}")
            return None

    def get_tweet_count(self) -> int:
        """Get total number of tweets in database."""
        query = "SELECT COUNT(*) as count FROM twitter_tweets"

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                return result['count'] if result else 0
        except psycopg2.Error as e:
            logger.error(f"Failed to get tweet count: {e}")
            return 0

    def get_tweets_by_hashtag(self, hashtag: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get tweets containing a specific hashtag."""
        query = """
        SELECT * FROM twitter_tweets
        WHERE hashtags LIKE %s
        ORDER BY created_utc DESC
        LIMIT %s
        """

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, (f'%{hashtag}%', limit))
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except psycopg2.Error as e:
            logger.error(f"Failed to get tweets by hashtag {hashtag}: {e}")
            return []