#!/usr/bin/env python3
"""Example script to demonstrate the Reddit Samsung Monitor."""

import sys
import os
sys.path.append(os.path.dirname(__file__))

def main():
    print("Reddit Samsung Monitor - Example Usage")
    print("=" * 50)

    print("\n1. Setup Instructions:")
    print("   - Edit .env file with your PostgreSQL password")
    print("   - Database connection: psql -h localhost -U adgear -p 6432 metadataservice")

    print("\n2. Running the application:")
    print("   a) Test mode (single fetch):")
    print("      python -m src.main --test")
    print("   b) Continuous monitoring:")
    print("      python -m src.main")

    print("\n3. Features:")
    print("   ✓ Monitors r/samsung subreddit for new posts")
    print("   ✓ Stores posts in PostgreSQL database")
    print("   ✓ Prevents duplicate posts with unique constraints")
    print("   ✓ Configurable polling intervals")
    print("   ✓ Comprehensive logging")
    print("   ✓ Graceful shutdown with Ctrl+C")

    print("\n4. Database Schema:")
    print("   Table: samsung_posts")
    print("   Columns: post_id, title, author, created_utc, score,")
    print("            num_comments, url, selftext, permalink,")
    print("            subreddit, retrieved_at")

    print("\n5. Configuration (via .env file):")
    print("   - DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT")
    print("   - POLL_INTERVAL (seconds)")
    print("   - LOG_LEVEL")

    print("\n6. Example Database Query:")
    print("   SELECT post_id, title, author, score")
    print("   FROM samsung_posts")
    print("   ORDER BY created_utc DESC")
    print("   LIMIT 10;")

    print("\nProject structure created successfully!")
    print("Ready to monitor Samsung subreddit posts!")

    return 0

if __name__ == "__main__":
    sys.exit(main())