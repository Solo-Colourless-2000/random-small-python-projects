"""Terminal Score Bars."""
import sys


def main():
    if not 2 <= len(sys.argv) <= 11:
        print("Usage: python3 08_score_bars.py score1 [score2 ...] (up to 10)")
        return 2

    try:
        scores = [int(value) for value in sys.argv[1:]]
    except ValueError:
        print("Error: scores must be integers.")
        return 2
    if any(score < 0 or score > 100 for score in scores):
        print("Error: scores must be 0-100.")
        return 2

    print("Scale: # = 10 points (rounded down)")
    for number, score in enumerate(scores, start=1):
        bar = "#" * (score // 10)
        print(f"{number:02d} | {bar:<10} {score:3d}")
    print(f"Average: {sum(scores) / len(scores):.1f}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
