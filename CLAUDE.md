# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Reddit Samsung Monitor is a Python application that monitors the r/samsung subreddit for new posts and stores them in a PostgreSQL database. The application uses the Reddit JSON API (no authentication required) and provides real-time monitoring with configurable polling intervals.

## Development Commands

### Setup and Installation
```bash
# Initial setup (installs dependencies and creates .env from template)
python setup.py

# Manual dependency installation
pip install -r requirements.txt
```

### Running the Application
```bash
# Test mode - single fetch cycle
python -m src.main --test

# Continuous monitoring
python -m src.main

# Test Reddit API connectivity only
python test_reddit.py

# Example/demo script
python run_example.py
```

### Database Connection
The application expects PostgreSQL with these default connection parameters:
- Host: localhost
- User: adgear
- Database: metadataservice
- Port: 6432

## Architecture Overview

### Core Components

**Main Entry Point**: `src/main.py`
- CLI argument parsing with `--test` flag for single-cycle testing
- Signal handling setup for graceful shutdown

**Monitor Service**: `src/monitor.py` (`RedditMonitor` class)
- Main orchestration logic that coordinates all components
- Initialization sequence: config → logging → database → reddit client
- Main monitoring loop with configurable polling intervals
- Statistics tracking and periodic reporting (every 5 minutes)

**Reddit API Client**: `src/reddit_client.py` (`RedditClient` class)
- Handles Reddit JSON API interactions (no authentication required)
- Fetches new posts with timestamp-based filtering
- User-agent configuration for rate limiting compliance
- Subreddit info retrieval and connection testing

**Database Manager**: `src/database.py` (`Database` class)
- PostgreSQL connection management with psycopg2
- Table creation with proper indexes on `created_utc` and `retrieved_at`
- Post insertion with conflict resolution (ON CONFLICT DO NOTHING)
- Timestamp tracking for incremental fetching

**Configuration**: `src/config.py`
- Environment variable loading from `.env` files
- Validation rules (polling intervals ≥10s, valid subreddit names)
- Logging setup with both console and file output
- Signal handlers for graceful shutdown

**Data Models**: `src/models.py`
- `RedditPost`: Pydantic model for post data with validation
- `MonitorStats`: Runtime statistics tracking
- `Config`: Application configuration with environment variable mapping

### Data Flow

1. **Initialization**: Config → Database connection → Reddit API test
2. **Monitoring Loop**:
   - Get latest post timestamp from database
   - Fetch newer posts from Reddit API
   - Convert raw data to `RedditPost` models
   - Store new posts (duplicates automatically ignored)
   - Update statistics and log progress
   - Sleep for configured interval
3. **Graceful Shutdown**: Statistics logging → Database disconnect

### Database Schema

**Table**: `samsung_posts`
- `post_id` (VARCHAR(20), PRIMARY KEY) - Reddit post ID
- `title` (TEXT, NOT NULL) - Post title
- `author` (VARCHAR(100)) - Username (defaults to "[deleted]")
- `created_utc` (BIGINT, NOT NULL) - Unix timestamp
- `score` (INTEGER, DEFAULT 0) - Upvote score
- `num_comments` (INTEGER, DEFAULT 0) - Comment count
- `url` (TEXT) - Post URL
- `selftext` (TEXT) - Self-post content
- `permalink` (TEXT) - Reddit permalink
- `subreddit` (VARCHAR(50), NOT NULL) - Subreddit name
- `retrieved_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP) - When stored

**Indexes**: `created_utc`, `retrieved_at`

### Configuration

All configuration via environment variables (loaded from `.env` file):

**Database**: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`
**Application**: `POLL_INTERVAL` (≥10s), `BATCH_SIZE` (1-100), `SUBREDDIT`
**System**: `LOG_LEVEL`, `USER_AGENT`

### Error Handling & Logging

- Comprehensive logging to both console and `logs/reddit_monitor.log`
- Statistics tracking for monitoring health (fetch counts, error counts, runtime)
- Graceful degradation: individual post processing errors don't stop the cycle
- Database transaction rollback on errors
- Rate limiting compliance through configurable intervals