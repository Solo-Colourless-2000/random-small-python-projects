"""Save basic system information as JSON without overwriting existing files."""
import json
import platform
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 09_system_info.py <output_json_file>")
        return 2

    information = {
            "os": platform.system(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            }

    try:
        output = Path(sys.argv[1]).expanduser()
        with output.open("x", encoding="utf-8") as handle:
            json.dump(information, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    except FileExistsError:
        print(f"Error: Refusing to overwrite existing file: {output}")
        return 1
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Error: Cannot write JSON: {error}")
        return 1

    print(f"Saved: {output}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
