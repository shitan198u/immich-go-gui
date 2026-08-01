import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from core import (
    CommandPlan,
    build_plan_from_state,
    create_lock,
    get_binary_path,
    load_binary_metadata,
    release_lock,
)
from core.terminal_launcher import launch_external_terminal


class ExecutionMixin:
    def build_plan(self, dry_run: bool) -> CommandPlan:
        tab_key = self._get_active_tab_key()
        if tab_key == "config":
            return CommandPlan(errors=["No executable tab selected."], tab_key=tab_key)

        config_state = self._collect_config_state()
        tab_state = self._collect_tab_state(tab_key)
        advanced_state = self._collect_advanced_state(tab_key)

        binary_path = getattr(self, "binary_path", "")
        if not binary_path:
            binary_path = get_binary_path(load_binary_metadata()) or "./immich-go"

        return build_plan_from_state(
            tab_key=tab_key,
            config_state=config_state,
            tab_state=tab_state,
            binary_path=binary_path,
            dry_run=dry_run,
            advanced_state=advanced_state,
        )

    def build_command(self, dry_run: bool) -> list[str]:
        """Backwards-compatible wrapper returning plan.argv."""
        return self.build_plan(dry_run).argv

    def run_command(self, plan: CommandPlan):
        if plan.errors:
            QMessageBox.critical(
                self, "Command Build Errors", "\n".join(f"• {e}" for e in plan.errors)
            )
            return

        binary_path = plan.binary_path or getattr(self, "binary_path", "./immich-go")
        try:
            resolved = Path(binary_path).expanduser().resolve()
            if resolved.is_file():
                binary_path = str(resolved)
        except OSError:
            resolved = Path(binary_path)

        if not os.path.isfile(binary_path) and not self.update_binary():
            QMessageBox.critical(
                self, "Error", "Immich-Go binary is missing or not executable."
            )
            return

        if not sys.platform.startswith("win") and not os.access(binary_path, os.X_OK):
            QMessageBox.critical(
                self, "Error", "Immich-Go binary exists but is not executable."
            )
            return

        plan.binary_path = binary_path

        if hasattr(self, "log"):
            self.log.info(
                "Launching: tab=%s argv=%s env_keys=%s",
                plan.tab_key,
                plan.display_argv,
                sorted(plan.env.keys()),
            )

        summary = f"{plan.tab_key}"
        if plan.argv:
            summary = " ".join(plan.argv[:3])

        lock_path = create_lock(
            tab_key=plan.tab_key,
            command_summary=summary,
            binary_path=binary_path,
        )

        pref_term = getattr(self.app_config, "preferred_terminal", "auto")
        full_cmd = [binary_path] + plan.argv

        res = launch_external_terminal(
            command=full_cmd,
            env=plan.env,
            lock_path=lock_path,
            preferred_terminal=pref_term,
        )

        if not res.ok:
            release_lock(lock_path)
            QMessageBox.critical(self, "Error Launching Terminal", res.message)
            self.btn_run.setEnabled(True)
            self.btn_dry_run.setEnabled(True)
            return

        self.active_lock_paths = {lock_path}
        self.active_lock_path = lock_path
        self.running_process = True
        self.btn_run.setEnabled(False)
        self.btn_dry_run.setEnabled(False)
        self._start_process_timer()
        self.update_status()
