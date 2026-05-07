"""Tests für BackgroundJobs-Queue-Verhalten."""

from datetime import datetime

from app.core import background_jobs
from app.core.background_jobs import (
    ANALYZE_BATCH_SIZE,
    ANALYZE_RETRY_DELAY_SECONDS,
    QUEUED_ANALYZE_JOB_ID,
    SCHEDULER_MISFIRE_GRACE_SECONDS,
    BackgroundJobs,
)


class DummyScheduler:
    """Minimaler Scheduler-Spy für APScheduler-Aufrufe."""

    def __init__(self) -> None:
        self.calls = []

    def add_job(self, *args, **kwargs) -> None:
        self.calls.append((args, kwargs))


def test_queue_analyze_ads_uses_deduplicated_immediate_job():
    """Immediate Analyzer-Jobs bekommen eine stabile ID und keinen künstlichen run_date."""
    jobs = BackgroundJobs()
    scheduler = DummyScheduler()
    jobs._scheduler = scheduler  # pyright: ignore[reportPrivateUsage]

    jobs._queue_analyze_ads()  # pyright: ignore[reportPrivateUsage]

    args, kwargs = scheduler.calls[0]
    assert args == (jobs._run_analyze_ads, "date")  # pyright: ignore[reportPrivateUsage]
    assert kwargs["id"] == QUEUED_ANALYZE_JOB_ID
    assert kwargs["replace_existing"] is True
    assert kwargs["executor"] == "analyzer"
    assert kwargs["misfire_grace_time"] == SCHEDULER_MISFIRE_GRACE_SECONDS
    assert "run_date" not in kwargs


def test_run_analyze_ads_retries_when_batch_makes_no_progress(monkeypatch):
    """Ein fehlerhafter Batch darf den Analyse-Rückstand nicht dauerhaft liegen lassen."""

    class FakeAIService:
        def __init__(self, service_session) -> None:
            self.session = service_session

        def analyze_unprocessed(self, limit: int = ANALYZE_BATCH_SIZE) -> int:
            assert limit == ANALYZE_BATCH_SIZE
            return 0

    class FakeResult:
        def one(self) -> int:
            return 5

    class FakeSession:
        def __init__(self, engine) -> None:
            self.engine = engine

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def exec(self, query) -> FakeResult:
            return FakeResult()

    monkeypatch.setattr(background_jobs, "Session", FakeSession)
    monkeypatch.setattr("app.services.ai.AIService", FakeAIService)

    jobs = BackgroundJobs()
    scheduler = DummyScheduler()
    jobs._scheduler = scheduler  # pyright: ignore[reportPrivateUsage]

    jobs._run_analyze_ads()  # pyright: ignore[reportPrivateUsage]

    args, kwargs = scheduler.calls[0]
    assert args == (jobs._run_analyze_ads, "date")  # pyright: ignore[reportPrivateUsage]
    assert kwargs["id"] == QUEUED_ANALYZE_JOB_ID
    assert kwargs["replace_existing"] is True
    assert kwargs["executor"] == "analyzer"
    assert kwargs["misfire_grace_time"] == SCHEDULER_MISFIRE_GRACE_SECONDS
    assert isinstance(kwargs["run_date"], datetime)
    assert (kwargs["run_date"] - datetime.now(kwargs["run_date"].tzinfo)).total_seconds() <= (
        ANALYZE_RETRY_DELAY_SECONDS + 1
    )
