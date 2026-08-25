"""External terminal launching logic for Immich-Go GUI.

Pure Python module, Qt-free.
"""

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .process_tracker import update_lock


@dataclass
class LaunchResult:
    ok: bool
    message: str = ""


def cleanup_stale_temp_dirs(max_age_hours: int = 24) -> int:
    """Removes abandoned temporary run directories older than max_age_hours."""
    temp_root = Path(tempfile.gettempdir())
    now = datetime.now(UTC).timestamp()
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


def _resolve_command_binary(command: list[str]) -> list[str]:
    """Resolve the binary path (argv[0]) to an absolute path when possible."""
    if not command:
        return command
    try:
        resolved = Path(command[0]).expanduser().resolve()
        if resolved.is_file():
            return [str(resolved)] + command[1:]
    except OSError:
        pass
    return command


def _write_posix_env_file(env_dir: Path, env: dict[str, str]) -> Path | None:
    """Write IMMICH_GO_* secrets to a restricted env.sh file for sourcing in run.sh."""
    immich_vars = {k: v for k, v in env.items() if k.startswith("IMMICH_GO_") and v}
    if not immich_vars:
        return None

    env_sh = env_dir / "env.sh"
    lines = ["#!/usr/bin/env bash\n"]
    for key, val in sorted(immich_vars.items()):
        lines.append(f"export {key}={_quote_sh_env_val(val)}\n")
    env_sh.write_text("".join(lines), encoding="utf-8")
    if os.name == "posix":
        try:
            os.chmod(env_sh, 0o600)
        except OSError:
            pass
    return env_sh


