"""Pure data structures and dataclasses for Immich-Go GUI core logic.

This module contains pure Python types only and MUST NOT import PySide6, Qt widgets,
or perform any file I/O or network operations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class VersionSupport(str, Enum):
    UNKNOWN = "unknown"
    UNSUPPORTED_OLD = "unsupported_old"
    TESTED = "tested"
    UNTESTED_BUT_MAY_WORK = "untested_but_may_work"
    UNTESTED_NEW = "untested_new"


class UpdateSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    BLOCKED = "blocked"


@dataclass
class ValidationResult:
    """Structured validation output for form states."""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


@dataclass
class CommandPlan:
    """Represents a fully resolved immich-go execution plan."""
    argv: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    display_argv: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    tab_key: str = ""
    dry_run: bool = False
    binary_path: str = ""


@dataclass
class BinaryStatus:
    """Status details for an immich-go binary."""
    state: str  # "ok" | "warn" | "err"
    card_text: str
    version_text: str
    support: VersionSupport = VersionSupport.UNKNOWN
    message: str = ""


@dataclass
class UpdateDecision:
    """Evaluation result for a software update attempt."""
    allowed: bool
    requires_confirmation: bool
    severity: UpdateSeverity
    message: str
    latest_version: str = ""
    current_version: str = ""


@dataclass
class AppConfig:
    """Application user configuration model."""
    schema_version: int = 2

    theme_mode: str = "system"
    advanced_mode: bool = False
    allow_untested_updates: bool = False

    server_url: str = ""
    skip_ssl: bool = False

    secrets_provider: str = "keyring"

    client_timeout_minutes: int = 20
    concurrent_tasks: int = 0
    device_uuid: str = ""
    on_errors: str = "stop"
    on_errors_tolerance: int = 10
    pause_immich_jobs: bool = True

    form_state: dict = field(default_factory=dict)
