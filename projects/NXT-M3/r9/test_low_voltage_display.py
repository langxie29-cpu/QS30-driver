"""Deterministic in-memory fault injection, with no GPIO or HV access."""

from dataclasses import replace
import unittest

from low_voltage_display import Frame, Node, Transaction, cathode_bits


class FixtureDisplay:
    def __init__(self):
        self.digits = None
        self.oled = None
        self.staged = None
        self.bits = 0
        self.fail_write = False
        self.fail_show = False
        self.fail_hide = False
        self.power_cut = False
        self.events = []

    def blank_digits(self):
        self.digits = None
        self.events.append("digits_off")

    def hide_oled(self):
        if self.fail_hide:
            return False
        self.oled = None
        self.events.append("oled_hidden")
        return True

    def write_hidden(self, frame, slot, count):
        if self.fail_write:
            return False
        assert self.digits is None and self.oled is None
        self.staged = (frame.sequence, frame.label, frame.unit, slot, count)
        self.events.append("oled_staged")
        return True

    def show_oled(self):
        if self.fail_show:
            return False
        assert self.digits is None
        self.oled = self.staged
        self.events.append("oled_visible")
        return True

    def power_off_oled(self):
        self.oled = None
        self.events.append("oled_cut")

    def latch(self, bitmask):
        assert self.digits is None
        self.bits = bitmask
        self.events.append("latched")

    def enable_digits(self):
        assert self.oled == self.staged and self.oled is not None
        self.digits = self.bits
        self.events.append("digits_visible")

    def inhibit_power(self):
        self.power_cut = True


class Harness:
    """Fake coordinator fan-out with deliberate prepare/commit/abort loss."""

    def __init__(self, count=1, session="boot-a"):
        self.members = ("left", "mid", "right")[:count]
        self.nodes = {
            name: Node(name, FixtureDisplay(), session, "measure", self.members)
            for name in self.members
        }

    def transactions(self, value="073", **changes):
        frame = Frame("", "measure", 1, value, 0, "Voltage", "V", "sensor",
                      0, 5_000, "ok")
        return {
            name: Transaction(replace(frame, module_id=name, **changes),
                              node.session, self.members, 200)
            for name, node in self.nodes.items()
        }

    def publish(self, txs, *, lose_prepare=(), lose_commit=(), lose_abort=()):
        shared = {
            (replace(tx.frame, module_id=""), tx.members, tx.apply_at)
            for tx in txs.values()
        }
        if set(txs) != set(self.members) or len(shared) != 1:
            return False
        ready = []
        for name, node in self.nodes.items():
            if name not in lose_prepare and node.prepare(txs[name], 20):
                ready.append(name)
        if len(ready) != len(self.members):
            self.abort(txs, lose_abort)
            return False
        armed = []
        for name, node in self.nodes.items():
            if name not in lose_commit and node.commit(txs[name], 50):
                armed.append(name)
        if len(armed) != len(self.members):
            self.abort(txs, lose_abort)
        return len(armed) == len(self.members)

    def abort(self, txs, lose_abort):
        for name, node in self.nodes.items():
            if name not in lose_abort:
                node.abort(txs[name])

    def tick(self, now):
        for node in self.nodes.values():
            node.tick(now)


