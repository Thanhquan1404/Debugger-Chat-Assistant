from __future__ import annotations

import asyncio

import pytest

from ai_debugger.learning import LearningJob, LearningWorker


class FakePipeline:
    def __init__(self):
        self.processed: list[str] = []
        self.should_raise = False

    async def process(self, job: LearningJob):
        if self.should_raise:
            raise RuntimeError("boom")
        self.processed.append(job.feedback_id)
        return type("O", (), {"action": "inserted", "memory_id": "m1", "reason": None})()


@pytest.mark.asyncio
async def test_worker_processes_jobs_in_order():
    q: asyncio.Queue = asyncio.Queue(maxsize=10)
    pipe = FakePipeline()
    worker = LearningWorker(queue=q, pipeline=pipe)
    await worker.start()

    for i in range(5):
        worker.enqueue(LearningJob("fb" + str(i), "s1", "u1", "a1"))
    await asyncio.sleep(0.2)
    await worker.stop(timeout=2.0)

    assert pipe.processed == [f"fb{i}" for i in range(5)]


@pytest.mark.asyncio
async def test_enqueue_returns_false_when_full():
    q: asyncio.Queue = asyncio.Queue(maxsize=2)
    worker = LearningWorker(queue=q, pipeline=FakePipeline())
    # Don't start worker → queue stays full after 2 puts
    assert worker.enqueue(LearningJob("a", "s", "u", "a")) is True
    assert worker.enqueue(LearningJob("b", "s", "u", "a")) is True
    assert worker.enqueue(LearningJob("c", "s", "u", "a")) is False


@pytest.mark.asyncio
async def test_worker_survives_pipeline_error():
    q: asyncio.Queue = asyncio.Queue(maxsize=10)
    pipe = FakePipeline()
    pipe.should_raise = True
    worker = LearningWorker(queue=q, pipeline=pipe)
    await worker.start()

    worker.enqueue(LearningJob("fb1", "s", "u", "a"))
    await asyncio.sleep(0.2)
    pipe.should_raise = False
    worker.enqueue(LearningJob("fb2", "s", "u", "a"))
    await asyncio.sleep(0.2)
    await worker.stop(timeout=2.0)

    assert "fb2" in pipe.processed