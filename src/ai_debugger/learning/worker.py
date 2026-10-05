"""Single async worker consuming a bounded asyncio.Queue of LearningJob."""
from __future__ import annotations

import asyncio

import structlog

from ai_debugger.learning.pipeline import LearningJob, LearningPipeline

log = structlog.get_logger(__name__)


class LearningWorker:
    def __init__(self, *, queue: asyncio.Queue, pipeline: LearningPipeline) -> None:
        self._queue = queue
        self._pipeline = pipeline
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    # ---------- lifecycle ----------

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="learning_worker")
        log.info("learning_worker.started", maxsize=self._queue.maxsize)

    async def stop(self, timeout: float = 30.0) -> None:
        self._stop.set()
        if self._task is None:
            return
        try:
            await asyncio.wait_for(self._task, timeout=timeout)
        except asyncio.TimeoutError:
            log.warning("learning_worker.shutdown_timeout", timeout=timeout)
            self._task.cancel()
        finally:
            self._task = None
            log.info("learning_worker.stopped")

    # ---------- enqueue ----------

    def enqueue(self, job: LearningJob) -> bool:
        """Non-blocking enqueue. Returns False if the queue is full (job dropped)."""
        try:
            self._queue.put_nowait(job)
            log.info(
                "learning_worker.enqueued",
                feedback_id=job.feedback_id,
                qsize=self._queue.qsize(),
            )
            return True
        except asyncio.QueueFull:
            log.warning(
                "learning_worker.queue_full_drop",
                feedback_id=job.feedback_id,
                maxsize=self._queue.maxsize,
            )
            return False

    # ---------- run ----------

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            try:
                outcome = await self._pipeline.process(job)
                log.info(
                    "learning_worker.job_done",
                    feedback_id=job.feedback_id,
                    action=outcome.action,
                    memory_id=outcome.memory_id,
                )
            except Exception:
                log.exception("learning_worker.job_crashed", feedback_id=job.feedback_id)
            finally:
                self._queue.task_done()