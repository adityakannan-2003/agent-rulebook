"""Tests for local_agent.py, without needing Ollama: a scripted stand-in model, and a fake Ollama server."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

import local_agent
from local_agent import OllamaError, Shop, TICKETS, _clean, inbox_prompt, make_chat, run_conversation, run_night
from rulebook import WORKSPACE


def call(name, **arguments):
    return {"function": {"name": name, "arguments": arguments}}


class ScriptedModel:
    """Plays back replies in Ollama's /api/chat message shape and records what it was sent."""

    def __init__(self, replies):
        self.replies, self.sent = list(replies), []

    def __call__(self, messages, tools):
        self.sent.append([dict(m) for m in messages])
        return self.replies.pop(0)


class AgentLoopTest(unittest.TestCase):
    def setUp(self):
        self.lines = []
        self.shop = Shop(out=self.lines.append)

    def test_every_tool_call_goes_through_the_rulebook(self):
        model = ScriptedModel([
            {"content": "", "tool_calls": [
                call("refund", order_id="1175", amount=24.99, reason="cracked"),
                call("refund", order_id="#1169", amount=189, reason="lost"),
                call("purchase", item="boxes", amount=420),
            ]},
            {"content": "", "tool_calls": [
                call("refund", order_id="1191", amount=79, reason="return"),
                call("send_message", to=["ALL_CUSTOMERS"], subject="Delays", body="..."),
                call("delete_file", path="../shared/customers.db"),
                call("update_prices", percent_change=-20),
            ]},
            {"content": "<think>done?</think>Morning! Two things need you."},
        ])
        note, messages = run_conversation(model, self.shop, inbox_prompt(), max_rounds=24)

        self.assertEqual([e["verdict"] for e in self.shop.log],
                         ["allow", "ask", "allow", "deny", "ask", "deny", "deny"])
        self.assertEqual(note, "Morning! Two things need you.")
        self.assertAlmostEqual(self.shop.spent, 444.99)
        self.assertEqual([a["label"] for a in self.shop.approvals],
                         ["Refund $189.00 on order #1169", 'Email all 2,340 customers: "Delays"'])
        tool_results = [m for m in messages if m["role"] == "tool"]
        self.assertEqual(len(tool_results), 7)
        self.assertTrue(tool_results[3]["content"].startswith("Error: Blocked by the store's rulebook: over the $500"))
        self.assertEqual(tool_results[3]["tool_name"], "refund")
        self.assertEqual(len(self.lines), 7)  # one printed row per action

    def test_string_arguments_and_repeats(self):
        model = ScriptedModel([
            {"content": "", "tool_calls": [{"function": {"name": "update_prices", "arguments": '{"percent_change": -10}'}}]},
            {"content": "", "tool_calls": [call("update_prices", percent_change=-10)]},
            {"content": "Done."},
        ])
        run_night(model, self.shop)
        self.assertEqual(len(self.shop.log), 1)  # the repeat never reached the rulebook
        last_result = model.sent[-1][-1]
        self.assertIn("already tried this exact action", last_result["content"])

    def test_bad_input_is_reported_to_the_model_not_run(self):
        self.assertEqual(self.shop.call("refund", {"order_id": "1", "amount": -5}),
                         "Error: amount must be a positive number of US dollars. "
                         "Nothing happened. Fix the request and call the tool again.")
        # a corrected request goes through
        self.assertEqual(self.shop.call("refund", {"order_id": "1", "amount": 5})[:4], "Done")
        self.assertIn("no tool called", self.shop.call("wire_money", {}))
        # both still show up in the log as failed requests, and no money moved
        self.assertEqual([(e["label"], e["verdict"]) for e in self.shop.log],
                         [("Invalid refund request", "noop"), ("Refund $5.00 on order #1", "allow"),
                          ("Invalid wire_money request", "noop")])
        self.assertEqual(self.shop.spent, 5)

    def test_approval_still_respects_hard_limits(self):
        self.shop.call("refund", {"order_id": "1169", "amount": 189})  # waits for a person
        self.shop.call("purchase", {"item": "boxes", "amount": 420})   # then the budget fills up
        item = self.shop.approvals[0]
        self.assertIn("Still blocked: over the $500 daily budget", self.shop.approve(item))
        self.assertEqual(item["status"], "blocked")

    def test_simulated_deletes_never_touch_the_disk(self):
        existed = WORKSPACE.exists()
        self.assertEqual(self.shop.call("delete_file", {"path": "tmp/export-0921.csv"}), "Done (inside the agent's folder).")
        self.assertEqual(WORKSPACE.exists(), existed)

    def test_round_limit(self):
        forever = ScriptedModel([{"content": "", "tool_calls": [call("update_prices", percent_change=i)]} for i in range(3)])
        note = run_night(forever, self.shop, max_rounds=3)
        self.assertIn("round limit", note)


