"""Main entry point for Twitter hashtag monitoring."""

import argparse
import sys
import os
from pathlib import Path

from .twitter_monitor import TwitterMonitor
from .twitter_config import (
    setup_twitter_signal_handlers,
    load_twitter_config,
    create_twitter_env_template,
    validate_twitter_environment,
    setup_twitter_logging,
    load_env_file,
    check_twitter_api_requirements,
    get_twitter_rate_limit_info
)


def main():
    """Main entry point for Twitter hashtag monitoring."""
    parser = argparse.ArgumentParser(
        description="Twitter Hashtag Monitor - Real-time hashtag tracking and storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.twitter_main                    # Start continuous monitoring
  python -m src.twitter_main --test             # Run single test cycle
  python -m src.twitter_main --create-env       # Create environment template
  python -m src.twitter_main --check-api        # Show API requirements
  python -m src.twitter_main --env .env.custom  # Use custom env file

Environment Variables:
  TWITTER_BEARER_TOKEN     Twitter API Bearer Token (required)
  TWITTER_HASHTAGS         Comma-separated hashtags (default: samsung,technology)
  TWITTER_POLL_INTERVAL    Polling interval in seconds (min: 120)
  TWITTER_MAX_RESULTS      Max tweets per request (10-100, default: 100)
        """)

    parser.add_argument('--test', action='store_true',
                       help='Run a single test cycle instead of continuous monitoring')

    parser.add_argument('--create-env', action='store_true',
                       help='Create a Twitter environment template file (.env.twitter)')

    parser.add_argument('--check-api', action='store_true',
                       help='Show Twitter API requirements and setup instructions')

    parser.add_argument('--env', type=str, default='.env.twitter',
                       help='Path to environment file (default: .env.twitter)')

    parser.add_argument('--version', action='version',
                       version='Twitter Hashtag Monitor 1.0')

    parser.add_argument('--rate-limits', action='store_true',
                       help='Show Twitter API rate limit information')

    parser.add_argument('--check-usage', action='store_true',
                       help='Check current API rate limit usage')

    parser.add_argument('--skip-connection-test', action='store_true',
                       help='Skip API connection test to conserve rate limits')

    args = parser.parse_args()

    # Handle special commands that don't require full setup
    if args.create_env:
        success = create_twitter_env_template(args.env)
        return 0 if success else 1

    if args.check_api:
        check_twitter_api_requirements()
        return 0

    if args.rate_limits:
        rate_limits = get_twitter_rate_limit_info()
        print("🐦 Twitter API Rate Limits:")
        for endpoint, limits in rate_limits.items():
            print(f"\n📍 {endpoint.replace('_', ' ').title()}:")
            for key, value in limits.items():
                print(f"   {key.replace('_', ' ').title()}: {value}")
        return 0

    if args.check_usage:
        # Load environment and check current usage
        if os.path.exists(args.env):
            load_env_file(args.env)

        if not validate_twitter_environment():
            print("❌ Environment validation failed")
            return 1

        try:
            from .twitter_client import TwitterClient
            config = load_twitter_config()
            client = TwitterClient(config.bearer_token, config.user_agent)

            print("🔍 Checking current X API rate limit usage...")
            rate_info = client.get_rate_limit_status()

            if rate_info:
                print(f"\n📊 X API Rate Limit Status:")
                print(f"   🔢 Total Limit: {rate_info.get('limit', 'unknown')}")
                print(f"   ⚡ Remaining: {rate_info.get('remaining', 'unknown')}")
                print(f"   🕒 Reset Time: {rate_info.get('reset_readable', rate_info.get('reset', 'unknown'))}")

                # Calculate usage percentage
                if rate_info.get('limit') != 'unknown' and rate_info.get('remaining') != 'unknown':
                    try:
                        limit = int(rate_info['limit'])
                        remaining = int(rate_info['remaining'])
                        used = limit - remaining
                        usage_pct = (used / limit) * 100
                        print(f"   📈 Used: {used}/{limit} ({usage_pct:.1f}%)")

                        if usage_pct > 80:
                            print("   ⚠️  WARNING: High usage - consider increasing poll interval")
                        elif usage_pct > 50:
                            print("   💡 NOTICE: Moderate usage - monitor closely")
                        else:
                            print("   ✅ GOOD: Low usage - plenty of capacity")
                    except ValueError:
                        pass

                return 0
            else:
                print("❌ Failed to get rate limit information")
                return 1

        except Exception as e:
            print(f"❌ Failed to check usage: {e}")
            return 1

    # Load environment file if it exists
    if os.path.exists(args.env):
        load_env_file(args.env)
        print(f"📄 Loaded environment from: {args.env}")
    else:
        print(f"⚠️ Environment file not found: {args.env}")
        print(f"💡 Use --create-env to create a template file")

    # Validate environment
    if not validate_twitter_environment():
        print(f"❌ Environment validation failed")
        print(f"💡 Use --create-env to create a template file")
        print(f"💡 Use --check-api to see setup requirements")
        return 1

    try:
        # Load configuration
        config = load_twitter_config()

        # Set up logging
        setup_twitter_logging(config.log_level)

        # Set up signal handlers for graceful shutdown
        setup_twitter_signal_handlers()

        # Create and initialize monitor
        monitor = TwitterMonitor(config)

        # Skip connection test if requested (for low rate limits)
        if args.skip_connection_test:
            print("⚠️ Skipping connection test to conserve rate limits")
            monitor._skip_connection_test = True

        if args.test:
            print("🧪 Running Twitter hashtag monitoring test cycle...")
            print(f"🏷️ Monitoring hashtags: {', '.join([f'#{tag}' for tag in config.hashtags])}")

            # Initialize monitor for test
            if not monitor.initialize():
                print("❌ Failed to initialize Twitter monitor")
                return 1

            # Run single cycle
            new_tweets = monitor.run_once()

            if new_tweets >= 0:
                print(f"✅ Test completed successfully. New tweets stored: {new_tweets}")

                # Show some stats
                stats = monitor.get_stats()
                print(f"📊 Total tweets fetched: {stats.total_tweets_fetched}")
                print(f"💾 New tweets saved: {stats.new_tweets_saved}")

                if stats.errors_count > 0:
                    print(f"⚠️ Errors encountered: {stats.errors_count}")

                return 0
            else:
                print("❌ Test cycle failed")
                return 1
        else:
            print("🚀 Starting Twitter hashtag monitoring...")
            print(f"🏷️ Monitoring hashtags: {', '.join([f'#{tag}' for tag in config.hashtags])}")
            print(f"⏱️ Poll interval: {config.poll_interval} seconds")
            print(f"📊 Max results per fetch: {config.max_results}")
            print("Press Ctrl+C to stop")

            try:
                monitor.run()
                return 0
            except KeyboardInterrupt:
                print("\n🛑 Monitoring stopped by user")
                return 0
            except Exception as e:
                print(f"❌ Monitor failed: {e}")
                return 1

    except KeyboardInterrupt:
        print("\n🛑 Startup interrupted by user")
        return 0
    except Exception as e:
        print(f"❌ Failed to start Twitter monitor: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())