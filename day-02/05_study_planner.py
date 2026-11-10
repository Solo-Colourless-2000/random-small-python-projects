"""Study Block Planner."""
import sys
from datetime import datetime, timedelta


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 05_study_planner.py HH:MM sets")
        return 2
