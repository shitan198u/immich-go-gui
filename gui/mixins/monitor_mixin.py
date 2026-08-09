"""Monitor mixin for ImmichGoGUI — orchestrates folder watching and backup scheduling.

Wires together the file watcher, activity monitor, network awareness,
folder runner, and scheduler into a cohesive backup subsystem.
"""

import os
import threading
from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from core.config_manager import get_secret_with_fallback
from core.folder_runner import (
    RunnerState,
    UploadResult,
    count_pending_files,
    run_folder_upload,
)
from core.folder_watcher import FolderWatcher
from core.monitor_config import MonitorConfig, MonitorConfigStore, NetworkPolicy
from core.monitor_state import MonitorState, MonitorStateStore
from core.network_awareness import NetworkMonitor, NetworkStatus


class MonitorSignals(QObject):
    """Qt signals for the monitor subsystem (thread-safe)."""

    log_entry = Signal(str, str, str)  # folder, message, level
    progress_update = Signal(str, int, int, str, int, int, int)
    # folder, completed, total, current_file, uploaded, skipped, failed
    state_changed = Signal(str)  # idle, running, paused, error, complete
    paused_reason = Signal(str)  # reason for pause
    run_requested = Signal(bool, str)  # full_rescan, trigger


class MonitorMixin:
    """Mixin that adds backup monitoring capability to ImmichGoGUI."""

    def __init__(self) -> None:
        # Called after main window init — override in layout mixin
        pass

    def init_monitor(self) -> None:
        """Initialize the monitoring subsystem."""
        self.monitor_config = self._load_monitor_config()
        self.monitor_state = MonitorStateStore.load()
        self._monitor_runner_state = RunnerState()
        self._monitor_signals = MonitorSignals()
        self._monitor_thread: threading.Thread | None = None
        self._monitor_semaphore = threading.Semaphore(
            self.monitor_config.max_parallel_folders
        )
        self._auto_pause_reason: str | None = None

        # Watcher
        self._watcher = FolderWatcher(
            self.monitor_config,
            on_batch_ready=self._on_watcher_batch_ready,
        )
        if hasattr(self, "watcher_status"):
            self.watcher_status.set_inactive("Monitor disabled")
        if hasattr(self, "file_watcher_check"):
            self.file_watcher_check.toggled.connect(self._on_file_watcher_toggled)
        if hasattr(self, "folder_list"):
            self.folder_list.folder_added.connect(self._on_monitor_folder_changed)
            self.folder_list.folder_removed.connect(self._on_monitor_folder_changed)

        # Scheduler timer
        self._scheduler_timer = QTimer(self)
        self._scheduler_timer.setInterval(30_000)  # 30 seconds
        self._scheduler_timer.timeout.connect(self._on_scheduler_tick)

        # Network check timer
        self._network_monitor = NetworkMonitor(
            self.monitor_config.network_policy,
            self.monitor_config.allowed_ssids,
        )
        self._network_timer = QTimer(self)
        self._network_timer.setInterval(60_000)  # 60 seconds
        self._network_timer.timeout.connect(self._on_network_tick)

        # Wire signals
        self._monitor_signals.log_entry.connect(self._on_monitor_log)
        self._monitor_signals.progress_update.connect(self._on_progress_update)
        self._monitor_signals.state_changed.connect(self._on_monitor_state_changed)
        self._monitor_signals.paused_reason.connect(self._on_paused_reason)
        # Watchdog invokes its debounce callback on a worker thread.  Route
        # run orchestration back to the GUI thread before it touches Qt
        # widgets or runner state.
        self._monitor_signals.run_requested.connect(self._start_run)

        # Connect buttons
        if hasattr(self, "btn_monitor_run"):
            self.btn_monitor_run.clicked.connect(self._on_run_now)
        if hasattr(self, "btn_monitor_full"):
            self.btn_monitor_full.clicked.connect(self._on_full_rescan)
        if hasattr(self, "btn_monitor_pause"):
            self.btn_monitor_pause.clicked.connect(self._on_toggle_pause)
        if hasattr(self, "btn_monitor_cancel"):
            self.btn_monitor_cancel.clicked.connect(self._on_cancel)

        # Start
        self._configure_monitor_activation()

    def _load_monitor_config(self) -> MonitorConfig:
        """Load monitor config from saved state or defaults."""
        return MonitorConfigStore.load(
            getattr(self.app_config, "profile_name", "default")
        )

    def _save_monitor_config(self) -> None:
        """Persist monitor config."""
        MonitorConfigStore.save(
            self.monitor_config, getattr(self.app_config, "profile_name", "default")
        )

    def _start_watcher(self) -> None:
        """Start the file watcher if enabled."""
        if not self.monitor_config.monitor_enabled:
            self._set_watcher_inactive("Monitor disabled")
            return
        if not self.monitor_config.file_watcher_enabled:
            self._set_watcher_inactive("Real-time file watching disabled")
            return
        if not self.monitor_config.folders:
            self._set_watcher_inactive("No folders configured")
            return
        try:
            self._watcher.start()
            if hasattr(self, "watcher_status") and self._watcher.running:
                self.watcher_status.set_active(len(self.monitor_config.folders))
            elif hasattr(self, "watcher_status"):
                self.watcher_status.set_inactive("No folders configured")
        except Exception as e:
            if hasattr(self, "watcher_status"):
                self.watcher_status.set_error(f"Watcher error: {e}")

    def _set_watcher_inactive(self, reason: str) -> None:
        if hasattr(self, "watcher_status"):
            self.watcher_status.set_inactive(reason)

    def _refresh_watcher_status(self) -> None:
        # Configuration loading runs before init_monitor during startup.
        # Do not attempt to start the watcher until init_monitor has created
        # the watcher and all monitor state.  This method is called from
        # persistence while the window is still being constructed.
        if not hasattr(self, "monitor_config") or not hasattr(self, "_watcher"):
            self._set_watcher_inactive("Monitor disabled")
            return
        self._start_watcher()

    def _on_file_watcher_toggled(self, enabled: bool) -> None:
        self.monitor_config.file_watcher_enabled = enabled
        self._save_monitor_config()
        self._configure_monitor_activation()

    def _on_monitor_folder_changed(self, *_args) -> None:
        self._sync_folders_from_ui()
        self._save_monitor_config()
        self._configure_monitor_activation()

    def _start_scheduler(self) -> None:
        """Start the scheduler timer."""
        if self.monitor_config.monitor_enabled:
            self._scheduler_timer.start()

    def _configure_monitor_activation(self) -> None:
        """Apply the master monitor switch to background services."""
        if hasattr(self, "_watcher") and self._watcher.running:
            self._watcher.stop()
        if self.monitor_config.monitor_enabled:
            self._start_watcher()
            self._start_scheduler()
            self._start_network_monitor()
        else:
            self._scheduler_timer.stop()
            self._network_timer.stop()
            if hasattr(self, "_watcher"):
                self._watcher.stop()
            self._set_watcher_inactive("Monitor disabled")

    def set_monitor_enabled(self, enabled: bool) -> None:
        """Enable or disable scheduled/background monitoring."""
        self.monitor_config.monitor_enabled = enabled
        self._save_monitor_config()
        if hasattr(self, "_save_monitor_state"):
            self._save_monitor_state()
        self._configure_monitor_activation()

    def _start_network_monitor(self) -> None:
        """Start network monitoring."""
        if self.monitor_config.network_policy != NetworkPolicy.ALWAYS:
            self._network_timer.start()

    # ── Watcher Callback ───────────────────────────────────

    def _on_watcher_batch_ready(self, files: list[str]) -> None:
        """Called when the watcher debounce window fires."""
        if not files:
            return
        if self._auto_pause_reason:
            self._monitor_signals.log_entry.emit(
                "",
                f"Deferred {len(files)} changed files (paused: {self._auto_pause_reason})",
                "warn",
            )
            return

        self._monitor_signals.log_entry.emit(
            "",
            f"File watcher detected {len(files)} changed files — queuing upload",
            "info",
        )

        # Queue files by folder
        from collections import defaultdict

        by_folder: defaultdict[str, list[str]] = defaultdict(list)
        for f in files:
            # Find which watched folder this file belongs to
            for wf in self.monitor_config.folders:
                resolved = str(Path(wf).resolve())
                if f.startswith(resolved):
                    by_folder[resolved].append(f)
                    break

        for folder, folder_files in by_folder.items():
            folder_state = self.monitor_state.get_folder_state(folder)
            folder_state.pending_files.extend(folder_files)
        MonitorStateStore.save(self.monitor_state)

        # The debounce callback runs on threading.Timer's worker thread.
        # Request the run through a Qt signal so _start_run executes on the
        # GUI thread rather than mutating widgets from the watcher thread.
        self._monitor_signals.run_requested.emit(False, "watcher")

    # ── Scheduler ──────────────────────────────────────────

    def _on_scheduler_tick(self) -> None:
        """Check if a scheduled run is due."""
        if self._monitor_runner_state.running:
            return
        if self._auto_pause_reason:
            return

        now = datetime.now(UTC)
        cfg = self.monitor_config

        # Weekly
        if cfg.scheduled_weekly_enabled:
            next_weekly = self._next_weekly_time(now)
            if now >= next_weekly:
                self._start_run(full_rescan=False, trigger="weekly")

        # Monthly
        if cfg.scheduled_monthly_enabled:
            next_monthly = self._next_monthly_time(now)
            if now >= next_monthly:
                self._start_run(full_rescan=True, trigger="monthly")

    def _next_weekly_time(self, from_dt: datetime) -> datetime:
        """Compute next weekly scheduled time."""
        cfg = self.monitor_config
        target_day = cfg.weekly_day
        target_hour = cfg.weekly_hour
        target_minute = cfg.weekly_minute
        days_ahead = target_day - from_dt.weekday()
        if days_ahead < 0:
            days_ahead += 7
        from datetime import timedelta

        candidate = (from_dt + timedelta(days=days_ahead)).replace(
            hour=target_hour, minute=target_minute, second=0, microsecond=0
        )
        if candidate <= from_dt:
            candidate += timedelta(days=7)
        return candidate

    def _next_monthly_time(self, from_dt: datetime) -> datetime:
        """Compute next monthly scheduled time."""
        from datetime import timedelta

        cfg = self.monitor_config
        target_day = max(1, min(cfg.monthly_rescan_day, 28))
        target_hour = cfg.monthly_rescan_hour
        target_minute = cfg.monthly_rescan_minute

        # This month
        try:
            candidate = from_dt.replace(
                day=target_day,
                hour=target_hour,
                minute=target_minute,
                second=0,
                microsecond=0,
            )
        except ValueError:
            candidate = from_dt.replace(day=28) + timedelta(days=4)

        if candidate <= from_dt:
            # Next month
            if from_dt.month == 12:
                candidate = from_dt.replace(
                    year=from_dt.year + 1,
                    month=1,
                    day=min(target_day, 31),
                    hour=target_hour,
                    minute=target_minute,
                    second=0,
                    microsecond=0,
                )
            else:
                candidate = from_dt.replace(
                    month=from_dt.month + 1,
                    day=min(target_day, 28),
                    hour=target_hour,
                    minute=target_minute,
                    second=0,
                    microsecond=0,
                )
        return candidate

    # ── Network ────────────────────────────────────────────

    def _on_network_tick(self) -> None:
        """Check network status and auto-pause/resume."""
        status = self._network_monitor.check_status()
        if status == NetworkStatus.ALLOWED:
            if self._auto_pause_reason and "network" in self._auto_pause_reason.lower():
                self._auto_pause_reason = None
                self._resume_uploads()
        elif status in (
            NetworkStatus.BLOCKED_METERED,
            NetworkStatus.BLOCKED_SSID,
            NetworkStatus.BLOCKED_OFFLINE,
            NetworkStatus.UNKNOWN,
        ):
            reason = {
                NetworkStatus.BLOCKED_METERED: "Network paused: metered connection",
                NetworkStatus.BLOCKED_SSID: "Network paused: not on allowed SSID",
                NetworkStatus.BLOCKED_OFFLINE: "Network paused: offline",
            }.get(status, "Network paused")
            self._auto_pause_reason = reason
            self._pause_uploads(reason)

    # ── Run Controls ───────────────────────────────────────

    def _sync_folders_from_ui(self) -> None:
        """Sync the folder list from the UI widget into monitor_config."""
        if hasattr(self, "folder_list"):
            folders = self.folder_list.get_folders()
            # Pick up a path typed into the input box but not yet "Add"ed so
            # Run Now doesn't falsely report "no folders configured".
            pending = self.folder_list._folder_input.text().strip()
            if pending and pending not in folders:
                folders.append(pending)
            self.monitor_config.folders = folders

    def _on_run_now(self) -> None:
        """Manual 'Run Now' button."""
        if self._monitor_runner_state.running:
            return
        self._sync_folders_from_ui()
        if not self.monitor_config.folders:
            self._monitor_signals.log_entry.emit(
                "", "No folders configured for monitoring", "warn"
            )
            return
        self._start_run(full_rescan=False, trigger="manual")

    def _on_full_rescan(self) -> None:
        """Manual 'Full Rescan' button."""
        if self._monitor_runner_state.running:
            return
        self._sync_folders_from_ui()
        if not self.monitor_config.folders:
            self._monitor_signals.log_entry.emit(
                "", "No folders configured for monitoring", "warn"
            )
            return
        self._start_run(full_rescan=True, trigger="manual-full")

    def _on_toggle_pause(self) -> None:
        """Toggle pause/resume."""
        if not self._monitor_runner_state.running:
            return
        if self._monitor_runner_state.paused:
            self._resume_uploads()
        else:
            self._pause_uploads("Manually paused")

    def _on_cancel(self) -> None:
        """Cancel current run."""
        if not self._monitor_runner_state.running:
            return
        self._monitor_runner_state.cancel_event.set()
        self._monitor_runner_state.pause_event.set()  # unblock
        self._monitor_signals.log_entry.emit("", "Cancelling upload run...", "warn")

    def _pause_uploads(self, reason: str) -> None:
        """Pause all upload activity."""
        self._monitor_runner_state.paused = True
        self._monitor_runner_state.pause_event.clear()
        self._monitor_signals.paused_reason.emit(reason)
        if hasattr(self, "btn_monitor_pause"):
            self.btn_monitor_pause.setText("Resume")

    def _resume_uploads(self) -> None:
        """Resume upload activity."""
        self._monitor_runner_state.paused = False
        self._monitor_runner_state.pause_event.set()
        if hasattr(self, "btn_monitor_pause"):
            self.btn_monitor_pause.setText("Pause")
        if hasattr(self, "progress_card"):
            self.progress_card.set_running(
                self._monitor_runner_state.current_folder,
                self._monitor_runner_state.completed_folders,
                self._monitor_runner_state.total_folders,
            )

    # ── Run Orchestration ──────────────────────────────────

    def _start_run(self, full_rescan: bool = False, trigger: str = "manual") -> None:
        """Start a batch upload run across all folders."""
        if self._monitor_runner_state.running:
            return

        folders = [f for f in self.monitor_config.folders if os.path.isdir(f)]
        if not folders:
            self._monitor_signals.log_entry.emit(
                "", f"Run not started: no existing watched folders ({trigger})", "warn"
            )
            return

        self._monitor_runner_state.reset()
        self._monitor_runner_state.total_folders = len(folders)

        self._monitor_signals.state_changed.emit("running")
        self._monitor_signals.log_entry.emit(
            "",
            f"Run started: trigger={trigger} full_rescan={full_rescan} "
            f"folders={len(folders)}",
            "summary",
        )

        # Progress card
        if hasattr(self, "progress_card"):
            self.progress_card.set_running(
                os.path.basename(folders[0]) or folders[0], 0, len(folders)
            )

        # Enable controls
        if hasattr(self, "btn_monitor_pause"):
            self.btn_monitor_pause.setEnabled(True)
            self.btn_monitor_pause.setText("Pause")
        if hasattr(self, "btn_monitor_cancel"):
            self.btn_monitor_cancel.setEnabled(True)
        if hasattr(self, "btn_monitor_run"):
            self.btn_monitor_run.setEnabled(False)
        if hasattr(self, "btn_monitor_full"):
            self.btn_monitor_full.setEnabled(False)

        # Run in thread
        self._monitor_thread = threading.Thread(
            target=self._run_all_folders,
            args=(folders, full_rescan, trigger),
            daemon=True,
        )
        self._monitor_thread.start()

    def _run_all_folders(
        self, folders: list[str], full_rescan: bool, trigger: str
    ) -> None:
        """Thread target: upload all folders with parallelism."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        state = self.monitor_state
        cfg = self.monitor_config
        rs = self._monitor_runner_state
        state.last_run_started_utc = datetime.now(UTC).isoformat()
        MonitorStateStore.save(state)

        # Resolve secrets from the config tab UI
        server_url = ""
        api_key = ""
        config_inputs = self.inputs.get("config", {})
        server_widget = config_inputs.get("server")
        if server_widget and hasattr(server_widget, "text"):
            server_url = server_widget.text().strip()
        api_key_widget = config_inputs.get("api_key")
        if api_key_widget and hasattr(api_key_widget, "text"):
            api_key = api_key_widget.text().strip()
        # Fall back to stored config if UI not available
        if not server_url and hasattr(self, "app_config"):
            server_url = self.app_config.server_url or ""
        if not api_key and hasattr(self, "app_config"):
            api_key = get_secret_with_fallback(
                profile_name=getattr(self.app_config, "profile_name", "default"),
                key="api_key",
                provider=self.app_config.secrets_provider,
            )

        from core.config_manager import default_config_dir

        log_dir = cfg.log_dir or os.path.join(str(default_config_dir()), "logs")

        total_uploaded = 0
        total_skipped = 0
        total_failed_folders = 0
        completed = 0

        max_workers = max(1, min(cfg.max_parallel_folders, len(folders)))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for folder in folders:
                future = executor.submit(
                    self._run_single_folder,
                    folder,
                    cfg,
                    server_url,
                    api_key,
                    full_rescan,
                    log_dir,
                    state,
                    rs,
                )
                futures[future] = folder

            for future in as_completed(futures):
                folder = futures[future]
                try:
                    result: UploadResult = future.result()
                except Exception as exc:
                    result = UploadResult(
                        folder=folder, success=False, message=f"Exception: {exc}"
                    )

                completed += 1
                rs.completed_folders = completed

                if result.success:
                    folder_state = state.get_folder_state(folder)
                    folder_state.last_success_utc = datetime.now(UTC).isoformat()
                    folder_state.retry_count = 0
                    folder_state.last_error = None
                    folder_state.pending_files.clear()
                    total_uploaded += result.files_uploaded
                    total_skipped += result.files_skipped
                else:
                    total_failed_folders += 1
                    folder_state = state.get_folder_state(folder)
                    folder_state.retry_count += 1
                    folder_state.last_error = result.message

                MonitorStateStore.save(state)

                self._monitor_signals.progress_update.emit(
                    os.path.basename(folder) or folder,
                    completed,
                    len(folders),
                    rs.current_file,
                    result.files_uploaded,
                    result.files_skipped,
                    result.files_errored,
                )

                self._monitor_signals.log_entry.emit(
                    os.path.basename(folder) or folder,
                    f"Folder complete: {result.message} "
                    f"({result.duration_seconds:.1f}s)",
                    "success" if result.success else "error",
                )

                # Check cancel
                if rs.cancel_event.is_set():
                    break

        # Complete
        rs.running = False
        rs.current_file = ""
        rs.current_folder = ""
        state.last_run_finished_utc = datetime.now(UTC).isoformat()
        if rs.cancel_event.is_set() and completed < len(folders):
            state.last_run_result = "cancelled"
        elif total_failed_folders == 0:
            state.last_run_result = "success"
        elif completed > total_failed_folders:
            state.last_run_result = "partial"
        else:
            state.last_run_result = "failure"
        MonitorStateStore.save(state)

        self._monitor_signals.state_changed.emit("complete")
        self._monitor_signals.log_entry.emit(
            "",
            f"Run complete: {total_uploaded} uploaded, {total_skipped} skipped, "
            f"{total_failed_folders} folders failed",
            "summary",
        )

    def _run_single_folder(
        self,
        folder: str,
        cfg: MonitorConfig,
        server_url: str,
        api_key: str,
        full_rescan: bool,
        log_dir: str,
        state: MonitorState,
        rs: RunnerState,
    ) -> UploadResult:
        """Run upload for a single folder."""
        from datetime import timedelta

        folder_state = state.get_folder_state(folder)

        if full_rescan:
            since = datetime.min.replace(tzinfo=UTC)
        elif folder_state.last_success_utc:
            try:
                since = datetime.fromisoformat(folder_state.last_success_utc)
            except (ValueError, TypeError):
                since = datetime.now(UTC) - timedelta(days=cfg.days_back)
        else:
            since = datetime.now(UTC) - timedelta(days=cfg.days_back)

        # Count pending files for duplicate awareness
        filter_rules = cfg.get_folder_filter(folder)
        pending_count = count_pending_files(folder, since, filter_rules)
        self._monitor_signals.log_entry.emit(
            os.path.basename(folder) or folder,
            f"Pre-scan: ~{pending_count} files since {since.strftime('%Y-%m-%d')}",
            "info",
        )

        # Monitor options are execution configuration, independent of global UI mode.
        advanced_state = cfg.advanced_state

        return run_folder_upload(
            folder=folder,
            config=cfg,
            server_url=server_url,
            api_key=api_key,
            since_utc=since,
            log_dir=log_dir,
            state=rs,
            on_log=lambda fk, msg: self._on_monitor_log(fk, msg, "info"),
            advanced_state=advanced_state,
        )

    # ── Signal Handlers ────────────────────────────────────

    def _on_monitor_log(self, folder: str, message: str, level: str = "info") -> None:
        """Handle a log entry from the monitor."""
        if hasattr(self, "activity_feed"):
            self.activity_feed.add_entry(folder, message, level)

    def _on_progress_update(
        self,
        folder: str,
        completed: int,
        total: int,
        current_file: str,
        uploaded: int,
        skipped: int,
        failed: int,
    ) -> None:
        """Handle a progress update."""
        self._monitor_runner_state.current_folder = folder
        self._monitor_runner_state.current_file = current_file
        if hasattr(self, "progress_card"):
            self.progress_card.set_running(
                folder,
                completed,
                total,
                uploaded=uploaded,
                skipped=skipped,
                failed=failed,
            )

    def _on_monitor_state_changed(self, new_state: str) -> None:
        """Handle state changes from the monitor."""
        if hasattr(self, "progress_card"):
            if new_state == "idle":
                self.progress_card.set_idle()
            elif new_state == "running":
                pass  # handled by progress_update
            elif new_state == "paused":
                self.progress_card.set_paused(self._auto_pause_reason or "")
            elif new_state == "complete":
                # Reset controls
                if hasattr(self, "btn_monitor_run"):
                    self.btn_monitor_run.setEnabled(True)
                if hasattr(self, "btn_monitor_full"):
                    self.btn_monitor_full.setEnabled(True)
                if hasattr(self, "btn_monitor_pause"):
                    self.btn_monitor_pause.setEnabled(False)
                    self.btn_monitor_pause.setText("Pause")
                if hasattr(self, "btn_monitor_cancel"):
                    self.btn_monitor_cancel.setEnabled(False)

    def _on_paused_reason(self, reason: str) -> None:
        """Handle auto-pause reason."""
        if hasattr(self, "progress_card"):
            self.progress_card.set_paused(reason)

    # ── Shutdown ───────────────────────────────────────────

    def shutdown_monitor(self) -> None:
        """Clean shutdown of the monitor subsystem."""
        self._monitor_runner_state.cancel_event.set()
        self._monitor_runner_state.pause_event.set()
        self._scheduler_timer.stop()
        self._network_timer.stop()
        if hasattr(self, "_watcher"):
            self._watcher.stop()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=10)
        if hasattr(self, "tray_manager"):
            self.tray_manager.shutdown()
        MonitorStateStore.save(self.monitor_state)
