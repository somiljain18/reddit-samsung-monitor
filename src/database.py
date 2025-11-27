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