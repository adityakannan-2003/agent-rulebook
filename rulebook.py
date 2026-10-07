"""The agent proposes. The rulebook decides."""
from dataclasses import dataclass
from pathlib import Path

WORKSPACE = (Path(__file__).parent / "workspace").resolve()  # its own folder
DAILY_BUDGET = 500             # $ the agent may spend per day, hard stop
REFUND_NEEDS_HUMAN_OVER = 100  # $ refunds above this wait for a person
BULK_RECIPIENTS = 10           # bigger mailings wait for a person

@dataclass
class Decision:
    verdict: str  # "allow" | "ask" | "deny"
    reason: str

def decide(action: dict, spent_today: float) -> Decision:
    kind = action["type"]
    if kind == "read":
        return Decision("allow", "read-only")
    if kind == "send_message":
        n = len(action["to"])
        if n > BULK_RECIPIENTS:
            return Decision("ask", f"{n:,} recipients, limit {BULK_RECIPIENTS}")
        return Decision("allow", f"{n} recipient{'s' if n > 1 else ''}")
    if kind in ("refund", "purchase"):
        total = spent_today + action["amount"]
        if total > DAILY_BUDGET:
            return Decision("deny", f"over the ${DAILY_BUDGET} daily budget")
        if kind == "refund" and action["amount"] > REFUND_NEEDS_HUMAN_OVER:
            return Decision("ask", f"refund over ${REFUND_NEEDS_HUMAN_OVER}")
        return Decision("allow", f"${total:.2f} of ${DAILY_BUDGET} spent today")
    if kind == "delete_file":
        target = (WORKSPACE / action["path"]).resolve()
        if not target.is_relative_to(WORKSPACE):
            return Decision("deny", "outside the agent's folder")
        return Decision("allow", "inside the agent's folder")
    return Decision("deny", f"no rule for '{kind}', so denied by default")
