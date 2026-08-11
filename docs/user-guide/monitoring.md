# Backup Monitor

The **Monitor** tab (sidebar group **BACKUP**) runs **background monitoring** of local folders and uploads new media to Immich automatically — without opening a terminal window. It combines:

- **Real-time file watching** — upload files as they appear in watched folders.
- **Scheduled scans** — a weekly incremental scan and a monthly full rescan.
- **Network awareness** — pause uploads on metered connections or away from allowed Wi-Fi.
- **Activity-aware pauses** — auto-pause while you game, edit video, or run fullscreen apps.
- **System tray operation** — keep the app running minimized so monitoring continues.

Monitor runs are **separate from the Upload tab**. They run immich-go as a hidden background process with secrets delivered through environment variables (never command-line args), so nothing is shown in a terminal and credentials stay out of `argv`.

## Enabling the Monitor

1. Open the **Monitor** tab and tick **Enable Backup Monitor** (the master switch). This keeps the app available for system-tray operation and starts the scheduler and watcher.
2. Add one or more **folders to watch** under **Watcher**, either by typing a path and clicking **Add** or using **Browse…**.
3. Choose a **Network** upload policy and, if needed, configure the **Options** and **Schedule**.
4. Configure Immich credentials on the **Config** tab (server URL + API key). Monitor runs reuse those credentials.

!!! note "Two things must be true for monitoring to run"
    The master **Enable Backup Monitor** switch must be on **and** at least one watched folder must exist. Some options (like *Start minimized to tray*) only apply when a system tray is available.

## The Monitor Tab

| Section | What it does |
|---------|--------------|
| **Progress card** | Status line (`Idle`, `Running`, `Paused`, `Complete`) plus per-folder progress, the current file, and uploaded/skipped/failed counts. |
| **Controls** | **Run Now** (incremental), **Full Rescan Now**, **Pause / Resume**, **Cancel**. |
| **Watcher** | Folder list with **Add** / **Browse…** / **Remove Selected**. |
| **Watcher status** | Colored indicator showing whether real-time file watching is active and how many folders are monitored. |
| **Schedule** | Weekly incremental scan (day/hour/minute) and monthly full rescan (day/hour/minute), each with its own **Enabled** toggle. |
| **Network** | Upload policy and allowed SSIDs. |
| **Options** | Concurrency, days back, watcher debounce, and background-behavior toggles. |
| **Advanced Flags** | Reuses the `upload-folder` flag schema so you can pass extra immich-go options to monitor runs (stored separately from the Upload tab). |
| **Activity** | Live, color-coded feed of upload events and a **Clear** button. |

### Watcher Status

The status dot and text reflect the real-time file watcher:

- **Active** (green) — watching *N* folder(s).
- **Inactive** (muted) — e.g. *Monitor disabled*, *Real-time file watching disabled*, or *No folders configured*.
- **Error** (red) — the watcher failed to start.

### Activity Feed

Each monitor run, watcher batch, and error is appended to the **Activity** feed with folder context and severity coloring (info, warn, error, success, progress, summary). The feed caps at 500 entries and auto-scrolls; use **Clear** to empty it.

## Watched Folders & File Filtering

Real-time watching is handled by a filesystem watcher (via the `watchdog` library) that monitors watched folders **recursively**. Changes are batched with a **debounce** window (default 30 s, configurable 5–300 s) before an upload starts, so a burst of file changes is uploaded together rather than one upload per file.

Files are filtered before upload:

- **Hidden files** (leading `.`) and **system files** (`thumbs.db`, `desktop.ini`, `~$` Office locks) are skipped by default.
- A set of common junk/thumbnail directories is excluded by default (e.g. `@eaDir`, `thumbnails`, `$RECYCLE.BIN`, `System Volume Information`, Lightroom Catalog, Recently Deleted).
- You can define per-folder include/exclude extensions, min/max file size, and custom glob exclude patterns via the Advanced Flags / filter configuration.

Whether a file counts toward an incremental scan is decided against the **folder's last successful upload time** (falling back to the **Days back** window when there is no prior success yet).

## Scheduling