def launch_external_terminal(
    command: list[str],
    env: dict[str, str],
    lock_path: Path,
    preferred_terminal: str = "auto",
) -> LaunchResult:
    """Launches command in an external terminal window without exposing secrets on CLI."""
    if not command:
        return LaunchResult(
            ok=False, message="Empty command passed to terminal launcher."
        )

    command = _resolve_command_binary(command)
    l_path = Path(lock_path).resolve()

    if sys.platform.startswith("win"):
        # Windows console execution
        try:
            cmd_str = subprocess.list2cmdline(command)
            bat_path = l_path.with_suffix(".bat")
            hb_path = l_path.with_suffix(".heartbeat")
            bat_content = (
                f"@echo off\r\n"
                f'cd /d "%~dp0"\r\n'
                f'set "LOCK_FILE={l_path}"\r\n'
                f'set "HB_FILE={hb_path}"\r\n'
                f'start /b cmd /c "for /L %%i in (1,1,999999) do ('
                f'type nul > "%HB_FILE%" 2>nul & '
                f"timeout /t 10 /nobreak >nul & "
                f'if not exist "%LOCK_FILE%" exit)"\r\n'
                f"{cmd_str}\r\n"
                f"set ERR=%ERRORLEVEL%\r\n"
                f'del /f "%LOCK_FILE%" 2>nul\r\n'
                f'del /f "%HB_FILE%" 2>nul\r\n'
                # NOTE: do NOT delete the bat file here. Deleting a bat file
                # from within itself while running under "cmd /k" causes
                # Windows to print "The batch file cannot be found" when the
                # script ends. release_lock() in process_tracker.py already
                # cleans up the .bat sidecar when the lock is released.
                f"echo.\r\n"
                f"echo immich-go exited with code %ERR%\r\n"
            )
            bat_path.write_text(bat_content, encoding="utf-8")

            CREATE_NEW_CONSOLE = 0x00000010
            proc = subprocess.Popen(
                ["cmd", "/k", str(bat_path)],
                creationflags=CREATE_NEW_CONSOLE,
                env=env,
            )
            update_lock(l_path, terminal_pid=proc.pid)
            return LaunchResult(
                ok=True, message="External terminal launched successfully."
            )
        except Exception as e:
            return LaunchResult(
                ok=False, message=f"Failed to launch Windows terminal: {e!s}"
            )

    # Linux / macOS POSIX execution
    try:
        posix_env = os.environ.copy()
        posix_env.update(env)

        temp_dir = Path(tempfile.mkdtemp(prefix="immich-go-run-"))
        if os.name == "posix":
            try:
                os.chmod(temp_dir, 0o700)
            except OSError:
                pass

        run_sh_path = temp_dir / "run.sh"
        env_sh_path = _write_posix_env_file(temp_dir, env)

        pid_file_path = l_path.with_suffix(".pid")
        hb_file_path = l_path.with_suffix(".heartbeat")

        cmd_quoted = " ".join(shlex.quote(c) for c in command)
        env_setup = ""
        if env_sh_path is not None:
            env_setup = (
                f"ENV_FILE={shlex.quote(str(env_sh_path))}\n"
                'if [ -f "$ENV_FILE" ]; then\n'
                "  # shellcheck source=/dev/null\n"
                '  source "$ENV_FILE"\n'
                '  rm -f "$ENV_FILE"\n'
                "fi\n"
            )

        run_sh_content = (
            "#!/usr/bin/env bash\n"
            f"PID_FILE={shlex.quote(str(pid_file_path))}\n"
            f"HB_FILE={shlex.quote(str(hb_file_path))}\n"
            f"LOCK_FILE={shlex.quote(str(l_path))}\n"
            f"TEMP_DIR={shlex.quote(str(temp_dir))}\n"
            "\n"
            f"{env_setup}"
            'echo $$ > "$PID_FILE"\n'
            "(\n"
            "  while true; do\n"
            '    touch "$HB_FILE" 2>/dev/null\n'
            "    sleep 10\n"
            "  done\n"
            ") >/dev/null 2>&1 &\n"
            "HB_PID=$!\n"
            "\n"
            'SAFE_DIR="$HOME"\n'
            '[ -d "$SAFE_DIR" ] || SAFE_DIR=/\n'
            'cd "$SAFE_DIR"\n'
            "\n"
            "cleanup() {\n"
            '  kill "$HB_PID" 2>/dev/null\n'
            '  rm -f "$PID_FILE" "$HB_FILE" "$LOCK_FILE"\n'
            "}\n"
            "\n"
            "trap cleanup EXIT INT TERM HUP\n"
            f"{cmd_quoted}\n"
            "code=$?\n"
            "\n"
            "trap - EXIT INT TERM HUP\n"
            "cleanup\n"
            "\n"
            'echo ""\n'
            'echo "immich-go exited with code $code"\n'
            'if [ -z "${IMMICH_GO_GUI_HEADLESS:-}" ]; then\n'
            "  exec bash\n"
            "fi\n"
        )

        run_sh_content = run_sh_content.rstrip() + "\n"
        run_sh_path.write_text(run_sh_content, encoding="utf-8")
        if os.name == "posix":
            try:
                os.chmod(run_sh_path, 0o700)
            except OSError:
                pass

        # macOS execution via osascript
        if sys.platform == "darwin":
            proc = subprocess.Popen(
                [
                    "osascript",
                    "-e",
                    "on run argv",
                    "-e",
                    'tell application "Terminal" to do script (item 1 of argv)',
                    "-e",
                    "end run",
                    str(run_sh_path),
                ],
                env=posix_env,
            )
            update_lock(l_path, terminal_pid=proc.pid)
            return LaunchResult(ok=True, message="Terminal launched on macOS.")

        # Linux execution with terminal discovery order
        terminals_to_try = []
        if preferred_terminal and preferred_terminal != "auto":
            terminals_to_try.append(preferred_terminal)

        terminals_to_try.extend(
            [
                "x-terminal-emulator",
                "gnome-terminal",
                "konsole",
                "xfce4-terminal",
                "alacritty",
                "kitty",
                "xterm",
            ]
        )

        launched_proc = None
        for term in terminals_to_try:
            if shutil.which(term):
                try:
                    if term == "gnome-terminal":
                        launched_proc = subprocess.Popen(
                            [term, "--", str(run_sh_path)], env=posix_env
                        )
                    elif term == "xterm":
                        launched_proc = subprocess.Popen(
                            [term, "-hold", "-e", str(run_sh_path)], env=posix_env
                        )
                    else:
                        launched_proc = subprocess.Popen(
                            [term, "-e", str(run_sh_path)], env=posix_env
                        )
                    break
                except Exception:
                    continue

        if not launched_proc:
            try:
                if l_path.exists():
                    l_path.unlink()
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            return LaunchResult(
                ok=False,
                message="No supported terminal emulator found (tried x-terminal-emulator, gnome-terminal, konsole, xfce4-terminal, alacritty, kitty, xterm).",
            )

        update_lock(l_path, terminal_pid=launched_proc.pid)
        return LaunchResult(ok=True, message="Terminal launched successfully.")

    except Exception as e:
        return LaunchResult(ok=False, message=f"Terminal launch failed: {e!s}")
