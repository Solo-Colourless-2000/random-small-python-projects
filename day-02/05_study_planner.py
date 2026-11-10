"""Study Block Planner."""
import sys
from datetime import datetime, timedelta


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 05_study_planner.py HH:MM sets")
        return 2

    try:
        current = datetime.strptime(sys.argv[1], "%H:%M")
        sets = int(sys.argv[2])
        if current.strftime("%H:%M") != sys.argv[1] or not 1 <= sets <= 8:
            raise ValueError("input range")
    except ValueError:
        print("Error: time must be 00:00-23:59; sets must be 1-8.")
        return 2
    first_day = current.date()

    for number in range(1, sets + 1):
        end = current + timedelta(minutes=25)
        print(f"Study {number}: {current:%H:%M} -> {end:%H:%M}")
        current = end
        if number < sets:
            end = current + timedelta(minutes=5)
            print(f"Break: {current:%H:%M} -> {end:%H:%M}")
            current = end
    suffix = " (next day)" if current.date() != first_day else ""
    print(f"Finish: {current:%H:%M}{suffix}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
