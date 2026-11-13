"""Run with a display: xvfb-run -a python3 tests/test_gui_smoke.py"""
import importlib.util
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

PROJECTS = Path(__file__).resolve().parents[1] / "projects"
real_tk = tk.Tk


def short_lived_root():
    root = real_tk()
    root.after(180, root.destroy)
    return root


for path in sorted(PROJECTS.glob("*.py")):
    spec = importlib.util.spec_from_file_location("gui_smoke", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with patch.object(tk, "Tk", side_effect=short_lived_root):
        module.launch()
    print("GUI PASS", path.name)
