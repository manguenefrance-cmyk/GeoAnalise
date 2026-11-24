"""One embedded queue consumer for small, single-process test deployments."""

import logging
from threading import Event, Thread

logger = logging.getLogger("arcambe.worker")


class EmbeddedWorker:
    def __init__(self, work=None, idle_seconds=3):
        if work is None:
            from .jobs import work_once

            work = work_once
        self.work, self.idle_seconds = work, idle_seconds
        self.stop_event = Event()
        self.thread = Thread(target=self.run, name="arcambe-queue", daemon=True)

    def start(self):
        self.thread.start()

    def run(self):
        while not self.stop_event.is_set():
            try:
                if self.work():
                    continue
            except Exception as exc:
                # A temporary database outage must not silently kill the consumer.
                logger.warning("queue_poll_failed type=%s", type(exc).__name__)
            self.stop_event.wait(self.idle_seconds)

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=5)
        # A forced shutdown leaves an active job subject to the existing durable lease.
