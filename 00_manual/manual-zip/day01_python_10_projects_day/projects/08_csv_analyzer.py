"""Count values in the CSV event column and track malformed rows."""
import csv
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 08_csv_analyzer.py <csv_file>")
        return 2

    counts = {}
    skipped = 0
    malformed = 0
    try:
        path = Path(sys.argv[1]).expanduser()
        if not path.is_file():
            print(f"Error: CSV file not found: {path}")
            return 1

        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            headers = reader.fieldnames
            if headers is None or "event" not in headers:
                print("Error: CSV header must include an event column.")
                return 2
            if len(headers) != len(set(headers)) or any(not name.strip() for name in headers):
                print("Error: CSV header contains duplicate or empty column names.")
                return 2
            for row in reader:
                # Extra columns create a None key; missing columns create None values.
                if None in row or any(value is None for value in row.values()):
                    malformed += 1
                    continue
                event = row["event"].strip()
                if not event:
                    skipped += 1
                    continue
                counts[event] = counts.get(event, 0) + 1
    except (OSError, UnicodeError, ValueError, RuntimeError, csv.Error) as error:
        print(f"Error: Cannot read CSV: {error}")
        return 1

    for event, count in sorted(counts.items()):
        print(f"{event}: {count}")
    print(f"Valid events: {sum(counts.values())}")
    print(f"Empty event rows: {skipped}")
    print(f"Malformed rows: {malformed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
