// The same 7 tests as test_rulebook.py, run against the page's rulebook.js,
// plus a check that the live page enforces exactly this file.
//   node live/rulebook.test.cjs
const assert = require("node:assert/strict");
const { test } = require("node:test");
const { decide } = require("./rulebook.js");

const verdict = (action, spent = 0) => decide(action, spent).verdict;
const people = (n) => Array(n).fill("a@x.com");

test("reads are allowed", () => {
  assert.equal(verdict({ type: "read" }), "allow");
});

test("small refund is allowed", () => {
  assert.equal(verdict({ type: "refund", amount: 40 }), "allow");
});

test("large refund waits for a human", () => {
  assert.equal(verdict({ type: "refund", amount: 100.01 }), "ask");
});

test("spend limit is a hard stop", () => {
  assert.equal(verdict({ type: "purchase", amount: 50 }, 480), "deny");
  assert.equal(verdict({ type: "refund", amount: 150 }, 400), "deny");
});

test("bulk message waits for a human", () => {
  assert.equal(verdict({ type: "send_message", to: people(10) }), "allow");
  assert.equal(verdict({ type: "send_message", to: people(11) }), "ask");
});

test("deletes stay inside the workspace", () => {
  assert.equal(verdict({ type: "delete_file", path: "tmp/old.csv" }), "allow");
  assert.equal(verdict({ type: "delete_file", path: "../shared/customers.db" }), "deny");
  assert.equal(verdict({ type: "delete_file", path: "tmp/../../notes.txt" }), "deny");
  assert.equal(verdict({ type: "delete_file", path: "/etc/hosts" }), "deny");
});

test("unknown actions are denied by default", () => {
  assert.equal(verdict({ type: "update_prices", change: -0.2 }), "deny");
});

test("the live page enforces exactly this rulebook", () => {
  const fs = require("node:fs");
  const path = require("node:path");
  const page = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
  const inline = page.match(/<script id="rulebook-js">([\s\S]*?)<\/script>/);
  assert.ok(inline, "index.html has a <script id=\"rulebook-js\"> block");
  const file = fs.readFileSync(path.join(__dirname, "rulebook.js"), "utf8");
  assert.equal(inline[1].trim(), file.trim(), "the copy in index.html matches rulebook.js");
});
