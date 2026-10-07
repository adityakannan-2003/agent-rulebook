// The same rules as rulebook.py, for the live demo page.
// The agent proposes. The rulebook decides.
(function (root) {
  const WORKSPACE = "/store/agent";   // the agent's own folder
  const DAILY_BUDGET = 500;           // $ the agent may spend per day, hard stop
  const REFUND_NEEDS_HUMAN_OVER = 100; // $ refunds above this wait for a person
  const BULK_RECIPIENTS = 10;         // bigger mailings wait for a person

  // Like Path.resolve(): join onto the workspace, then collapse "." and "..".
  function resolve(path) {
    const full = path.startsWith("/") ? path : WORKSPACE + "/" + path;
    const out = [];
    for (const part of full.split("/")) {
      if (part === "" || part === ".") continue;
      if (part === "..") out.pop();
      else out.push(part);
    }
    return "/" + out.join("/");
  }

  function decide(action, spentToday) {
    const kind = action.type;
    if (kind === "read") {
      return { verdict: "allow", reason: "read-only" };
    }
    if (kind === "send_message") {
      const n = action.to.length;
      if (n > BULK_RECIPIENTS) {
        return { verdict: "ask", reason: `${n.toLocaleString("en-US")} recipients, limit ${BULK_RECIPIENTS}` };
      }
      return { verdict: "allow", reason: `${n} recipient${n > 1 ? "s" : ""}` };
    }
    if (kind === "refund" || kind === "purchase") {
      const total = spentToday + action.amount;
      if (total > DAILY_BUDGET) {
        return { verdict: "deny", reason: `over the $${DAILY_BUDGET} daily budget` };
      }
      if (kind === "refund" && action.amount > REFUND_NEEDS_HUMAN_OVER) {
        return { verdict: "ask", reason: `refund over $${REFUND_NEEDS_HUMAN_OVER}` };
      }
      return { verdict: "allow", reason: `$${total.toFixed(2)} of $${DAILY_BUDGET} spent today` };
    }
    if (kind === "delete_file") {
      const target = resolve(action.path);
      if (!(target === WORKSPACE || target.startsWith(WORKSPACE + "/"))) {
        return { verdict: "deny", reason: "outside the agent's folder" };
      }
      return { verdict: "allow", reason: "inside the agent's folder" };
    }
    return { verdict: "deny", reason: `no rule for '${kind}', so denied by default` };
  }

  const api = { decide, resolve, WORKSPACE, DAILY_BUDGET, REFUND_NEEDS_HUMAN_OVER, BULK_RECIPIENTS };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Rulebook = api;
})(this);
