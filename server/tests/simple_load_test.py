#!/usr/bin/env python3
"""
Simple load testing script - repeatedly sends events to the API.
Run with: python simple_load_test.py [num_events]
Example: python simple_load_test.py 50
"""

import requests
import time
import json
import sys
from datetime import datetime
from uuid import uuid4
from random import choice, randint


def generate_event():
    """Generate a random event for testing."""
    event_types = ["click", "pageview", "conversion", "scroll", "hover"]
    urls = [
        "http://example.com/home",
        "http://example.com/products",
        "http://example.com/checkout",
        "http://example.com/profile"
    ]

    return {
        "type": choice(event_types),
        "timestamp": datetime.now().isoformat(),
        "user_id": str(uuid4()),
        "source_url": choice(urls),
        "metadata": {
            "browser": choice(["chrome", "firefox", "safari"]),
            "device": choice(["desktop", "mobile", "tablet"]),
            "session_id": str(uuid4())
        }
    }


def send_events(num_events: int):
    """Send multiple events to the API."""
    base_url = "http://localhost:8000"

    print(f"Sending {num_events} events to {base_url}/events...")

    successful = 0
    failed = 0

    for i in range(num_events):
        event = generate_event()

        try:
            response = requests.post(
                f"{base_url}/events", json=event, timeout=5)

            if response.status_code == 200:
                result = response.json()
                job_id = result.get("job_id", "unknown")
                print(f"✅ Event {i+1}: {event['type']} -> Job {job_id}")
                successful += 1
            else:
                print(f"❌ Event {i+1}: HTTP {response.status_code}")
                failed += 1

        except Exception as e:
            print(f"❌ Event {i+1}: Error - {e}")
            failed += 1

        # Small delay between requests
        time.sleep(0.05)

    print(f"\n📊 Results: {successful} successful, {failed} failed")
    return successful, failed


if __name__ == "__main__":
    # Parse command line arguments
    n = 20  # default

    if len(sys.argv) > 1:
        try:
            n = int(sys.argv[1])
        except ValueError:
            print("❌ Error: Number of events must be an integer")
            print("Usage: python simple_load_test.py [num_events]")
            print("Example: python simple_load_test.py 50")
            sys.exit(1)

    if n <= 0:
        print("❌ Error: Number of events must be greater than 0")
        sys.exit(1)

    # Send events
    send_events(n)

    print("\n🔍 Check the RQ dashboard at http://localhost:9181 to see job processing!")
