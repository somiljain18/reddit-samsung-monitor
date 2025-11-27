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