"""Review a simplified firewall-rule CSV. No network changes are made."""
import csv
import ipaddress
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

FIELDS = ("protocol", "port", "source", "action")
INTERESTING_PORTS = {22, 3389, 3306, 5432, 6379}
MAX_CSV_BYTES = 1024 * 1024


def read_rules(path):
    rules = []
    if Path(path).stat().st_size > MAX_CSV_BYTES:
        raise ValueError("CSV file exceeds the 1 MiB teaching limit.")
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or len(reader.fieldnames) != len(FIELDS) or set(reader.fieldnames) != set(FIELDS):
            raise ValueError("Expected: protocol,port,source,action")
        for row in reader:
            if len(rules) >= 300:
                raise ValueError("Limit: 300 rules.")
            if None in row or any(row.get(field) is None for field in FIELDS):
                raise ValueError("Broken CSV row.")
            rule = {field: row[field].strip() for field in FIELDS}
            rule["protocol"] = rule["protocol"].upper()
            rule["action"] = rule["action"].upper()
            if rule["protocol"] not in {"TCP", "UDP"}:
                raise ValueError("Protocol must be TCP or UDP.")
            if rule["action"] not in {"ALLOW", "DENY"}:
                raise ValueError("Action must be ALLOW or DENY.")
            if rule["port"].lower() != "any":
                if (len(rule["port"]) > 5 or not rule["port"].isascii()
                        or not rule["port"].isdecimal()
                        or not 1 <= int(rule["port"]) <= 65535):
                    raise ValueError("Port must be ASCII digits 1..65535 or any.")
            try:
                rule["source"] = str(ipaddress.ip_network(rule["source"], strict=True))
            except ValueError as error:
                raise ValueError("Invalid source network (CIDR host bits must be zero).") from error
            rules.append(rule)
    return rules


def assess(rule):
    """A heuristic: upstream routing and rule order are not represented."""
    network = ipaddress.ip_network(rule["source"])
    world = network.prefixlen == 0
    if rule["action"] != "ALLOW":
        return "DENY rule"
    if world and (rule["port"].lower() == "any" or
                  int(rule["port"]) in INTERESTING_PORTS):
        return "REVIEW: broad sensitive access"
    if world:
        return "REVIEW: broad source"
    return "Scoped source (check context)"


def launch():
    root = tk.Tk()
    root.title("Firewall Rule Review Board")
    root.geometry("950x540")
    pane = ttk.Frame(root, padding=14)
    pane.pack(fill="both", expand=True)
    ttk.Label(pane, text="Simplified firewall rule review", font=("Sans", 15, "bold")).pack(anchor="w")
    ttk.Label(pane, text="Informational review only; does not prove internet reachability.").pack(anchor="w")
    result = tk.StringVar(value="Open rules.csv.")
    headers = FIELDS + ("assessment",)
    grid_frame = ttk.Frame(pane)
    grid_frame.pack(fill="both", expand=True, pady=12)
    grid = ttk.Treeview(grid_frame, columns=headers, show="headings")
    for name in headers:
        grid.heading(name, text=name)
        grid.column(name, width=150, stretch=True)
    grid.pack(side="left", fill="both", expand=True)
    scrollbar = ttk.Scrollbar(grid_frame, orient="vertical", command=grid.yview)
    grid.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    ttk.Label(pane, textvariable=result).pack(anchor="w")

    def open_rules():
        filename = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not filename:
            return
        try:
            rules = read_rules(filename)
            evaluations = [assess(rule) for rule in rules]
        except (OSError, UnicodeError, ValueError, csv.Error) as error:
            messagebox.showerror("CSV error", str(error))
            return
        for item_id in grid.get_children():
            grid.delete(item_id)
        for rule, evaluation in zip(rules, evaluations):
            grid.insert("", "end", values=tuple(rule[field] for field in FIELDS) + (evaluation,))
        result.set(f"{len(rules)} rules / {sum(x.startswith('REVIEW') for x in evaluations)} review candidates")

    ttk.Button(pane, text="Open rule CSV", command=open_rules).pack(anchor="w")
    root.mainloop()


if __name__ == "__main__":
    launch()
