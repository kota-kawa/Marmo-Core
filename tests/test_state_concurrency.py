from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest import mock
import tempfile
import threading
import unittest

from marmo_core import (
    BudgetExceededError,
    BudgetLedger,
    InMemoryStateStore,
    JsonFileStateStore,
    ModelPrice,
    SQLiteStateStore,
    StateConflictError,
    TaskBudget,
)
from marmo_core import state as state_module


def _budget(amount: str) -> TaskBudget:
    return TaskBudget(
        amount=Decimal(amount),
        currency="USD",
        resource_cost_unit="USD",
        model_price=ModelPrice(Decimal(0), Decimal(0), 1000, 1000),
    )


class CrossConnectionBudgetTests(unittest.TestCase):
    def _competing_reservations(self, first_store, second_store) -> tuple[BudgetLedger, str, list[bool]]:
        task_id = first_store.create("Do work").task_id
        first = BudgetLedger(first_store, _budget("5"))
        second = BudgetLedger(second_store, _budget("5"))
        first.attach(task_id)
        outcomes: list[bool] = []
        original_append = first_store.append
        interleaved = False

        def append_after_the_other_connection(*args, **kwargs):
            # The other connection reserves after this ledger checked the
            # balance and before it records its own reservation.
            nonlocal interleaved
            if not interleaved:
                interleaved = True
                second.reserve(task_id, "other connection", Decimal("4"))
                outcomes.append(True)
            return original_append(*args, **kwargs)

        with mock.patch.object(first_store, "append", append_after_the_other_connection):
            try:
                first.reserve(task_id, "this connection", Decimal("4"))
                outcomes.append(True)
            except BudgetExceededError:
                outcomes.append(False)
        return first, task_id, outcomes

    def test_two_sqlite_connections_cannot_both_reserve_past_the_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.sqlite"
            first_store = SQLiteStateStore(path)
            second_store = SQLiteStateStore(path)
            self.addCleanup(first_store.close)
            self.addCleanup(second_store.close)

            ledger, task_id, outcomes = self._competing_reservations(first_store, second_store)

            self.assertEqual(sorted(outcomes), [False, True])
            self.assertEqual(ledger.status(task_id)["reserved"], "4")

    def test_two_json_stores_cannot_both_reserve_past_the_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger, task_id, outcomes = self._competing_reservations(
                JsonFileStateStore(directory), JsonFileStateStore(directory)
            )

            self.assertEqual(sorted(outcomes), [False, True])
            self.assertEqual(ledger.status(task_id)["reserved"], "4")


class CrossInstanceWriteTests(unittest.TestCase):
    def test_json_stores_on_one_directory_never_write_the_same_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stores = [JsonFileStateStore(directory) for _ in range(4)]
            task_id = stores[0].create("Do work").task_id
            barrier = threading.Barrier(len(stores))

            def write(store: JsonFileStateStore) -> None:
                barrier.wait(timeout=10)
                for index in range(25):
                    while True:
                        try:
                            store.append(task_id, "variable", {"key": "k", "value": index})
                        except StateConflictError:
                            continue
                        break

            threads = [threading.Thread(target=write, args=(store,)) for store in stores]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=30)

            seqs = [event.seq for event in stores[0].events(task_id)]
            self.assertEqual(seqs, list(range(1, 102)))


class ExecutionRightTests(unittest.TestCase):
    def _assert_exclusive(self, first, second) -> None:
        task_id = first.create("Do work").task_id
        with first.execution(task_id):
            with self.assertRaises(StateConflictError) as raised:
                with second.execution(task_id):
                    self.fail("a second executor must not enter")
            self.assertIn("already being executed", str(raised.exception))
        with second.execution(task_id):
            pass

    def test_same_instance_is_exclusive(self) -> None:
        store = InMemoryStateStore()
        self._assert_exclusive(store, store)

    def test_json_stores_on_one_directory_are_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self._assert_exclusive(JsonFileStateStore(directory), JsonFileStateStore(directory))

    def test_sqlite_connections_to_one_file_are_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.sqlite"
            first, second = SQLiteStateStore(path), SQLiteStateStore(path)
            self.addCleanup(first.close)
            self.addCleanup(second.close)
            self._assert_exclusive(first, second)

    def test_different_tasks_do_not_block_each_other(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = JsonFileStateStore(directory)
            one = store.create("One").task_id
            two = store.create("Two").task_id
            with store.execution(one), JsonFileStateStore(directory).execution(two):
                pass


class RollbackProjectionTests(unittest.TestCase):
    def test_repeated_rollbacks_apply_each_event_once(self) -> None:
        store = InMemoryStateStore()
        task_id = store.create("Do work").task_id
        for index in range(30):
            store.append(task_id, "variable", {"key": "round", "value": index})
            checkpoint = store.checkpoint(task_id, f"cp-{index}")
            store.append(task_id, "variable", {"key": "discarded", "value": index})
            store.rollback(task_id, checkpoint.seq)
        events = store.events(task_id)

        with mock.patch.object(state_module, "_apply", wraps=state_module._apply) as apply:
            state = store.load(task_id)

        self.assertLessEqual(apply.call_count, len(events))
        self.assertEqual(state.variables, {"round": 29})
        self.assertEqual(state.version, events[-1].seq)

    def test_rollback_restores_the_state_at_the_target_even_after_earlier_rollbacks(self) -> None:
        store = InMemoryStateStore()
        task_id = store.create("Do work").task_id
        store.append(task_id, "variable", {"key": "a", "value": 1})
        first = store.checkpoint(task_id, "first")
        store.append(task_id, "variable", {"key": "b", "value": 2})
        store.rollback(task_id, first.seq)
        store.append(task_id, "variable", {"key": "c", "value": 3})
        second = store.checkpoint(task_id, "second")
        store.append(task_id, "variable", {"key": "d", "value": 4})

        self.assertEqual(store.rollback(task_id, second.seq).variables, {"a": 1, "c": 3})
        self.assertEqual(store.rollback(task_id, first.seq).variables, {"a": 1})
        self.assertEqual(store.replay(task_id, until_seq=second.seq).variables, {"a": 1, "c": 3})


if __name__ == "__main__":
    unittest.main()
