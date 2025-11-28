"""Configuration management for Twitter hashtag monitoring."""

import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional

from .twitter_models import TwitterConfig


logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def setup_twitter_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        global shutdown_requested
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        shutdown_requested = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def load_twitter_config() -> TwitterConfig:
    """Load Twitter configuration from environment variables."""
    try:
        config = TwitterConfig.from_env()
        logger.info("✅ Twitter configuration loaded successfully")
        return config
    except Exception as e:
        logger.error(f"❌ Failed to load Twitter configuration: {e}")
        raise


def create_twitter_env_template(file_path: str = ".env.twitter"):
    """Create a Twitter environment template file."""
    template_content = """# Twitter API Configuration
# Get your Bearer Token from: https://developer.twitter.com/en/portal/dashboard
TWITTER_BEARER_TOKEN=your_bearer_token_here

# Hashtags to monitor (comma-separated, without # symbol)
TWITTER_HASHTAGS=samsung,technology,mobile

# Monitoring Configuration
TWITTER_POLL_INTERVAL=120  # Minimum 120 seconds (2 minutes) for rate limits
TWITTER_MAX_RESULTS=100    # 10-100 tweets per request

# Twitter API Settings
TWITTER_USER_AGENT=TwitterHashtagMonitor/1.0

# Database Configuration (shared with Reddit monitor)
DB_HOST=localhost
DB_USER=adgear
DB_PASSWORD=
DB_NAME=metadataservice
DB_PORT=6432

# Logging
LOG_LEVEL=INFO
"""

    try:
        with open(file_path, 'w') as f:
            f.write(template_content)
        logger.info(f"✅ Twitter environment template created: {file_path}")
        print(f"📄 Twitter environment template created: {file_path}")
        print("📝 Please edit the file and add your Twitter Bearer Token")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create Twitter environment template: {e}")
        return False


def validate_twitter_environment() -> bool:
    """Validate Twitter environment variables."""
    required_vars = ['TWITTER_BEARER_TOKEN']
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("💡 Run with --create-env to create a template .env.twitter file")
        return False

    return True


def setup_twitter_logging(log_level: str = "INFO"):
    """Set up logging for Twitter monitoring."""
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure logging
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # File handler for Twitter logs
    file_handler = logging.FileHandler(log_dir / "twitter_monitor.log")
    file_handler.setFormatter(logging.Formatter(log_format))

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Add handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logger.info(f"📋 Twitter logging configured - Level: {log_level}")


def load_env_file(env_file: str = ".env.twitter"):
    """Load environment variables from a file."""
    if not os.path.exists(env_file):
        logger.warning(f"⚠️ Environment file {env_file} not found")
        return False

    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

        logger.info(f"✅ Environment variables loaded from {env_file}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to load environment file {env_file}: {e}")
        return False


def check_twitter_api_requirements():
    """Check Twitter API requirements and provide guidance."""
    print("🐦 Twitter API Requirements:")
    print("   1. Twitter Developer Account (free)")
    print("   2. Twitter API Bearer Token")
    print("   3. Basic plan rate limits: 300 requests per 15 minutes")
    print("   4. Search endpoint: ~10,000 tweets per month")
    print("")
    print("📝 Setup Instructions:")
    print("   1. Visit: https://developer.twitter.com/en/portal/dashboard")
    print("   2. Create a new App/Project")
    print("   3. Generate Bearer Token")
    print("   4. Add token to your .env.twitter file")
    print("")
    print("⚠️ Rate Limit Considerations:")
    print("   - Minimum polling interval: 120 seconds (2 minutes)")
    print("   - Maximum 100 tweets per request")
    print("   - Monitor usage to stay within limits")


def get_twitter_rate_limit_info():
    """Get information about Twitter API rate limits."""
    return {
        "search_tweets": {
            "requests_per_15min": 300,
            "tweets_per_request": 100,
            "recommended_poll_interval": 120  # seconds
        },
        "user_lookup": {
            "requests_per_15min": 300
        }
    }