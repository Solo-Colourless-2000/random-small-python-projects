"""Coordinate Treasure Hunt."""
TREASURE = (4, 2)


def main():
    target_x, target_y = TREASURE
    attempts = 0
    print("Treasure hunt: x increases east, y increases north. Range: 1-5. Guesses: 5.")

    while attempts < 5:
        try:
            x_text, y_text = input("Guess x y: ").split()
            x, y = int(x_text), int(y_text)
        except (EOFError, KeyboardInterrupt):
            print("\nGame stopped.")
            return 1
        except ValueError:
            print("Error: enter two integers separated by a space.")
            continue
        if not (1 <= x <= 5 and 1 <= y <= 5):
            print("Error: both coordinates must be 1-5.")
            continue

        attempts += 1
        if (x, y) == TREASURE:
            print(f"Found it! Guesses used: {attempts}.")
            return 0
        horizontal = "east" if x < target_x else "west" if x > target_x else "same x"
        vertical = "north" if y < target_y else "south" if y > target_y else "same y"
        print(f"Hint: {horizontal} / {vertical}. Guesses left: {5 - attempts}")
    print(f"Game over. The treasure was at {TREASURE}.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
