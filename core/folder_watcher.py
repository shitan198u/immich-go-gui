"""Real-time filesystem watcher for the Monitor subsystem.

Uses watchdog to detect on_created and on_modified events in watched folders,
batches them via a debounce queue, and emits file lists for upload.
"""

import logging
import os
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from .folder_filters import is_within_folder, should_skip_file
from .monitor_config import FolderFilter, MonitorConfig

_log = logging.getLogger(__name__)


class DebounceFileQueue:
    """Thread-safe file queue that batches changes within a fixed window.

    The timer starts on the empty -> non-empty transition and is NOT reset
    by subsequent files, so a folder that keeps receiving changes still
    flushes at least once per window (a sliding window could starve
    uploads forever).
    """

    def __init__(self, debounce_seconds: int = 30):
        self._lock = threading.Lock()
        self._files: dict[str, float] = {}  # file_path -> first_seen_time
        self._debounce_seconds = debounce_seconds
        self._timer: threading.Timer | None = None
        self._callback: Callable[[list[str]], None] | None = None
        self._shutdown = False

    def set_callback(self, callback: Callable[[list[str]], None]) -> None:
        """Set the function called when the debounce window expires."""
        self._callback = callback

    def add_file(self, file_path: str) -> None:
        """Add a file to the queue; starts the batch window if it was empty."""
        with self._lock:
            if self._shutdown:
                return
            was_empty = not self._files
            if file_path not in self._files:
                self._files[file_path] = datetime.now(UTC).timestamp()
            if was_empty:
                self._start_timer_locked()

    def add_files(self, paths: list[str]) -> None:
        """Add multiple files at once."""
        with self._lock:
            if self._shutdown:
                return
            was_empty = not self._files
            now = datetime.now(UTC).timestamp()
            for p in paths:
                if p not in self._files:
                    self._files[p] = now
            if was_empty:
                self._start_timer_locked()

    def flush(self) -> list[str]:
        """Immediately flush and return all queued files."""
        with self._lock:
            return self._drain_locked()

    def _drain_locked(self) -> list[str]:
        """Drain queued files and cancel any pending timer. Lock must be held."""
        files = list(self._files.keys())
        self._files.clear()
        if self._timer:
            self._timer.cancel()
            self._timer = None
        return files

    def _start_timer_locked(self) -> None:
        """Start the batch window timer. Lock must be held."""
        if self._shutdown:
            return
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(self._debounce_seconds, self._on_timeout)
        self._timer.daemon = True
        self._timer.start()

    def _on_timeout(self) -> None:
        """Called when the debounce window expires."""
        with self._lock:
            self._timer = None
            files = self._drain_locked()
        # Invoke the callback outside the lock.
        if files and self._callback:
            self._callback(files)

    def shutdown(self) -> None:
        """Cancel timer, clear queue, and reject further additions."""
        with self._lock:
            self._shutdown = True
            if self._timer:
                self._timer.cancel()
                self._timer = None
            self._files.clear()


class WatchedFolder:
    """Configuration and state for a single watched folder."""

    def __init__(
        self,
        path: str,
        filter_rules: FolderFilter,
    ):
        self.path = str(Path(path).resolve())
        self.filter_rules = filter_rules
        self.enabled = True

    def should_accept(self, file_path: str) -> bool:
        """Check if a file should be accepted by this folder's filters."""
        return not should_skip_file(file_path, self.filter_rules)

    def should_accept_event(self, src_path: str) -> bool:
        """Check if a watchdog event path should be accepted."""
        # Must be within this folder (boundary-safe: a sibling folder whose
        # name merely starts with the same prefix must not match).
        if not is_within_folder(self.path, src_path):
            return False

        # Must be a file
        if not os.path.isfile(src_path):
            return False

        # Apply filters
        return self.should_accept(src_path)


class FolderWatcher:
    """Watchdog-based folder watcher that debounces events into a file queue."""

    def __init__(
        self,
        config: MonitorConfig,
        on_batch_ready: Callable[[list[str]], None],
    ):
        self.config = config
        self._queue = DebounceFileQueue(config.watcher_debounce_seconds)
        self._queue.set_callback(on_batch_ready)
        self._observer = None
        self._watched_folders: dict[str, WatchedFolder] = {}
        self._running = False
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start watching all configured folders."""
        if self._running:
            return

        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer
        except ImportError:
            _log.warning("watchdog not installed; real-time file watching disabled")
            return

        if not self.config.folders:
            _log.info("No folders configured for watching")
            return

        self._watched_folders.clear()
        for folder_path in self.config.folders:
            resolved = str(Path(folder_path).resolve())
            if os.path.isdir(resolved):
                filter_rules = self.config.get_folder_filter(resolved)
                self._watched_folders[resolved] = WatchedFolder(resolved, filter_rules)
            else:
                _log.warning("Watch folder does not exist: %s", folder_path)

        if not self._watched_folders:
            return

        class _Handler(FileSystemEventHandler):
            def __init__(self, watcher: FolderWatcher):
                super().__init__()
                self._watcher = watcher

            def on_created(self, event):
                self._watcher._handle_event(str(event.src_path))

            def on_modified(self, event):
                self._watcher._handle_event(str(event.src_path))

        self._observer = Observer()
        handler = _Handler(self)
        for folder in self._watched_folders.values():
            self._observer.schedule(handler, folder.path, recursive=True)
            _log.info("Watching folder: %s", folder.path)

        self._observer.start()
        self._running = True
        _log.info("File watcher started (%d folders)", len(self._watched_folders))

    def stop(self) -> None:
        """Stop the file watcher."""
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        self._queue.shutdown()
        _log.info("File watcher stopped")

    def flush_pending(self) -> list[str]:
        """Flush any files currently in the debounce queue."""
        return self._queue.flush()

    def _handle_event(self, src_path: str) -> None:
        """Process a watchdog event."""
        if not self._running:
            return

        # Find which folder this belongs to
        for folder in self._watched_folders.values():
            if folder.should_accept_event(src_path):
                _log.debug("Watcher queued: %s", src_path)
                self._queue.add_file(src_path)
                break
