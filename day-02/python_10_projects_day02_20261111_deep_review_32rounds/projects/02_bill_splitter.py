"""Fair Bill Splitter."""
import sys


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 02_bill_splitter.py total_jpy people")
        return 2

    try:
        total = int(sys.argv[1])
        people = int(sys.argv[2])
    except ValueError:
        print("Error: total and people must be integers.")
        return 2
    if not 0 <= total <= 10000000 or not 1 <= people <= 100:
        print("Error: total must be 0-10000000 JPY; people must be 1-100.")
        return 2

    base, extra = divmod(total, people)
    print(f"People paying {base + 1} JPY: {extra}")
    print(f"People paying {base} JPY: {people - extra}")
    check = (base + 1) * extra + base * (people - extra)
    print(f"Checked total: {check} JPY")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
