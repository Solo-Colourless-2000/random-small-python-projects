"""Date Countdown."""
import sys
from datetime import date


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 04_date_countdown.py start_date target_date")
        return 2

    try:
        start = date.fromisoformat(sys.argv[1])
        target = date.fromisoformat(sys.argv[2])
        if start.isoformat() != sys.argv[1] or target.isoformat() != sys.argv[2]:
            raise ValueError("date format")
    except ValueError:
        print("Error: use valid dates in YYYY-MM-DD format.")
        return 2

    days = (target - start).days
    if days > 0:
        print(f"Days remaining: {days}")
    elif days == 0:
        print("The event is on the reference date.")
    else:
        print(f"Days since event: {-days}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
