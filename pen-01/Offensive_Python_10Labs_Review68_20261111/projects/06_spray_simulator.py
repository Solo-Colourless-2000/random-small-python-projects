"""Run a small offline password-spraying simulation on fake accounts."""
import sys

# No network, external usernames, or real credentials are used.
ACCOUNTS = {
    "alice": "BlueFish7",
    "bob": "PaperSun9",
    "carol": "BlueFish7",
    "dave": "CopperKey5",
}
GUESS = "BlueFish7"
LIMIT = 2


def try_password(user, guess):
    return ACCOUNTS.get(user) == guess


def simulate(mode):
    if mode not in ("protected", "unprotected"):
        raise ValueError("mode must be protected or unprotected")
    attempts = 0
    successes = []
    for user in ACCOUNTS:
        if mode == "protected" and attempts >= LIMIT:
            print(f"BLOCKED {user}: lab-wide attempt cap")
            continue
        attempts += 1
        match = try_password(user, GUESS)
        print(f"ATTEMPT {user}: {'MATCH' if match else 'NO MATCH'}")
        if match:
            successes.append(user)
    print(f"Attempts: {attempts}")
    print("Matched fake accounts: " + (", ".join(successes) or "(none)"))
    return attempts, successes


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("unprotected", "protected"):
        print("Usage: python3 06_spray_simulator.py unprotected|protected")
        return 2
    simulate(sys.argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
