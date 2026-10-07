"""One night of an always-on support agent, with every action checked by the rulebook.

The agent's proposed actions are scripted so the demo runs offline and gives the
same result every time. With a real agent, call decide() in your tool layer,
before any tool runs, exactly the way run_night() does below.

    python3 night_shift.py          # coloured log
    python3 night_shift.py --json   # machine-readable log
"""
import json
import sys

from rulebook import decide

NIGHT = [
    ("23:04", "Read the open ticket queue (37 tickets)", {"type": "read"}),
    ("23:06", "Tell a customer order #1182 has shipped", {"type": "send_message", "to": ["dana@example.com"]}),
    ("23:19", "Refund $24.99 for a damaged mug, order #1175", {"type": "refund", "amount": 24.99}),
    ("23:47", "Refund $189.00 for a lost package, order #1169", {"type": "refund", "amount": 189.00}),
    ("00:31", "Delete an old export: tmp/export-0921.csv", {"type": "delete_file", "path": "tmp/export-0921.csv"}),
    ("01:15", "Email every customer about holiday shipping delays",
     {"type": "send_message", "to": [f"customer{i}@example.com" for i in range(2340)]}),
    ("02:02", "Reorder packaging supplies, $420.00", {"type": "purchase", "amount": 420.00}),
    ("03:40", "Refund $79.00 for a wrong size, order #1191", {"type": "refund", "amount": 79.00}),
    ("04:12", "Free up space: delete ../shared/customers.db", {"type": "delete_file", "path": "../shared/customers.db"}),
    ("05:30", "Put every product on 20% off to clear stock", {"type": "update_prices", "change": -0.20}),
    ("06:00", "Send the owner a morning summary", {"type": "send_message", "to": ["owner@example.com"]}),
]


def run_night():
    spent, log = 0.0, []
    for time, summary, action in NIGHT:
        decision = decide(action, spent)
        if decision.verdict == "allow" and action["type"] in ("refund", "purchase"):
            spent += action["amount"]  # only money that actually moved counts
        log.append({"time": time, "action": summary, "verdict": decision.verdict, "reason": decision.reason})
    return log


LABEL = {"allow": ("\033[32m", "✓ DONE   "), "ask": ("\033[33m", "? WAITING"), "deny": ("\033[31m", "✕ BLOCKED")}
DIM, RESET = "\033[2m", "\033[0m"


def print_log(log):
    print(f"\n  Night shift · always-on support agent · checked by rulebook.py\n  {'─' * 92}")
    for e in log:
        colour, label = LABEL[e["verdict"]]
        print(f"  {DIM}{e['time']}{RESET}  {colour}{label}{RESET}  {e['action']:<52} {DIM}{e['reason']}{RESET}")
    counts = {v: sum(e["verdict"] == v for e in log) for v in LABEL}
    print(f"  {'─' * 92}\n  {len(log)} actions · {counts['allow']} done · "
          f"{counts['ask']} waiting for you · {counts['deny']} blocked\n")
    waiting = [e for e in log if e["verdict"] == "ask"]
    if waiting:
        print("  Waiting for you this morning:")
        for e in waiting:
            print(f"    • {e['action']}  {DIM}· {e['reason']}{RESET}")
        print()


if __name__ == "__main__":
    log = run_night()
    print(json.dumps(log, indent=2)) if "--json" in sys.argv else print_log(log)
