import threading
import time

import pytest

from src.jobs import Job, JobCancelled, JobRunner


def drain(job, timeout=5.0):
    """Odbiera zdarzenia tak, jak robi to petla Tk."""
    end = time.time() + timeout
    while time.time() < end:
        if job.pump():
            return
        time.sleep(0.005)
    raise AssertionError("zadanie nie zakonczylo sie w czasie")


def test_success_callbacks_run_in_pumping_thread_in_order():
    log = []
    main = threading.get_ident()

    def work(ctx):
        ctx.report(1, 2, "polowa")
        ctx.report(2, 2, "koniec")
        return 42

    job = Job(
        work,
        on_progress=lambda *a: log.append(("progress", a, threading.get_ident() == main)),
        on_success=lambda r: log.append(("success", r, threading.get_ident() == main)),
        on_finish=lambda: log.append(("finish",)),
    )
    job.start()
    drain(job)
    assert log == [
        ("progress", (1, 2, "polowa"), True),
        ("progress", (2, 2, "koniec"), True),
        ("success", 42, True),
        ("finish",),
    ]


def test_error_passes_the_exception_object_not_a_closure():
    # regresja: lambda przechwytujaca `exc` z bloku except dostawala NameError po jego zakonczeniu
    received = []

    def work(ctx):
        raise ValueError("szczegoly bledu")

    job = Job(work, on_error=received.append)
    job.start()
    drain(job)
    assert len(received) == 1 and isinstance(received[0], ValueError) and str(received[0]) == "szczegoly bledu"


def test_error_message_is_still_available_long_after_the_worker_ended():
    received = []
    job = Job(lambda ctx: 1 / 0, on_error=received.append)
    job.start()
    job._thread.join()
    time.sleep(0.05)  # callback uruchamiany "pozniej", jak w Tk
    drain(job)
    assert "division by zero" in str(received[0])


def test_cancel_before_start_of_work():
    done = []
    job = Job(lambda ctx: ctx.raise_if_cancelled(), on_cancel=lambda: done.append("cancel"), on_success=lambda r: done.append("ok"))
    job.cancel()
    job.start()
    drain(job)
    assert done == ["cancel"]


def test_cooperative_cancel_in_loop():
    started = threading.Event()
    results = []

    def work(ctx):
        started.set()
        for _ in range(1000):
            ctx.raise_if_cancelled()
            time.sleep(0.005)
        return "doszlo do konca"

    job = Job(work, on_cancel=lambda: results.append("cancel"), on_success=results.append)
    job.start()
    started.wait(2)
    job.cancel()
    drain(job)
    assert results == ["cancel"]


def test_job_cancelled_subclass_is_treated_as_cancel():
    class Custom(JobCancelled):
        pass

    def work(ctx):
        raise Custom()

    results = []
    job = Job(work, on_cancel=lambda: results.append("cancel"), on_error=lambda e: results.append("error"))
    job.start()
    drain(job)
    assert results == ["cancel"]


def test_finish_callback_runs_even_if_success_callback_fails():
    log = []

    def bad_success(_r):
        raise RuntimeError("blad w callbacku")

    job = Job(lambda ctx: 1, on_success=bad_success, on_finish=lambda: log.append("finish"))
    job.start()
    with pytest.raises(RuntimeError):
        drain(job)
    assert log == ["finish"]


def test_runner_allows_only_one_job_at_a_time():
    scheduled = []
    runner = JobRunner(lambda ms, fn: scheduled.append(fn))
    release = threading.Event()
    first = runner.start(lambda ctx: release.wait(2))
    assert runner.busy
    with pytest.raises(RuntimeError):
        runner.start(lambda ctx: None)
    release.set()
    first._thread.join()
    while scheduled:
        scheduled.pop(0)()
    assert not runner.busy
    runner.start(lambda ctx: None)  # po zakonczeniu mozna startowac kolejne


def test_runner_cancel_without_job_is_noop():
    JobRunner(lambda ms, fn: None).cancel()


def test_wait_returns_after_thread_ends():
    job = Job(lambda ctx: None)
    job.start()
    assert job.wait(2.0)
