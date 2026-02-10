#!/usr/bin/env python
"""
Run the Semantic Data Discovery Streamlit Demo

Usage:
    python run_demo.py

Or directly:
    streamlit run app/streamlit_app.py
"""

import subprocess
import sys


def main():
    """Launch the Streamlit demo application."""
    print("=" * 60)
    print("  Semantic Data Discovery Platform")
    print("  Natural Language to SQL Translation Demo")
    print("=" * 60)
    print()
    print("Starting Streamlit server...")
    print("The browser will open automatically.")
    print()
    print("Press Ctrl+C to stop the server.")
    print("=" * 60)

    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "app/streamlit_app.py"],
            check=True
        )
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except subprocess.CalledProcessError as e:
        print(f"\nError starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
