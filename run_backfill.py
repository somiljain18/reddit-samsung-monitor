#!/usr/bin/env python3
"""
Quick runner for historical backfill operations.
"""

import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from backfill_historical import HistoricalBackfill

def main():
    """Run backfill for all configured subreddits."""
    print("🚀 Reddit Historical Backfill Tool")
    print("=" * 50)

    # Create logs directory
    os.makedirs('logs', exist_ok=True)

    backfill = HistoricalBackfill()

    try:
        if not backfill.initialize():
            print("❌ Failed to initialize backfill system")
            return

        # Show current stats first
        print("\n📊 Current Database Stats (Before Backfill):")
        backfill.get_current_stats()

        # Get subreddits to backfill
        subreddits_to_backfill = ['samsung', 'apple', 'technology']  # Based on your current data

        print(f"\n🎯 Planning to backfill {len(subreddits_to_backfill)} subreddits:")
        for sub in subreddits_to_backfill:
            print(f"   📂 r/{sub}")

        # Confirm before proceeding
        response = input(f"\n🤔 Continue with backfill? This may take 10-30 minutes. (y/N): ")
        if response.lower() != 'y':
            print("❌ Backfill cancelled")
            return

        total_new_posts = 0
        overall_start = datetime.now()

        # Backfill each subreddit
        for i, subreddit in enumerate(subreddits_to_backfill, 1):
            print(f"\n🔄 [{i}/{len(subreddits_to_backfill)}] Processing r/{subreddit}")
            print("-" * 40)

            start_time = datetime.now()
            new_posts = backfill.backfill_subreddit_comprehensive(subreddit, max_posts_per_method=800)
            end_time = datetime.now()

            duration = (end_time - start_time).total_seconds()
            total_new_posts += new_posts

            print(f"✅ r/{subreddit} complete: {new_posts} new posts in {duration:.1f}s")

        overall_end = datetime.now()
        overall_duration = (overall_end - overall_start).total_seconds()

        # Show final results
        print("\n" + "=" * 50)
        print("🎉 BACKFILL COMPLETE!")
        print("=" * 50)

        print("\n📊 Final Database Stats:")
        backfill.get_current_stats()

        print(f"\n📈 Summary:")
        print(f"   🆕 Total new posts added: {total_new_posts}")
        print(f"   ⏱️  Total time: {overall_duration/60:.1f} minutes")
        print(f"   🚀 Average rate: {total_new_posts/overall_duration if overall_duration > 0 else 0:.2f} posts/second")

        if total_new_posts > 0:
            print(f"\n💡 Tips:")
            print(f"   • Run 'python -m src.main --test' to test your regular monitoring")
            print(f"   • Check logs/backfill.log for detailed information")
            print(f"   • Your regular monitoring will now continue from these new posts")

    except KeyboardInterrupt:
        print(f"\n🛑 Backfill interrupted by user")
    except Exception as e:
        print(f"❌ Error during backfill: {e}")
    finally:
        backfill.shutdown()

if __name__ == "__main__":
    main()