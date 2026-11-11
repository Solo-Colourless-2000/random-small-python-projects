"""Run the offline tests in small, reproducible batches."""
import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("test_all.py")
spec = importlib.util.spec_from_file_location("offline_tests", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
GROUPS = {"1": ("01", "02", "03"), "2": ("04", "05", "06"),
          "3": ("07", "08"), "4": ("09", "10")}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in GROUPS:
        print("Usage: python3 tests/run_groups.py 1|2|3|4")
        return 2
    subset = GROUPS[sys.argv[1]]
    tests = unittest.TestSuite()
    for name in unittest.defaultTestLoader.getTestCaseNames(module.LearningTools):
        if name == "test_inventory" and sys.argv[1] == "1" or name.startswith(tuple(f"test_{item}_" for item in subset)):
            tests.addTest(module.LearningTools(name))
    print(f"TEST_GROUP={sys.argv[1]} TEST_METHODS={tests.countTestCases()}", flush=True)
    outcome = unittest.TextTestRunner(verbosity=1).run(tests)
    return 0 if outcome.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
