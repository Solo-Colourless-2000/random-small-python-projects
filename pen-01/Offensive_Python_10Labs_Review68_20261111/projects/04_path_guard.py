"""Compare a toy traversal bug with a guarded local file reader."""
import sys
from pathlib import Path
from urllib.parse import unquote

SAMPLES = Path(__file__).resolve().parent.parent / "samples"
ROOT = SAMPLES / "webroot"


def choose(root, user_path, mode):
    if mode not in ("safe", "unsafe"):
        raise ValueError("mode must be safe or unsafe")
    decoded = unquote(user_path, errors="strict")
    if not decoded or "\x00" in decoded or Path(decoded).is_absolute():
        raise ValueError("invalid relative path")
    base = root.resolve(strict=True)
    target = (base / decoded).resolve(strict=True)
    # Even the unsafe demonstration may only read bundled lab samples.
    if not target.is_relative_to(SAMPLES.resolve(strict=True)):
        raise ValueError("outside lab samples")
    if mode == "safe" and not target.is_relative_to(base):
        raise ValueError("path escapes webroot")
    if not target.is_file() or target.stat().st_size > 4096:
        raise ValueError("not a small regular file")
    return target


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("unsafe", "safe"):
        print("Usage: python3 04_path_guard.py unsafe|safe relative_file")
        return 2
    try:
        target = choose(ROOT, sys.argv[2], sys.argv[1])
        print(target.read_text(encoding="utf-8"), end="")
    except (ValueError, OSError, UnicodeError) as exc:
        print(f"Blocked or unavailable: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
