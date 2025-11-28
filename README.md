# Reddit Samsung Monitor

A Python application that monitors multiple subreddits (Samsung, Apple, Technology) for new posts and stores them in a PostgreSQL database. Features both real-time monitoring and historical data backfill capabilities.

## Features

- **Multi-subreddit monitoring** - Supports Samsung, Apple, Technology, and other subreddits
- **Real-time monitoring** - Continuous polling for new posts with configurable intervals
- **Historical data backfill** - Comprehensive tool to fill gaps with older posts
- **Smart duplicate prevention** - Automatically avoids storing duplicate posts
- **Robust data persistence** - PostgreSQL storage with proper indexing
- **Comprehensive logging** - Both console and file-based logging
- **Rate limiting compliance** - Respects Reddit API guidelines
- **Error handling and recovery** - Graceful degradation on individual failures
- **Statistics tracking** - Monitor performance and data collection metrics

## Quick Start

### 1. Initial Setup
```bash
# Clone and setup (installs dependencies and creates .env from template)
python setup.py

# Or manually install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy environment template and configure your database connection
cp .env.example .env
# Edit .env with your PostgreSQL credentials
```

### 3. Running Options

#### Regular Monitoring (Continuous)
```bash
# Start continuous monitoring
python -m src.main

# Test mode (single fetch cycle)
python -m src.main --test
```

#### Historical Data Backfill
```bash
# Interactive backfill for all configured subreddits (Recommended)
python run_backfill.py

# Manual backfill for specific subreddit
python backfill_historical.py samsung 1000

# Test Reddit API connectivity
python test_reddit.py
```

## Database Schema

The application creates a `samsung_posts` table with the following structure:
- post_id (primary key)
- title
- author
- created_utc
- score
- num_comments
- url
- selftext
- permalink
- subreddit
- retrieved_at

## Configuration

Set the following environment variables in your `.env` file:

### Database Configuration
- `DB_HOST`: PostgreSQL host (default: localhost)
- `DB_USER`: PostgreSQL username (default: adgear)
- `DB_PASSWORD`: PostgreSQL password
- `DB_NAME`: Database name (default: metadataservice)
- `DB_PORT`: PostgreSQL port (default: 6432)

### Application Configuration
- `POLL_INTERVAL`: Polling interval in seconds (minimum: 10, default: 60)
- `BATCH_SIZE`: Posts to fetch per cycle (1-100, default: 25)
- `SUBREDDIT`: Comma-separated list of subreddits (default: samsung,apple,technology)
- `USER_AGENT`: Custom user agent string
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, default: INFO)

## Historical Data Backfill

The backfill system uses multiple Reddit API endpoints to maximize historical data collection:

### How It Works
- **Top Posts (All Time)** - Fetches the most popular posts ever
- **Top Posts by Period** - Year, month, week timeframes
- **Hot Posts** - Currently trending posts
- **Smart Pagination** - Fetches in 100-post batches with rate limiting
- **Duplicate Prevention** - Automatically skips posts already in database

### Expected Results
- **Samsung subreddit**: ~2,000-5,000 additional posts
- **Apple subreddit**: ~3,000-8,000 additional posts
- **Technology subreddit**: ~5,000-15,000 additional posts
- **Runtime**: 10-30 minutes depending on subreddit size
- **Rate limiting**: 2-second delays between requests for API compliance

### Usage
```bash
# Interactive mode (recommended)
python run_backfill.py

# Manual mode for specific subreddit
python backfill_historical.py <subreddit> [max_posts_per_method]

# Examples
python backfill_historical.py samsung 1000
python backfill_historical.py apple 800
```

## Architecture

### Core Components
- **`src/main.py`** - CLI entry point with test mode support
- **`src/monitor.py`** - Main orchestration (RedditMonitor class)
- **`src/reddit_client.py`** - Reddit API client with multi-subreddit support
- **`src/database.py`** - PostgreSQL management with connection pooling
- **`src/config.py`** - Configuration loading and validation
- **`src/models.py`** - Pydantic data models for type safety

### Backfill Components
- **`backfill_historical.py`** - Advanced backfill engine
- **`run_backfill.py`** - Interactive backfill runner

## Monitoring & Logging

