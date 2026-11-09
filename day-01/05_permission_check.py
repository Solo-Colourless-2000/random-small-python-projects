"""Check POSIX file permissions and write access for others."""
import stat
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 05_permission_check.py <file>")
        return 2

    try:
        path = Path(sys.argv[1]).expanduser()
        if path.is_symlink():
            print("Error: Symbolic links are not supported.")
            return 1
        if not path.is_file():
            print(f"Error: Regular file not found: {path}")
            return 1
        mode = path.stat().st_mode
    except (OSError, RuntimeError) as error:
        print(f"Error: Cannot check permissions: {error}")
        return 1

    permissions = stat.S_IMODE(mode)
    print(f"Permissions: {permissions:o}")
    if mode & stat.S_IWOTH:
        print("Warning: Others have write permissions.")
    else:
        print("OK: Others do not have write permissions.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
