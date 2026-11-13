"""Compare hashes of direct child files in a local folder."""
import hashlib
import os
import stat
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

MAX_FILES = 100
MAX_SIZE = 5 * 1024 * 1024


def digest_file(path):
    """Hash a bounded regular file without following a final-component symlink (Linux)."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as handle:
        details = os.fstat(handle.fileno())
        if not stat.S_ISREG(details.st_mode):
            raise ValueError(f"Not a regular file: {Path(path).name}")
        if details.st_size > MAX_SIZE:
            raise ValueError(f"File too large (5 MiB limit): {Path(path).name}")
        sha = hashlib.sha256()
        total = 0
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_SIZE:
                raise ValueError(f"File grew beyond 5 MiB: {Path(path).name}")
            sha.update(chunk)
        # This detects many accidental concurrent edits, but is not an atomic snapshot.
        after = os.fstat(handle.fileno())
        identity = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if total != details.st_size or any(
                getattr(details, key) != getattr(after, key) for key in identity):
            raise ValueError(f"File changed while hashing: {Path(path).name}")
    return sha.hexdigest()


def snapshot(folder):
    """Inspect only direct regular files; do not follow symlinks."""
    root = Path(folder)
    if not root.is_dir():
        raise ValueError("Choose an existing directory.")
    result = {}
    for entry in sorted(root.iterdir()):
        if entry.is_symlink() or not entry.is_file():
            continue
        if len(result) >= MAX_FILES:
            raise ValueError("More than 100 files; choose a smaller directory.")
        result[entry.name] = digest_file(entry)
    return result


def compare(before, after):
    changes = []
    for name in sorted(before.keys() | after.keys()):
        if name not in before:
            state = "ADDED"
        elif name not in after:
            state = "REMOVED"
        elif before[name] != after[name]:
            state = "MODIFIED"
        else:
            state = "UNCHANGED"
        changes.append((name, state))
    return changes


def launch():
    root = tk.Tk()
    root.title("File Integrity Baseline")
    root.geometry("840x560")
    frame = ttk.Frame(root, padding=14)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Compare a local folder before and after changes", font=("Sans", 15, "bold")).pack(anchor="w")
    ttk.Label(frame, text="Only direct files, <= 5 MiB each, no symlinks; baseline lives in memory.").pack(anchor="w")
    selected = tk.StringVar()
    status = tk.StringVar(value="Choose a practice folder and capture a baseline.")
    row = ttk.Frame(frame)
    row.pack(fill="x", pady=12)
    ttk.Entry(row, textvariable=selected).pack(side="left", fill="x", expand=True)
    ttk.Button(row, text="Choose folder", command=lambda: selected.set(
        filedialog.askdirectory() or selected.get())).pack(side="left", padx=8)
    result = ttk.Treeview(frame, columns=("file", "state"), show="headings")
    for name in ("file", "state"):
        result.heading(name, text=name)
        result.column(name, width=260, stretch=True)
    result.pack(fill="both", expand=True)
    ttk.Label(frame, textvariable=status).pack(anchor="w", pady=8)
    baseline = None
    baseline_path = None

    def scan_action(capture):
        nonlocal baseline, baseline_path
        try:
            current_dir = str(Path(selected.get()).resolve(strict=True))
            if not capture and (baseline is None or current_dir != baseline_path):
                raise ValueError("Capture a baseline for this exact folder first.")
            current = snapshot(current_dir)
        except (OSError, ValueError) as error:
            messagebox.showerror("Scan error", str(error))
            return
        if capture:
            baseline = current
            baseline_path = current_dir
            items = [(name, "BASELINE") for name in sorted(current)]
        else:
            items = compare(baseline, current)
        for item_id in result.get_children():
            result.delete(item_id)
        for item in items:
            result.insert("", "end", values=item)
        status.set(f"{len(items)} files/entries shown; all hashes computed with SHA-256.")

    buttons = ttk.Frame(frame)
    buttons.pack(anchor="w", pady=8)
    ttk.Button(buttons, text="Capture baseline", command=lambda: scan_action(True)).pack(side="left", padx=4)
    ttk.Button(buttons, text="Compare now", command=lambda: scan_action(False)).pack(side="left", padx=4)
    root.mainloop()


if __name__ == "__main__":
    launch()
