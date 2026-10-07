"""You can unit-test a rulebook. You can't unit-test a model's judgment."""
import unittest

from rulebook import decide


def verdict(action, spent=0.0):
    return decide(action, spent).verdict


class RulebookTest(unittest.TestCase):
    def test_reads_are_allowed(self):
        self.assertEqual(verdict({"type": "read"}), "allow")

    def test_small_refund_is_allowed(self):
        self.assertEqual(verdict({"type": "refund", "amount": 40}), "allow")

    def test_large_refund_waits_for_a_human(self):
        self.assertEqual(verdict({"type": "refund", "amount": 100.01}), "ask")

    def test_spend_limit_is_a_hard_stop(self):
        self.assertEqual(verdict({"type": "purchase", "amount": 50}, spent=480), "deny")
        self.assertEqual(verdict({"type": "refund", "amount": 150}, spent=400), "deny")

    def test_bulk_message_waits_for_a_human(self):
        self.assertEqual(verdict({"type": "send_message", "to": ["a@x.com"] * 10}), "allow")
        self.assertEqual(verdict({"type": "send_message", "to": ["a@x.com"] * 11}), "ask")

    def test_deletes_stay_inside_the_workspace(self):
        self.assertEqual(verdict({"type": "delete_file", "path": "tmp/old.csv"}), "allow")
        self.assertEqual(verdict({"type": "delete_file", "path": "../shared/customers.db"}), "deny")
        self.assertEqual(verdict({"type": "delete_file", "path": "tmp/../../notes.txt"}), "deny")
        self.assertEqual(verdict({"type": "delete_file", "path": "/etc/hosts"}), "deny")

    def test_unknown_actions_are_denied_by_default(self):
        self.assertEqual(verdict({"type": "update_prices", "change": -0.2}), "deny")


if __name__ == "__main__":
    unittest.main()
