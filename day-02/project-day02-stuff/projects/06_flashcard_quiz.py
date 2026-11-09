"""Tiny Flashcard Quiz."""
CARDS = [("a red fruit", "apple"), ("something you read", "book"), ("something you drink", "water")]


def main():
    score = 0
    print("Type the English word for each clue.")

    try:
        for number, (question, answer) in enumerate(CARDS, start=1):
            guess = input(f"Q{number} {question}: ").strip().casefold()
            if guess == answer:
                score += 1
                print("Correct!")
            else:
                print(f"Answer: {answer}")

    except (EOFError, KeyboardInterrupt):
        print("\nQuiz stopped.")
        return 1
    print(f"Score: {score} / {len(CARDS)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
