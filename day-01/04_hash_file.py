"""Calculate a file SHA-256 digest by reading it in chunks."""
import hashlib
import sys
from pathlib import Path

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 04_hash_file.py <file>")
        return 2

    digest = hashlib.sha256()
    try:
        path = Path(sys.argv[1]).expanduser()
        if not path.is_file():
            print(f"Error: File not found: {path}")
            return 1
        with path.open("rb") as handle:
            while True:
                block = handle.read(65536)
                if not block:
                    break
                digest.update(block)
    
    except (OSError, RuntimeError) as error:
        print(f"Error: Cannot read file: {error}")
        return 1

    print(f"SHA-256: {digest.hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
