"""Zadania w tle bez dotykania Tk z watku roboczego.

Watek roboczy nigdy nie wywoluje metod Tk. Wynik trafia do kolejki, a watek
interfejsu odbiera go cyklicznie. Dzieki temu nie ma tez pulapki z lambda
przechwytujaca zmienna wyjatku (Python usuwa `exc` po bloku except, zanim
callback `after` zdazy sie wykonac) - do kolejki trafia sam obiekt wyjatku.
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

POLL_INTERVAL_MS = 50


class JobCancelled(Exception):
    """Zadanie przerwane przez uzytkownika."""


@dataclass
class JobContext:
    """Przekazywany do funkcji roboczej: postep i sprawdzanie anulowania."""

    cancel_event: threading.Event
    _events: queue.Queue[tuple[str, Any]]

    @property
    def cancelled(self) -> bool:
        return self.cancel_event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancel_event.is_set():
            raise JobCancelled()

    def report(self, done: int, total: int, message: Any = "") -> None:
        self._events.put(("progress", (done, total, message)))


class Job:
    def __init__(
        self,
        work: Callable[[JobContext], Any],
        *,
        on_progress: Callable[[int, int, Any], None] | None = None,
        on_success: Callable[[Any], None] | None = None,
        on_error: Callable[[BaseException], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
        on_finish: Callable[[], None] | None = None,
    ) -> None:
        self._work = work
        self._on_progress = on_progress
        self._on_success = on_success
        self._on_error = on_error
        self._on_cancel = on_cancel
        self._on_finish = on_finish
        self._events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.cancel_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True, name="studio-ocr-job")
        self.finished = False

    def start(self) -> None:
        self._thread.start()

    def cancel(self) -> None:
        self.cancel_event.set()

    def wait(self, timeout: float) -> bool:
        """Czeka na zakonczenie watku (np. przy zamykaniu okna). True, gdy zakonczony."""
        self._thread.join(timeout)
        return not self._thread.is_alive()

    def _run(self) -> None:
        context = JobContext(self.cancel_event, self._events)
        try:
            result = self._work(context)
        except JobCancelled:
            self._events.put(("cancelled", None))
        except BaseException as exc:  # noqa: BLE001 - przekazujemy kazdy wyjatek do UI
            self._events.put(("error", exc))
        else:
            self._events.put(("success", result))

    def pump(self) -> bool:
        """Obsluguje zakolejkowane zdarzenia (w watku UI). Zwraca True, gdy zadanie sie zakonczylo."""
        while True:
            try:
                kind, payload = self._events.get_nowait()
            except queue.Empty:
                return self.finished

            if kind == "progress":
                if self._on_progress:
                    self._on_progress(*payload)
                continue

            self.finished = True
            try:
                if kind == "success" and self._on_success:
                    self._on_success(payload)
                elif kind == "error" and self._on_error:
                    self._on_error(payload)
                elif kind == "cancelled" and self._on_cancel:
                    self._on_cancel()
            finally:
                if self._on_finish:
                    self._on_finish()
            return True


class JobRunner:
    """Uruchamia jedno zadanie naraz i odbiera jego zdarzenia w petli Tk."""

    def __init__(self, schedule: Callable[[int, Callable[[], None]], Any]) -> None:
        self._schedule = schedule
        self.current: Job | None = None

    @property
    def busy(self) -> bool:
        return self.current is not None and not self.current.finished

    def start(self, work: Callable[[JobContext], Any], **callbacks: Any) -> Job:
        if self.busy:
            raise RuntimeError("Inne zadanie jest juz uruchomione.")
        job = Job(work, **callbacks)
        self.current = job
        job.start()
        self._schedule(POLL_INTERVAL_MS, self._poll)
        return job

    def cancel(self) -> None:
        if self.current is not None:
            self.current.cancel()

    def _poll(self) -> None:
        job = self.current
        if job is None:
            return
        if not job.pump():
            self._schedule(POLL_INTERVAL_MS, self._poll)