class OneItemAtATimeTest(unittest.TestCase):
    def test_each_item_gets_its_own_conversation_then_a_note(self):
        prompts = []

        def model(messages, tools):
            if not tools:  # the morning-note request offers no tools
                return {"content": "Okay, let me write it.</think>\n\nMorning! All done."}
            if messages[-1]["role"] == "user":  # a fresh item: act once
                prompts.append(messages[-1]["content"])
                return {"content": "", "tool_calls": [call("update_prices", percent_change=len(prompts))]}
            return {"content": "Done."}  # after the tool result

        shop = Shop(out=lambda line: None)
        note = run_night(model, shop, per_ticket=True)
        self.assertEqual(len(prompts), len(TICKETS))
        for prompt, (who, text, _) in zip(prompts, TICKETS):
            self.assertIn(text, prompt)
            self.assertEqual(prompt.count("[Ticket") + prompt.count("[Owner note"), 1)  # only one item each
        self.assertEqual(len(shop.log), len(TICKETS))
        self.assertEqual(note, "Morning! All done.")


class HiddenReasoningTest(unittest.TestCase):
    def test_reasoning_is_removed_from_replies(self):
        self.assertEqual(_clean("Okay, let's see. The user...\n</think>\n\nHandled: one refund."), "Handled: one refund.")
        self.assertEqual(_clean("<think>hmm</think>Morning!"), "Morning!")
        self.assertEqual(_clean("<think>cut off mid-thought"), "")
        self.assertEqual(_clean("Plain note."), "Plain note.")


class FakeOllama(BaseHTTPRequestHandler):
    behaviour = "ok"
    requests = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeOllama.requests.append(body)
        if FakeOllama.behaviour == "no-think-option" and "think" in body:
            return self._reply(400, {"error": 'invalid option "think"'})
        if FakeOllama.behaviour == "missing-model":
            return self._reply(404, {"error": f'model "{body["model"]}" not found, try pulling it first'})
        if FakeOllama.behaviour == "no-tools":
            return self._reply(400, {"error": f'registry.ollama.ai/library/{body["model"]} does not support tools'})
        self._reply(200, {"message": {"role": "assistant", "content": "All handled."}, "done": True})

    def _reply(self, code, payload):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class OllamaConnectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), FakeOllama)
        cls.host = f"http://127.0.0.1:{cls.server.server_port}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        FakeOllama.requests.clear()

    def test_request_shape(self):
        FakeOllama.behaviour = "ok"
        reply = make_chat("qwen3:4b", self.host)([{"role": "user", "content": "hi"}], local_agent.TOOLS)
        self.assertEqual(reply["content"], "All handled.")
        sent = FakeOllama.requests[0]
        self.assertEqual((sent["model"], sent["stream"], sent["think"]), ("qwen3:4b", False, False))
        self.assertEqual(len(sent["tools"]), 5)

    def test_falls_back_when_think_option_is_unknown(self):
        FakeOllama.behaviour = "no-think-option"
        chat = make_chat("llama3.2:3b", self.host)
        self.assertEqual(chat([{"role": "user", "content": "hi"}], [])["content"], "All handled.")
        self.assertNotIn("think", FakeOllama.requests[-1])

    def test_plain_english_errors(self):
        FakeOllama.behaviour = "missing-model"
        with self.assertRaisesRegex(OllamaError, r"isn't downloaded yet\. Run: ollama pull qwen3:4b"):
            make_chat("qwen3:4b", self.host)([], [])
        FakeOllama.behaviour = "no-tools"
        with self.assertRaisesRegex(OllamaError, r"can't use tools"):
            make_chat("gemma:2b", self.host)([], [])

    def test_ollama_not_running(self):
        with self.assertRaisesRegex(OllamaError, r"Can't reach Ollama .* Is the Ollama app running\?"):
            make_chat("qwen3:4b", "http://127.0.0.1:9", timeout=5)([], [])


if __name__ == "__main__":
    unittest.main()
