"""Host-only NXT R9 transaction model. Times are integer reference-clock ms."""

from dataclasses import dataclass
from typing import Protocol


FIRST_LEASE_MS = 1_000
MIN_LEAD_MS = 100
MAX_LEAD_MS = 2_000
MAX_UNCERTAINTY_MS = 5
MAX_LATE_MS = 10
MAX_TTL_MS = 60_000


class Display(Protocol):
    """Segment LEDs and OLED driver boundary for the isolated fixture."""

    def blank_digits(self) -> None: ...
    def hide_oled(self) -> bool: ...
    def write_hidden(self, frame: "Frame", slot: int, count: int) -> bool: ...
    def show_oled(self) -> bool: ...
    def power_off_oled(self) -> None: ...
    def latch(self, bitmask: int) -> None: ...
    def enable_digits(self) -> None: ...
    def inhibit_power(self) -> None: ...


@dataclass(frozen=True)
class Frame:
    module_id: str
    group_id: str
    sequence: int
    value: str
    decimal_scale: int
    label: str
    unit: str
    source: str
    timestamp: int
    ttl: int
    status: str

    def valid(self, now: int, width: int) -> bool:
        return (
            type(self.sequence) is int and 0 < self.sequence < 2**64
            and isinstance(self.value, str) and 1 <= len(self.value) <= width
            and all("0" <= char <= "9" for char in self.value)
            and type(self.decimal_scale) is int
            and 0 <= self.decimal_scale < len(self.value)
            and type(self.timestamp) is int and 0 <= self.timestamp <= now
            and type(self.ttl) is int and 0 < self.ttl <= MAX_TTL_MS
            and now < self.expires
            and valid_text(self.group_id, 32) and valid_text(self.label, 32)
            and valid_text(self.unit, 16, allow_empty=True)
            and valid_text(self.source, 32) and self.status == "ok"
        )

    @property
    def expires(self) -> int:
        return self.timestamp + self.ttl


def valid_text(value: str, limit: int, allow_empty: bool = False) -> bool:
    return (
        isinstance(value, str) and len(value) <= limit
        and (bool(value) or allow_empty)
        and all(char.isprintable() for char in value)
    )


@dataclass(frozen=True)
class Transaction:
    frame: Frame
    session: str
    members: tuple[str, ...]
    apply_at: int


def cathode_bits(value: str, slot: int, count: int) -> int:
    if count not in (1, 2, 3) or not 0 <= slot < count:
        raise ValueError("invalid group width or slot")
    if not 1 <= len(value) <= 3 * count or any(
        digit < "0" or digit > "9" for digit in value
    ):
        raise ValueError("invalid decimal digits")
    digits = value.rjust(3 * count)[slot * 3:slot * 3 + 3]
    return sum(1 << (index * 10 + int(digit))
               for index, digit in enumerate(digits) if digit != " ")


class Node:
    """One authenticated configuration/session, replaced on reset or regroup."""

    def __init__(
        self, module_id: str, display: Display, session: str,
        group_id: str, members: tuple[str, ...],
    ):
        if len(members) not in (1, 2, 3) or len(set(members)) != len(members):
            raise ValueError("invalid configured membership")
        self.module_id = module_id
        self.display = display
        self.session = session
        self.group_id = group_id
        self.members = members
        self.slot = members.index(module_id)
        self.connected = True
        self.uncertainty_ms = 0  # Supplied by the fixture clock, not a Wi-Fi default.
        self.running = True
        self.fault_latched = False
        self.sequence = 0
        self.pending: Transaction | None = None
        self.committed = False
        self.active: Transaction | None = None
        self.lease_until = 0
        self.lease_round = 0
        self.blank()

    def blank(self) -> bool:
        self.display.blank_digits()
        oled_hidden = self.display.hide_oled()
        if not oled_hidden:
            self.display.power_off_oled()
        self.pending = self.active = None
        self.committed = False
        self.lease_until = self.lease_round = 0
        return oled_hidden

    def permitted(self) -> bool:
        return (self.connected and self.running and not self.fault_latched
                and 0 <= self.uncertainty_ms <= MAX_UNCERTAINTY_MS)

    def prepare(self, tx: Transaction, now: int) -> bool:
        frame = tx.frame
        if not self.permitted() or not (
            tx.session == self.session and tx.members == self.members
            and frame.module_id == self.module_id and frame.group_id == self.group_id
            and frame.valid(now, 3 * len(self.members))
        ):
            return False
        if tx == self.pending or tx == self.active:
            deadline = self.lease_until if tx == self.active else tx.apply_at
            return now < min(frame.expires, deadline)
        if not (
            frame.sequence > self.sequence
            and MIN_LEAD_MS <= tx.apply_at - now <= MAX_LEAD_MS
            and tx.apply_at + MAX_LATE_MS + 2 * MAX_UNCERTAINTY_MS < frame.expires
        ):
            return False
        self.sequence = frame.sequence
        if not self.blank() or not self.display.write_hidden(
            frame, self.slot, len(self.members)
        ):
            self.blank()
            return False
        self.display.latch(cathode_bits(frame.value, self.slot, len(self.members)))
        self.pending = tx
        return True

    def commit(self, tx: Transaction, now: int) -> bool:
        if self.active == tx and now < self.lease_until and self.permitted():
            return True
        if not (self.permitted() and self.pending == tx and now < tx.apply_at):
            return False
        self.committed = True
        return True

    def tick(self, now: int) -> None:
        if not self.permitted():
            if self.active or self.pending:
                self.blank()
            return
        if self.active and now >= min(
            self.lease_until, self.active.frame.expires - self.uncertainty_ms
        ):
            self.blank()
        tx = self.pending
        if tx is None or now < tx.apply_at:
            return
        if (not self.committed or now - tx.apply_at > MAX_LATE_MS
                or now + self.uncertainty_ms >= tx.frame.expires
                or not self.display.show_oled()):
            self.blank()
            return
        self.active, self.pending = tx, None
        self.committed = False
        self.lease_until = min(tx.frame.expires - self.uncertainty_ms,
                               tx.apply_at + FIRST_LEASE_MS)
        self.display.enable_digits()

    def renew(self, tx: Transaction, round_id: int, until: int, now: int) -> bool:
        if not (self.permitted() and self.active == tx and now < self.lease_until):
            return False
        if round_id == self.lease_round:
            return until == self.lease_until
        if not (round_id == self.lease_round + 1 and
                self.lease_until < until <= min(
                    now + FIRST_LEASE_MS, tx.frame.expires - MAX_UNCERTAINTY_MS)):
            return False
        self.lease_round, self.lease_until = round_id, until
        return True

    def abort(self, tx: Transaction) -> None:
        if tx in (self.pending, self.active):
            self.blank()

    def link_down(self) -> None:
        self.connected = False
        self.blank()

    def inhibit(self, *, fault: bool = False) -> None:
        self.running = False
        self.fault_latched |= fault
        self.display.inhibit_power()
        self.blank()
