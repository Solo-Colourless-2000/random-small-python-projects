"""Inspect a small local CSV of authentication events."""
import csv
import ipaddress
import tkinter as tk
from collections import Counter
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

COLUMNS = ("timestamp", "username", "ip", "status")
VALID_STATUSES = {"FAIL", "SUCCESS"}
MAX_ROWS = 1000
MAX_CSV_BYTES = 1024 * 1024


def read_events(path):
    """Read bounded CSV data. Return validated event dictionaries."""
    events = []
    if Path(path).stat().st_size > MAX_CSV_BYTES:
        raise ValueError("CSV file exceeds the 1 MiB teaching limit.")
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or len(reader.fieldnames) != len(COLUMNS) or set(reader.fieldnames) != set(COLUMNS):
            raise ValueError("Expected columns: " + ", ".join(COLUMNS))
        for row in reader:
            if len(events) >= MAX_ROWS:
                raise ValueError("Too many events (limit: 1000).")
            if None in row or any(row.get(key) is None for key in COLUMNS):
                raise ValueError("Broken CSV row.")
            item = {key: row[key].strip() for key in COLUMNS}
            if not item["timestamp"] or not item["username"]:
                raise ValueError("Empty timestamp or username.")
            try:
                item["ip"] = str(ipaddress.ip_address(item["ip"]))
            except ValueError as error:
                raise ValueError("Invalid IP address in CSV.") from error
            if item["status"] not in VALID_STATUSES:
                raise ValueError("Status must be FAIL or SUCCESS.")
            events.append(item)
    return events


def summarize(events, filter_text=""):
    """Show per-IP failure counts in the complete dataset."""
    failures = Counter(item["ip"] for item in events if item["status"] == "FAIL")
    term = filter_text.casefold().strip()
    visible = [item for item in events if term in item["username"].casefold()
               or term in item["ip"].casefold()]
    return visible, failures


def launch():
    root = tk.Tk()
    root.title("Auth Log Triage Board")
    root.geometry("900x540")
    events = []
    search = tk.StringVar()
    summary = tk.StringVar(value="Open a sample CSV to begin.")
    frame = ttk.Frame(root, padding=14)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Local authentication event triage", font=("Sans", 15, "bold")).pack(anchor="w")
    ttk.Label(frame, text="3 or more FAIL events per IP are review candidates, not proof.").pack(anchor="w")
    controls = ttk.Frame(frame)
    controls.pack(fill="x", pady=10)
    ttk.Label(controls, text="Filter user or IP:").pack(side="left")
    entry = ttk.Entry(controls, textvariable=search)
    entry.pack(side="left", fill="x", expand=True, padx=8)
    table_frame = ttk.Frame(frame)
    table_frame.pack(fill="both", expand=True)
    table = ttk.Treeview(table_frame, columns=COLUMNS + ("review",), show="headings")
    for name in COLUMNS + ("review",):
        table.heading(name, text=name)
        table.column(name, width=130, stretch=True)
    scroll = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=scroll.set)
    table.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    ttk.Label(frame, textvariable=summary, wraplength=850).pack(anchor="w", pady=8)

    def refresh(*_args):
        visible, fails = summarize(events, search.get())
        for item_id in table.get_children():
            table.delete(item_id)
        for item in visible:
            flag = "REVIEW" if fails[item["ip"]] >= 3 else "-"
            table.insert("", "end", values=tuple(item[key] for key in COLUMNS) + (flag,))
        summary.set(f"{len(visible)} shown / {len(events)} total; "
                    f"{sum(count >= 3 for count in fails.values())} IPs with 3+ FAIL events")

    def open_file():
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("All", "*")])
        if not path:
            return
        try:
            loaded = read_events(path)
        except (OSError, UnicodeError, ValueError, csv.Error) as error:
            messagebox.showerror("CSV error", str(error))
            return
        events.clear()
        events.extend(loaded)
        refresh()

    ttk.Button(controls, text="Open CSV", command=open_file).pack(side="left")
    search.trace_add("write", refresh)
    root.mainloop()


if __name__ == "__main__":
    launch()
