"""Main entry point for Reddit Samsung Monitor."""

import argparse
import sys
from .monitor import RedditMonitor
from .config import setup_signal_handlers


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Reddit Samsung Monitor")
    parser.add_argument('--test', action='store_true',
                       help='Run a single test cycle instead of continuous monitoring')
    parser.add_argument('--version', action='version', version='Reddit Samsung Monitor 1.0')

    args = parser.parse_args()

    # Set up signal handlers for graceful shutdown
    setup_signal_handlers()

    # Create and run monitor
    monitor = RedditMonitor()

    if args.test:
        print("Running test cycle...")
        new_posts = monitor.run_once()
        print(f"Test completed. New posts stored: {new_posts}")
        return 0 if new_posts >= 0 else 1
    else:
        print("Starting continuous monitoring... Press Ctrl+C to stop")
        try:
            monitor.run()
            return 0
        except Exception as e:
            print(f"Monitor failed: {e}")
            return 1


if __name__ == "__main__":
    sys.exit(main())