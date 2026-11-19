"""Text Line Wrapper."""
import sys
import textwrap


def main():
    if len(sys.argv) != 3:
        print('Usage: python3 07_text_wrapper.py width "text"')
        return 2
    
    try:
        width = int(sys.argv[1])
    except ValueError:
        print("Error: width must be an integer.")
        return 2
    text = sys.argv[2].strip()
    if not 5 <= width <= 80 or not text or len(text) > 2000:
        print("Error: width must be 5-80; text must contain 1-2000 characters.")
        return 2

    result = textwrap.fill(text, width=width, break_long_words=True, break_on_hyphens=False)
    print(result)
    print(f"Lines: {len(result.splitlines())}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())