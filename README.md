# Reddit Samsung Monitor

A Python application that monitors the Samsung subreddit for new posts and stores them in a PostgreSQL database.

## Features

- Real-time monitoring of r/samsung subreddit
- Automatic data persistence to PostgreSQL
- Configurable polling intervals
- Logging and error handling

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure database connection:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

3. Run the application:
```bash
python src/main.py
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
- `DB_HOST`: PostgreSQL host
- `DB_USER`: PostgreSQL username
- `DB_PASSWORD`: PostgreSQL password
- `DB_NAME`: Database name
- `DB_PORT`: PostgreSQL port
- `POLL_INTERVAL`: Polling interval in seconds (default: 60)