Runs are triggered two ways: on a schedule, or manually.

| Run type | Trigger | Scope |
|----------|---------|-------|
| **Weekly incremental scan** | Scheduled (day/hour/min) or **Run Now** | Uploads files modified since the folder's last successful upload. |
| **Monthly full rescan** | Scheduled (day/hour/min) or **Full Rescan Now** | Re-scans everything — used to catch files a watcher or incremental scan may have missed. |

Schedules are evaluated every 30 seconds while the monitor is on. Each occurrence fires **exactly once, even across app restarts** (the GUI persists a "last handled" marker for the weekly and monthly schedules in `monitor_state.json`).

## Network Policy

| Policy | Behavior |
|--------|----------|
| **Always (any network)** | Upload regardless of connection. Offline still pauses. |
| **No metered connections** | Skip uploads while on a metered connection. |
| **Only specific Wi-Fi** | Only upload when connected to one of the **Allowed SSIDs** (comma-separated). |

The GUI checks network state every 60 seconds and auto-pauses/resumes uploads accordingly. If it cannot determine the network, it **pauses** rather than risk uploading unexpectedly.

!!! warning "Metered-connection detection is limited"
    Reliable metered-connection detection depends on platform APIs and is not fully implemented yet. On systems where it cannot be determined, the **No metered connections** policy may not block uploads. SSID matching and offline detection are functional.

## Activity-Based Auto-Pause

The monitor can detect high-activity states (gaming, video editing, fullscreen apps) and pause uploads while you use your machine, then resume after a quiet period.

| Detection method | How it works |
|------------------|--------------|
| **Process list** | Pauses when a monitored process runs (e.g. `gamingservices.exe`, `obs64.exe`, `premiere.exe`, `afterfx.exe`, `resolve.exe`, `blender.exe`, `photoshop.exe`). |
| **CPU threshold** | Pauses when sustained CPU usage stays above the configured percent. |
| **GPU threshold** | Pauses when GPU usage stays above the configured percent. |
| **Fullscreen** | Pauses when a fullscreen application is in the foreground. |

Two grace periods control responsiveness:

- **Activity grace** (default 30 s) — how long activity must persist before pausing (avoids pausing on brief spikes).
- **Resume grace** (default 60 s) — how long the system must be quiet before uploads resume.

Detection is best-effort and depends on platform support (for example, GPU/fullscreen detection is Windows-oriented). You can disable activity pausing entirely.

## Retries

A failed folder upload is retried with exponential backoff. Defaults: **4 retries** with delays of **1, 5, 15, 30 minutes** between attempts. Per-folder last-success timestamps and retry counts are persisted so a folder that failed earlier is retried without re-uploading work already completed.

## Running in the Background

While the monitor is enabled you can keep the GUI out of the way:

- **Close to system tray when monitor is enabled** — closing the main window hides it to the tray instead of quitting; right-click the tray icon to reopen or quit.
- **Start minimized to tray** — launch hidden, ready to monitor.
- **Start monitor with Windows** — launch the app / start monitoring at logon (Windows).

The tray icon shows the monitor's status (Idle / Running / Paused) and double-clicking it reopens the main window.

Use the master **Enable Backup Monitor** switch to completely stop all background activity (watcher, scheduler, and network checks).

## Where Data Is Stored

Monitor settings are **per profile** and stored beside that profile's config:

| File | Purpose |
|------|---------|
| `monitor_config.json` | Monitor settings (folders, schedule, network policy, activity rules, retries, tray options, advanced flags). |
| `monitor_state.json` | Runtime state: per-folder last-success timestamps, retry counts/errors, pending files, last run results, and scheduled-occurrence markers. |

Individual upload logs are written under `{config_dir}/logs/` as `upload-{timestamp}-{folder}.log`. See [Config Schema](../reference/config-schema.md) for config locations.

## Related

- [Configuration](configuration.md) — Server credentials and binary setup
- [Upload Workflows](upload-workflows.md) — One-off uploads from the Upload tab
- [Troubleshooting](troubleshooting.md) — Common issues
- [Glossary](glossary.md) — Monitor-related terms
