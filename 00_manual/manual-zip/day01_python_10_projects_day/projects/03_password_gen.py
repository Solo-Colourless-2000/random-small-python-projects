"""Generate a random password using secrets."""
import secrets
import string
import sys


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 03_password_gen.py <length_12_to_128>")
        return 2

    try:
        length = int(sys.argv[1])
    except ValueError:
        print("Error: Length must be an integer.")
        return 2

    if not 12 <= length <= 128:
        print("Error: Length must be between 12 and 128.")
        return 2

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ""
    for _ in range(length):
        password += secrets.choice(alphabet)
    print(password)
    return 0


if __name__ == "__main__":
    sys.exit(main())
