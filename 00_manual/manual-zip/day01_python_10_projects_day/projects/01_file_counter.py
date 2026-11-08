"""Count regular files directly inside a directory by extension."""
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 01_file_counter.py <directory>")
        return 2

    try:
        folder = Path(sys.argv[1]).expanduser()
        if not folder.is_dir():
            print(f"Error: Directory not found: {folder}")
            return 1
    except (OSError, RuntimeError) as error:
        print(f"Error: Cannot check directory: {error}")
        return 1

    counts = {}
    try:
        for item in folder.iterdir():
            if item.is_symlink() or not item.is_file():
                continue
            extension = item.suffix.lower() or "(no extension)"
            counts[extension] = counts.get(extension, 0) + 1
    except OSError as error:
        print(f"Error: Cannot scan directory: {error}")
        return 1

    for extension, count in sorted(counts.items()):
        print(f"{extension}: {count}")
    print(f"Total files: {sum(counts.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
