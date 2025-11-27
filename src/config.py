"""Configuration and logging setup."""

import logging
import os
from pathlib import Path
from dotenv import load_dotenv


def setup_logging(log_level: str = "DEBUG", log_dir: str = "logs") -> None:
    """
    Set up logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Configure log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Set up root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            # Console handler
            logging.StreamHandler(),
            # File handler
            logging.FileHandler(
                log_path / "reddit_monitor.log",
                mode='a',
                encoding='utf-8'
            )
        ]
    )

    # Set specific log levels for external libraries
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("psycopg2").setLevel(logging.WARNING)


def load_environment() -> None:
    """Load environment variables from .env file if it exists."""
    env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)
        logging.info(f"Loaded environment variables from {env_file}")
    else:
        logging.info("No .env file found, using system environment variables")


def get_config_from_env():
    """Get configuration from environment variables."""
    from .models import Config
    return Config.from_env()


def validate_config(config) -> bool:
    """
    Validate configuration settings.

    Args:
        config: Configuration object

    Returns:
        True if configuration is valid, False otherwise
    """
    errors = []

    # Database validation
    if not config.db_host:
        errors.append("Database host is required")

    if not config.db_user:
        errors.append("Database user is required")

    if not config.db_name:
        errors.append("Database name is required")

    if config.db_port <= 0 or config.db_port > 65535:
        errors.append("Database port must be between 1 and 65535")

    # Application validation
    if config.poll_interval < 10:
        errors.append("Poll interval must be at least 10 seconds to respect rate limits")

    if config.batch_size < 1 or config.batch_size > 100:
        errors.append("Batch size must be between 1 and 100")

    if not config.subreddit or not config.subreddit.replace('_', '').replace('-', '').isalnum():
        errors.append("Invalid subreddit name")

    # Log validation errors
    if errors:
        for error in errors:
            logging.error(f"Configuration error: {error}")
        return False

    return True


def print_config_summary(config) -> None:
    """
    Print a summary of the current configuration.

    Args:
        config: Configuration object
    """
    logging.info("Configuration Summary:")
    logging.info(f"  Database: {config.db_user}@{config.db_host}:{config.db_port}/{config.db_name}")
    logging.info(f"  Subreddit: r/{config.subreddit}")
    logging.info(f"  Poll Interval: {config.poll_interval} seconds")
    logging.info(f"  Batch Size: {config.batch_size} posts")
    logging.info(f"  Log Level: {config.log_level}")


def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    import signal
    import sys

    def signal_handler(signum, frame):
        logging.info(f"Received signal {signum}, initiating graceful shutdown...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logging.info("Signal handlers configured for graceful shutdown")