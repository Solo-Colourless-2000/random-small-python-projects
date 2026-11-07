"""Print matching lines from a UTF-8 log with their line numbers."""
import sys
from pathlib import Path

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 02_log_finder.py <log_file> <keyword>")
        return 2

    keyword = sys.argv[2]
    if not keyword:
        print("Error: keyword must not be empty.")
        return 2

    matches = 0
    try:
        path = Path(sys.argv[1]).expanduser()
        if not path.is_file():
            print(f"Error: File not found: {Path}")
            return 1
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if keyword in line:
