"""External terminal launching logic for Immich-Go GUI.

Pure Python module, Qt-free.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

from .process_tracker import update_lock


from datetime import datetime, timezone

@dataclass
class LaunchResult:
    ok: bool
    message: str = ""


def cleanup_stale_temp_dirs(max_age_hours: int = 24) -> int:
    """Removes abandoned temporary run directories older than max_age_hours."""
    temp_root = Path(tempfile.gettempdir())
    now = datetime.now(timezone.utc).timestamp()
    threshold = now - (max_age_hours * 3600)
    cleaned_count = 0

    try:
        for item in temp_root.glob("immich-go-run-*"):
            if item.is_dir():
                try:
                    mtime = item.stat().st_mtime
                    if mtime < threshold:
                        shutil.rmtree(item, ignore_errors=True)
                        cleaned_count += 1
                except Exception:
                    pass
    except Exception:
        pass

    return cleaned_count


def _quote_sh_env_val(val: str) -> str:
    """Escapes string value for bash export."""
    return "'" + val.replace("'", "'\"'\"'") + "'"


def launch_external_terminal(
    command: list[str],
    env: dict[str, str],
    lock_path: Path,
    preferred_terminal: str = "auto",
) -> LaunchResult:
    """Launches command in an external terminal window without exposing secrets on CLI."""
    if not command:
        return LaunchResult(ok=False, message="Empty command passed to terminal launcher.")

    l_path = Path(lock_path).resolve()

    if sys.platform.startswith("win"):
        # Windows console execution
        try:
            cmd_str = subprocess.list2cmdline(command)
            bat_path = l_path.with_suffix(".bat")
            bat_content = (
                f"@echo off\n"
                f'cd /d "%~dp0"\n'
                f"{cmd_str}\n"
                f"set ERR=%ERRORLEVEL%\n"
                f'del /f "{l_path}" 2>nul\n'
                f'del /f "{l_path.with_suffix(".bat")}" 2>nul\n'
                f"echo.\n"
                f"echo immich-go exited with code %ERR%\n"
            )
            bat_path.write_text(bat_content, encoding="utf-8")

            CREATE_NEW_CONSOLE = 0x00000010
            proc = subprocess.Popen(
                ["cmd", "/k", str(bat_path)],
                creationflags=CREATE_NEW_CONSOLE,
                env=env,
            )
            update_lock(l_path, terminal_pid=proc.pid)
            return LaunchResult(ok=True, message="External terminal launched successfully.")
        except Exception as e:
            return LaunchResult(ok=False, message=f"Failed to launch Windows terminal: {str(e)}")

    # Linux / macOS POSIX execution
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix="immich-go-run-"))
        if os.name == "posix":
            try:
                os.chmod(temp_dir, 0o700)
            except OSError:
                pass

        env_sh_path = temp_dir / "env.sh"
        run_sh_path = temp_dir / "run.sh"

        # Export all IMMICH_GO_* environment variables to env.sh
        env_lines = []
        for k, v in sorted(env.items()):
            if k.startswith("IMMICH_GO_"):
                env_lines.append(f"export {k}={_quote_sh_env_val(v)}")

        env_sh_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
        if os.name == "posix":
            try:
                os.chmod(env_sh_path, 0o600)
            except OSError:
                pass

        pid_file_path = l_path.with_suffix(".pid")
        hb_file_path = l_path.with_suffix(".heartbeat")

        cmd_quoted = " ".join(shlex.quote(c) for c in command)
        run_sh_content = (
            "#!/usr/bin/env bash\n"
            f"PID_FILE={shlex.quote(str(pid_file_path))}\n"
            f"HB_FILE={shlex.quote(str(hb_file_path))}\n"
            f"LOCK_FILE={shlex.quote(str(l_path))}\n"
            f"ENV_FILE={shlex.quote(str(env_sh_path))}\n"
            f"TEMP_DIR={shlex.quote(str(temp_dir))}\n"
            "\n"
            'echo $$ > "$PID_FILE"\n'
            "(\n"
            "  while true; do\n"
            '    touch "$HB_FILE" 2>/dev/null\n'
            "    sleep 10\n"
            "  done\n"
            ") &\n"
            "HB_PID=$!\n"
            "\n"
            'SAFE_DIR="$HOME"\n'
            '[ -d "$SAFE_DIR" ] || SAFE_DIR=/\n'
            'cd "$SAFE_DIR"\n'
            "\n"
            "set -a\n"
            'source "$ENV_FILE"\n'
            "set +a\n"
            "\n"
            "cleanup() {\n"
            '  kill "$HB_PID" 2>/dev/null\n'
            '  rm -f "$PID_FILE" "$HB_FILE" "$LOCK_FILE" "$ENV_FILE"\n'
            "}\n"
            "\n"
            "trap cleanup EXIT INT TERM\n"
            f"{cmd_quoted}\n"
            "code=$?\n"
            "\n"
            "trap - EXIT INT TERM\n"
            "cleanup\n"
            "\n"
            'echo ""\n'
            'echo "immich-go exited with code $code"\n'
            "exec bash\n"
        )

        run_sh_path.write_text(run_sh_content, encoding="utf-8")
        if os.name == "posix":
            try:
                os.chmod(run_sh_path, 0o700)
            except OSError:
                pass

        # macOS execution via osascript
        if sys.platform == "darwin":
            proc = subprocess.Popen([
                "osascript",
                "-e", "on run argv",
                "-e", 'tell application "Terminal" to do script (item 1 of argv)',
                "-e", "end run",
                str(run_sh_path),
            ])
            update_lock(l_path, terminal_pid=proc.pid)
            return LaunchResult(ok=True, message="Terminal launched on macOS.")

        # Linux execution with terminal discovery order
        terminals_to_try = []
        if preferred_terminal and preferred_terminal != "auto":
            terminals_to_try.append(preferred_terminal)

        terminals_to_try.extend([
            "x-terminal-emulator",
            "gnome-terminal",
            "konsole",
            "xfce4-terminal",
            "xterm",
        ])

        launched_proc = None
        for term in terminals_to_try:
            if shutil.which(term):
                try:
                    if term == "gnome-terminal":
                        launched_proc = subprocess.Popen([term, "--", str(run_sh_path)])
                    elif term == "xterm":
                        launched_proc = subprocess.Popen([term, "-hold", "-e", str(run_sh_path)])
                    else:
                        launched_proc = subprocess.Popen([term, "-e", str(run_sh_path)])
                    break
                except Exception:
                    continue

        if not launched_proc:
            # Fallback cleanup on launch failure
            try:
                if l_path.exists():
                    l_path.unlink()
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            return LaunchResult(
                ok=False,
                message="No supported terminal emulator found (tried gnome-terminal, konsole, xfce4-terminal, xterm).",
            )

        update_lock(l_path, terminal_pid=launched_proc.pid)
        return LaunchResult(ok=True, message="Terminal launched successfully.")

    except Exception as e:
        return LaunchResult(ok=False, message=f"Terminal launch failed: {str(e)}")
