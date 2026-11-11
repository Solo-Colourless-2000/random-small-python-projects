"""Demonstrate an object-level authorization bug with toy identities."""
import sys

ROLES = {"alice": "analyst", "bob": "viewer", "root": "admin"}
DOCS = {
    "report": {"owner": "alice", "scope": "team"},
    "notes": {"owner": "bob", "scope": "private"},
}


def permitted(actor, document, action):
    role = ROLES.get(actor)
    target = DOCS.get(document)
    if role is None or target is None or action not in ("read", "edit"):
        return False
    if role == "admin":
        return True
    if target["owner"] == actor:
        return True
    if action == "read" and role == "analyst" and target["scope"] == "team":
        return True
    return False


def check_access(mode, actor, document, action):
    if mode not in ("safe", "unsafe"):
        raise ValueError("mode must be safe or unsafe")
    if mode == "unsafe":
        # Bug: user existence is checked, but object ownership is ignored.
        return actor in ROLES and document in DOCS and action in ("read", "edit")
    return permitted(actor, document, action)


def main():
    if len(sys.argv) != 5 or sys.argv[1] not in ("unsafe", "safe"):
        print("Usage: python3 08_access_matrix.py unsafe|safe ACTOR DOCUMENT read|edit")
        return 2
    mode, actor, document, action = sys.argv[1:]
    if action not in ("read", "edit"):
        print("Error: action must be read or edit")
        return 2
    allowed = check_access(mode, actor, document, action)
    print(f"{mode} {actor} {action} {document}: {'ALLOW' if allowed else 'DENY'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
