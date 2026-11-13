"""Match exact indicators against synthetic local CSV events."""
import csv
import ipaddress
import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

TYPES = ("ip", "domain", "sha256")
MAX_CSV_BYTES = 1024 * 1024
SHA_PATTERN = re.compile(r"[0-9a-fA-F]{64}\Z")
DOMAIN_PATTERN = re.compile(r"(?=.{1,253}\Z)[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\Z")


def normalize(kind, value):
    value = value.strip()
    if kind == "ip":
        if "%" in value:
            raise ValueError("IP scope identifiers are not supported in IOC matching.")
        return str(ipaddress.ip_address(value))
    if kind == "domain":
        if value.endswith(".."):
            raise ValueError("Invalid domain ending.")
        value = (value[:-1] if value.endswith(".") else value).lower()
        if not DOMAIN_PATTERN.fullmatch(value) or any(
                len(label) > 63 for label in value.split(".")) or any(
                label.startswith("-") or label.endswith("-") for label in value.split(".")):
            raise ValueError("Invalid ASCII domain.")
        return value
    if kind == "sha256" and SHA_PATTERN.fullmatch(value):
        return value.lower()
    raise ValueError("Invalid indicator type or value.")


def load_csv(path, fields, max_rows=500):
    result = []
    if Path(path).stat().st_size > MAX_CSV_BYTES:
        raise ValueError("CSV file exceeds the 1 MiB teaching limit.")
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or len(reader.fieldnames) != len(fields) or set(reader.fieldnames) != set(fields):
            raise ValueError("Columns must be exactly: " + ", ".join(fields))
        for row in reader:
            if len(result) >= max_rows:
                raise ValueError("CSV row limit reached.")
            if None in row or any(row.get(field) is None for field in fields):
                raise ValueError("Malformed CSV row.")
            item = {field: row[field].strip() for field in fields}
            if "timestamp" in item and not item["timestamp"]:
                raise ValueError("Event timestamp must not be empty.")
            if "type" in item and not item["value"]:
                raise ValueError("IOC value must not be empty.")
            result.append(item)
    return result


def correlate(indicators, events):
    lookup = {kind: set() for kind in TYPES}
    for item in indicators:
        kind = item["type"].lower()
        if kind not in lookup:
            raise ValueError("Unknown indicator type.")
        lookup[kind].add(normalize(kind, item["value"]))
    matches = []
    for event in events:
        for kind in TYPES:
            value = event[kind]
            if value and normalize(kind, value) in lookup[kind]:
                matches.append((event["timestamp"], kind, value))
    return matches


def launch():
    root = tk.Tk()
    root.title("IOC Exact-Match Console")
    root.geometry("870x550")
    pane = ttk.Frame(root, padding=14)
    pane.pack(fill="both", expand=True)
    ttk.Label(pane, text="IOC correlation on sample CSVs", font=("Sans", 15, "bold")).pack(anchor="w")
    ttk.Label(pane, text="Exact matches only. A match is a lead, not proof of compromise.").pack(anchor="w")
    paths = {name: tk.StringVar() for name in ("indicators", "events")}
    for name in paths:
        row = ttk.Frame(pane)
        row.pack(fill="x", pady=6)
        ttk.Label(row, text=name.capitalize(), width=12).pack(side="left")
        ttk.Entry(row, textvariable=paths[name]).pack(side="left", fill="x", expand=True)

        def browse(key=name):
            selected = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
            if selected:
                paths[key].set(selected)

        ttk.Button(row, text="Browse", command=browse).pack(side="left", padx=6)
    status = tk.StringVar(value="Choose both sample CSV files.")
    grid = ttk.Treeview(pane, columns=("timestamp", "type", "value"), show="headings")
    for column in ("timestamp", "type", "value"):
        grid.heading(column, text=column)
        grid.column(column, width=180, stretch=True)
    grid.pack(fill="both", expand=True, pady=12)
    ttk.Label(pane, textvariable=status).pack(anchor="w")

    def run_match():
        try:
            indicators = load_csv(paths["indicators"].get(), ("type", "value"))
            events = load_csv(paths["events"].get(), ("timestamp",) + TYPES)
            matches = correlate(indicators, events)
        except (OSError, UnicodeError, ValueError, csv.Error) as error:
            messagebox.showerror("Input error", str(error))
            return
        for item_id in grid.get_children():
            grid.delete(item_id)
        for item in matches:
            grid.insert("", "end", values=item)
        status.set(f"{len(matches)} exact matches across {len(events)} events.")

    ttk.Button(pane, text="Correlate", command=run_match).pack(anchor="w")
    root.mainloop()


if __name__ == "__main__":
    launch()