- **Console logging**: Real-time progress and status updates
- **File logging**: Detailed logs in `logs/reddit_monitor.log` and `logs/backfill.log`
- **Statistics tracking**: Fetch counts, error rates, runtime metrics
- **Database queries**: Monitor post counts and time ranges

### Example Database Queries
```sql
-- Current statistics by subreddit
SELECT
    subreddit,
    MIN(to_timestamp(created_utc)) AS earliest_post,
    MAX(to_timestamp(created_utc)) AS latest_post,
    COUNT(*) AS total_posts
FROM samsung_posts
GROUP BY subreddit
ORDER BY subreddit;

-- Recent posts
SELECT title, author, to_timestamp(created_utc), subreddit
FROM samsung_posts
ORDER BY created_utc DESC
LIMIT 10;
```

## Twitter Hashtag Monitoring

**NEW**: This repository now includes a separate Twitter hashtag monitoring system that runs alongside the Reddit monitor.

### Features
- **Real-time hashtag tracking** - Monitor specific hashtags on Twitter
- **Twitter API v2 integration** - Uses Bearer token authentication
- **Independent database schema** - Separate `twitter_tweets` table
- **Rate limit compliance** - Respects Twitter API limits (300 requests/15min)
- **Comprehensive tweet data** - Stores metrics, author info, and engagement data
- **Separate configuration** - Independent `.env.twitter` file

### Quick Start - Twitter Monitor

#### 1. Setup Twitter API Access
```bash
# Create environment template
python3 -m src.twitter_main --create-env

# Check API requirements and setup instructions
python3 -m src.twitter_main --check-api

# View rate limit information
python3 -m src.twitter_main --rate-limits
```

#### 2. Configure Twitter Environment
```bash
# Edit .env.twitter file and add your Twitter Bearer Token
# Get your token from: https://developer.twitter.com/en/portal/dashboard
nano .env.twitter
```

#### 3. Running Twitter Monitor
```bash
# Test mode (single cycle)
python3 -m src.twitter_main --test

# Continuous monitoring
python3 -m src.twitter_main

# Use custom environment file
python3 -m src.twitter_main --env .env.custom
```

### Twitter Configuration

Set the following variables in your `.env.twitter` file:

#### Required
- `TWITTER_BEARER_TOKEN`: Your Twitter API Bearer Token

#### Optional
- `TWITTER_HASHTAGS`: Comma-separated hashtags (default: samsung,technology,mobile)
- `TWITTER_POLL_INTERVAL`: Polling interval in seconds (min: 120, default: 120)
- `TWITTER_MAX_RESULTS`: Max tweets per request (10-100, default: 100)
- `TWITTER_USER_AGENT`: Custom user agent (default: TwitterHashtagMonitor/1.0)

### Twitter Database Schema

The Twitter monitor creates a `twitter_tweets` table:
- tweet_id (primary key)
- text
- author_id, author_username, author_name, author_verified
- created_at, created_utc
- lang (language code)
- retweet_count, like_count, reply_count, quote_count
- conversation_id, in_reply_to_user_id
- hashtags (comma-separated)
- referenced_tweets
- retrieved_at

### Twitter API Requirements

- **Twitter Developer Account** (free)
- **Bearer Token** from Twitter Developer Portal
- **Rate Limits**: 300 requests per 15 minutes (Basic plan)
- **Search Limit**: ~10,000 tweets per month
- **Minimum Poll Interval**: 120 seconds (2 minutes)

### Example Twitter Queries
```sql
-- Recent tweets by hashtag
SELECT text, author_username, to_timestamp(created_utc), hashtags
FROM twitter_tweets
WHERE hashtags LIKE '%samsung%'
ORDER BY created_utc DESC
LIMIT 10;

-- Tweet statistics by hashtag
SELECT
    UNNEST(string_to_array(hashtags, ',')) as hashtag,
    COUNT(*) as tweet_count,
    AVG(like_count) as avg_likes
FROM twitter_tweets
GROUP BY hashtag
ORDER BY tweet_count DESC;
```

### Running Both Monitors

The Reddit and Twitter monitors can run simultaneously:

```bash
# Terminal 1: Reddit monitoring
python3 -m src.main

# Terminal 2: Twitter monitoring
python3 -m src.twitter_main
```

Both systems use the same PostgreSQL database but separate tables, so they won't interfere with each other.