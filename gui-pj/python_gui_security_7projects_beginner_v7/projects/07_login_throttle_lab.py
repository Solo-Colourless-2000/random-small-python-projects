"""Simulate one account's failed-login throttling in a local GUI."""
import tkinter as tk
from tkinter import ttk

WINDOW = 60
LIMIT = 3
LOCK_TIME = 30


class Throttle:
    """Small teaching model: not suitable for production authentication."""

    def __init__(self):
        self.now = 0
        self.fail_times = []
        self.lock_until = 0

    def advance(self, seconds):
        if type(seconds) is not int or seconds < 0:
            raise ValueError("Time advance must be a nonnegative integer.")
        self.now += seconds
        if self.lock_until and self.now >= self.lock_until:
            self.lock_until = 0
            self.fail_times.clear()
        self.fail_times = [t for t in self.fail_times if self.now - t < WINDOW]
        return f"Clock advanced to t={self.now}s."

    def attempt(self, outcome):
        if outcome not in {"FAIL", "SUCCESS"}:
            raise ValueError("Outcome must be FAIL or SUCCESS.")
        if self.now < self.lock_until:
            return f"BLOCKED until t={self.lock_until}s."
        if self.lock_until and self.now >= self.lock_until:
            self.lock_until = 0
            self.fail_times.clear()
        self.fail_times = [t for t in self.fail_times if self.now - t < WINDOW]
        if outcome == "SUCCESS":
            self.fail_times.clear()
            return "Allowed: simulated success; failure history reset."
        self.fail_times.append(self.now)
        if len(self.fail_times) >= LIMIT:
            self.lock_until = self.now + LOCK_TIME
            return f"LOCKED: {len(self.fail_times)} failures in {WINDOW}s."
        return f"Recorded failure ({len(self.fail_times)} of {LIMIT})."


def launch():
    root = tk.Tk()
    root.title("Login Throttle Simulation")
    root.geometry("820x570")
    frame = ttk.Frame(root, padding=14)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Rate limiting / account lockout simulation", font=("Sans", 15, "bold")).pack(anchor="w")
    ttk.Label(frame, text="No accounts, passwords, servers, or network traffic are used.").pack(anchor="w")
    model = Throttle()
    clock = tk.StringVar(value="t=0s; 0 failures; not locked")
    ttk.Label(frame, textvariable=clock).pack(anchor="w", pady=8)
    history = tk.Text(frame, wrap="word", height=10, state="disabled")
    history.pack(fill="both", expand=True, pady=8)

    def display(text):
        lock_info = (f"LOCKED until t={model.lock_until}s"
                     if model.lock_until else "not locked")
        clock.set(f"t={model.now}s; {len(model.fail_times)} recorded failures; {lock_info}")
        history.configure(state="normal")
        history.insert("end", f"t={model.now}: {text}\n")
        history.see("end")
        history.configure(state="disabled")

    controls = ttk.Frame(frame)
    controls.pack(fill="x")
    ttk.Button(controls, text="Simulate FAIL", command=lambda: display(model.attempt("FAIL"))).pack(side="left", padx=3)
    ttk.Button(controls, text="Simulate SUCCESS", command=lambda: display(model.attempt("SUCCESS"))).pack(side="left", padx=3)
    ttk.Button(controls, text="Advance +10s", command=lambda: display(model.advance(10))).pack(side="left", padx=3)

    def reset():
        nonlocal model
        model = Throttle()
        history.configure(state="normal")
        history.delete("1.0", "end")
        history.configure(state="disabled")
        display("Simulation reset.")

    ttk.Button(controls, text="Reset", command=reset).pack(side="left", padx=3)
    display("Simulation ready.")
    root.mainloop()


if __name__ == "__main__":
    launch()
