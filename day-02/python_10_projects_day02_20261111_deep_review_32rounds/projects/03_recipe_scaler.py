"""Recipe Scaler."""
import sys

BASE_SERVINGS = 2
INGREDIENTS = {"rice": 150, "water": 200, "carrot": 60}


def main():

    if len(sys.argv) != 2:
        print("Usage: python3 03_recipe_scaler.py servings")
        return 2
    try:
        servings = int(sys.argv[1])
    except ValueError:
        print("Error: servings must be an integer.")
        return 2
    if not 1 <= servings <= 20:
        print("Error: servings must be 1-20.")
        return 2

    ratio = servings / BASE_SERVINGS
    print(f"Servings: {servings} / Scale: {ratio:.2f}")
    for name, grams in INGREDIENTS.items():
        scaled = grams * ratio
        print(f"{name}: {scaled:.1f} g")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
