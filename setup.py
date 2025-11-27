#!/usr/bin/env python3
"""Setup script for Reddit Samsung Monitor."""

import subprocess
import sys
from pathlib import Path


def install_requirements():
    """Install required packages."""
    print("Installing required packages...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✓ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install requirements: {e}")
        return False


def create_env_file():
    """Create .env file if it doesn't exist."""
    env_file = Path('.env')
    if env_file.exists():
        print("✓ .env file already exists")
        return True

    try:
        # Copy from example
        example_file = Path('.env.example')
        if example_file.exists():
            env_content = example_file.read_text()
            env_file.write_text(env_content)
            print("✓ Created .env file from .env.example")
            print("  Please edit .env with your database password")
        else:
            print("✗ .env.example not found")
            return False
        return True
    except Exception as e:
        print(f"✗ Failed to create .env file: {e}")
        return False


def test_database_connection():
    """Test database connection."""
    print("Testing database connection...")
    try:
        from src.database import Database
        from src.config import load_environment
        from src.models import Config

        load_environment()
        config = Config.from_env()

        db = Database(
            host=config.db_host,
            user=config.db_user,
            password=config.db_password,
            database=config.db_name,
            port=config.db_port
        )

        if db.connect():
            print("✓ Database connection successful")
            db.disconnect()
            return True
        else:
            print("✗ Database connection failed")
            return False

    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False


def main():
    """Main setup function."""
    print("Reddit Samsung Monitor - Setup")
    print("=" * 40)

    success = True

    # Install requirements
    if not install_requirements():
        success = False

    # Create .env file
    if not create_env_file():
        success = False

    # Test database (optional, may fail if password not set)
    print("\nOptional: Testing database connection...")
    test_database_connection()

    print("\n" + "=" * 40)
    if success:
        print("✓ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Edit .env file with your database password")
        print("2. Run: python -m src.main --test")
        print("3. If test passes, run: python -m src.main")
    else:
        print("✗ Setup encountered some issues")
        print("Please resolve the issues above and try again")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())