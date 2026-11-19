"""Parse an HTTP/HTTPS URL without making network requests."""
import sys
from urllib.parse import urlsplit


def main():
    if len(sys.argv) != 2:
        print('Usage: python3 07_url_analyzer.py "https://example.com/path?q=1"')
        return 2

    try:
        parts = urlsplit(sys.argv[1])
        hostname = parts.hostname
        port = parts.port
    except ValueError as error:
        print(f"Error: Invalid URL: {error}")
        return 2

    if parts.scheme not in ("http", "https") or not hostname:
        print("Error: Specify a URL starting with http:// or https://.")
        return 2

    print(f"Scheme: {parts.scheme}")
    print(f"Hostname: {hostname}")
    print(f"Port: {port if port is not None else '(not specified)'}")
    print(f"Path: {parts.path or '/'}")
    print(f"Query: {parts.query or '(none)'}")
    print(f"Fragment: {parts.fragment or '(none)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
