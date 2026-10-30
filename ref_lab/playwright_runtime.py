"""One persistent asyncio loop for Playwright's async object graph."""
from __future__ import annotations

import asyncio
from concurrent.futures import Future, TimeoutError as FutureTimeout
import threading


class PlaywrightLoop:
    """Serial synchronous bridge to a loop that keeps pumping between calls."""

    def __init__(self, name: str = "playwright-runtime"):
        self.name = name
        self.loop = None
        self.thread = None
        self._ready = threading.Event()
        self._run_lock = threading.Lock()
        self._pending: set[Future] = set()
        self._pending_lock = threading.Lock()

    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.loop = loop
        self._ready.set()
        try:
            loop.run_forever()
        finally:
            loop.close()

    def start(self, timeout: float = 5.0) -> None:
        if self.thread is not None and self.thread.is_alive():
            return
        self._ready.clear()
        self.thread = threading.Thread(target=self._thread_main, name=self.name, daemon=True)
        self.thread.start()
        if not self._ready.wait(timeout) or self.loop is None:
            raise RuntimeError("Playwright event loop did not start")

    def submit(self, coroutine) -> Future:
        if self.loop is None or self.thread is None or not self.thread.is_alive():
            if hasattr(coroutine, "close"):
                coroutine.close()
            raise RuntimeError("Playwright event loop is not running")
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        with self._pending_lock:
            self._pending.add(future)
        future.add_done_callback(self._discard)
        return future

    def _discard(self, future: Future) -> None:
        with self._pending_lock:
            self._pending.discard(future)

    def run(self, coroutine, timeout_ms: int):
        with self._run_lock:
            future = self.submit(coroutine)
            try:
                return future.result(timeout=max(0.001, timeout_ms / 1000))
            except FutureTimeout as exc:
                future.cancel()
                raise asyncio.TimeoutError() from exc

    async def _cancel_pending(self) -> None:
        current = asyncio.current_task()
        tasks = [task for task in asyncio.all_tasks() if task is not current]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def stop(self, timeout: float = 3.0) -> None:
        if self.loop is None or self.thread is None:
            return
        if self.thread.is_alive() and self.loop.is_running():
            try:
                self.run(self._cancel_pending(), min(2000, int(timeout * 1000)))
            except Exception:
                pass
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=max(0.0, timeout))
        if self.thread.is_alive():
            raise TimeoutError("Playwright event loop thread did not stop")
        with self._pending_lock:
            pending = list(self._pending)
        for future in pending:
            future.cancel()
        self.loop = None
        self.thread = None
