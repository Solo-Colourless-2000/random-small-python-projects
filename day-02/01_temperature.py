"""Temperature Converter."""
import math


def main():

    try:
        celsius = float(input("Temperature in Celsius: "))
    except (EOFError, KeyboardInterrupt):
        print("\nConversion stopped.")
        return 1
    except ValueError:
        print("Error: enter a number.")
        return 2

    if not math.isfinite(celsius) or not -100 <= celsius <= 100:
        print("Error: enter a finite number from -100 to 100.")
        return 2
    fahrenheit = celsius * 9 / 5 + 32
    print(f"Fahrenheit: {fahrenheit:.1f} F")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