class DisplayProtocolTests(unittest.TestCase):
    def test_single_module_and_atomic_event_order(self):
        harness = Harness()
        self.assertTrue(harness.publish(harness.transactions()))
        node = harness.nodes["left"]
        harness.tick(199)
        self.assertIsNone(node.display.digits)
        harness.tick(200)
        self.assertEqual(node.display.digits, (1 << 0) | (1 << 17) | (1 << 23))
        self.assertEqual(node.display.oled, (1, "Voltage", "V", 0, 1))
        self.assertEqual(node.display.events[-4:],
                         ["oled_staged", "latched", "oled_visible", "digits_visible"])

    def test_six_digits_keep_leading_zeros_and_blank_padding(self):
        harness = Harness(2)
        txs = harness.transactions("00012")
        self.assertTrue(harness.publish(txs))
        harness.tick(200)
        self.assertEqual(harness.nodes["left"].display.digits, (1 << 10) | (1 << 20))
        self.assertEqual(harness.nodes["mid"].display.digits, cathode_bits("012", 0, 1))

    def test_nine_digits_same_semantics_and_order(self):
        harness = Harness(3)
        txs = harness.transactions("123456789", decimal_scale=2)
        self.assertTrue(harness.publish(txs))
        harness.tick(200)
        for slot, (name, node) in enumerate(harness.nodes.items()):
            self.assertEqual(node.display.digits, cathode_bits("123456789", slot, 3))
            self.assertEqual(node.display.oled, (1, "Voltage", "V", slot, 3))
            self.assertEqual(node.active, txs[name])

    def test_link_disconnect_and_bounded_peer_lease(self):
        harness = Harness(3)
        self.assertTrue(harness.publish(harness.transactions("123456789")))
        harness.tick(200)
        harness.nodes["mid"].link_down()
        self.assertIsNone(harness.nodes["mid"].display.digits)
        harness.tick(1200)
        self.assertTrue(all(node.display.digits is None for node in harness.nodes.values()))

    def test_source_ttl_overrides_lease(self):
        harness = Harness()
        txs = harness.transactions(ttl=310)
        self.assertTrue(harness.publish(txs))
        harness.tick(200)
        harness.tick(309)
        self.assertIsNotNone(harness.nodes["left"].display.digits)
        harness.tick(310)
        self.assertIsNone(harness.nodes["left"].display.digits)

    def test_coordinator_rejects_mixed_semantics(self):
        harness = Harness(2)
        txs = harness.transactions("123456")
        txs["mid"] = replace(txs["mid"], frame=replace(txs["mid"].frame, unit="A"))
        self.assertFalse(harness.publish(txs))
        harness.tick(200)
        self.assertTrue(all(node.active is None for node in harness.nodes.values()))

    def test_clock_uncertainty_growth_shortens_source_validity(self):
        harness = Harness()
        self.assertTrue(harness.publish(harness.transactions(ttl=310)))
        harness.tick(200)
        node = harness.nodes["left"]
        node.uncertainty_ms = 5
        harness.tick(305)
        self.assertIsNone(node.active)

    def test_missing_ready_never_commits(self):
        harness = Harness(3)
        self.assertFalse(harness.publish(harness.transactions("123456789"),
                                         lose_prepare=("mid",)))
        harness.tick(200)
        self.assertTrue(all(node.active is None for node in harness.nodes.values()))

    def test_partial_commit_even_if_abort_lost_is_bounded(self):
        harness = Harness(3)
        txs = harness.transactions("123456789")
        self.assertFalse(harness.publish(txs, lose_commit=("mid",),
                                         lose_abort=("left", "right")))
        harness.tick(200)
        self.assertIsNotNone(harness.nodes["left"].active)
        self.assertIsNone(harness.nodes["mid"].active)
        harness.tick(1200)
        self.assertTrue(all(node.active is None for node in harness.nodes.values()))

    def test_failed_oled_write_show_and_bus_cut(self):
        harness = Harness()
        node = harness.nodes["left"]
        node.display.fail_write = True
        self.assertFalse(harness.publish(harness.transactions()))
        node.display.fail_write = False
        node.display.fail_show = True
        self.assertTrue(harness.publish(harness.transactions(sequence=2)))
        node.display.fail_hide = True
        harness.tick(200)
        self.assertIsNone(node.display.digits)
        self.assertIsNone(node.display.oled)
        self.assertIn("oled_cut", node.display.events)

    def test_reboot_rejects_old_session_and_starts_blank(self):
        harness = Harness()
        txs = harness.transactions()
        self.assertTrue(harness.publish(txs))
        old_node = harness.nodes["left"]
        old_node.inhibit()
        rebooted = Harness(session="boot-b")
        node = rebooted.nodes["left"]
        self.assertFalse(node.prepare(txs["left"], 20))
        self.assertFalse(node.commit(txs["left"], 50))
        self.assertIsNone(node.display.digits)
        self.assertTrue(rebooted.publish(rebooted.transactions(value="007")))

    def test_ota_interruption_and_hardware_fault_are_fail_closed(self):
        harness = Harness()
        self.assertTrue(harness.publish(harness.transactions()))
        harness.tick(200)
        node = harness.nodes["left"]
        node.inhibit()
        node.inhibit(fault=True)
        node.tick(210)
        self.assertTrue(node.display.power_cut and node.fault_latched)
        self.assertFalse(node.prepare(harness.transactions(sequence=2)["left"], 20))
        self.assertIsNone(node.display.digits)

    def test_duplicate_replay_and_late_commit(self):
        harness = Harness()
        tx = harness.transactions()["left"]
        node = harness.nodes["left"]
        self.assertTrue(node.prepare(tx, 20))
        self.assertTrue(node.prepare(tx, 99))
        self.assertTrue(node.commit(tx, 50))
        self.assertTrue(node.commit(tx, 60))
        harness.tick(211)
        self.assertIsNone(node.active)
        self.assertFalse(node.commit(tx, 212))
        self.assertFalse(node.prepare(tx, 20))

    def test_skew_limit_and_bad_data(self):
        harness = Harness()
        node = harness.nodes["left"]
        node.uncertainty_ms = 6
        self.assertFalse(node.prepare(harness.transactions()["left"], 20))
        node.uncertainty_ms = 5
        for value in ("-42", "1.2", "1234", "１２", ""):
            self.assertFalse(node.prepare(harness.transactions(value)["left"], 20))
        self.assertFalse(node.prepare(harness.transactions("007", status="invalid")["left"], 20))
        self.assertFalse(node.prepare(harness.transactions("007", decimal_scale=3)["left"], 20))

    def test_lease_renewal_is_bounded_and_idempotent(self):
        harness = Harness()
        txs = harness.transactions()
        self.assertTrue(harness.publish(txs))
        harness.tick(200)
        node, tx = harness.nodes["left"], txs["left"]
        self.assertFalse(node.renew(tx, 1, 1_601, 600))
        self.assertTrue(node.renew(tx, 1, 1_600, 600))
        self.assertTrue(node.renew(tx, 1, 1_600, 650))
        self.assertFalse(node.renew(tx, 1, 1_650, 650))
        harness.tick(1_599)
        self.assertIsNotNone(node.active)
        harness.tick(1_600)
        self.assertIsNone(node.active)


if __name__ == "__main__":
    unittest.main()
