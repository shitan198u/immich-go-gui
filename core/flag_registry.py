# core/flag_registry.py
"""Unified flag registry loaded from flags.toml.

Replaces the hand-maintained TAB_ALLOWED_FLAGS, ADVANCED_FLAGS,
ENV_KEY_MAP, TAB_COMMANDS, UPLOAD_TABS, ARCHIVE_TABS,
SERVER_REQUIRED_TABS, SERVERLESS_TABS.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

_FLAGS_TOML = Path(__file__).resolve().parent / "flags.toml"

AdvancedFlagKind = Literal[
    "bool",
    "text",
    "enum",
    "int",
    "duration_minutes",
    "extensions",
    "csv_repeat",
    "lines_repeat",
    "date_range",
    "path",
    "paths",
]

FlagMode = Literal["simple", "advanced"]


@dataclass(frozen=True)
class FlagDef:
    """One flag entry from flags.toml."""

    key: str
    flag: str  # CLI name without --; "" for positional
    label: str
    kind: AdvancedFlagKind
    mode: FlagMode = "advanced"
    default: Any = None
    options: tuple[str, ...] = ()
    placeholder: str = ""
    hint: str = ""
    secret_env: str | None = None
    allow_empty: bool = True
    hidden: bool = False
    min_val: int | None = None
    max_val: int | None = None
    warn_values: dict[Any, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TabDef:
    key: str
    command: tuple[str, ...]
    section: str  # "upload" | "archive" | "stack"
    server_required: bool
    serverless: bool


@dataclass(frozen=True)
class Registry:
    tabs: dict[str, TabDef]
    flags: dict[str, tuple[FlagDef, ...]]
    secrets: dict[str, dict[str, str]]

    # ── Derived sets (match old cli_schema.py exports) ─────────
    @property
    def tab_keys(self) -> list[str]:
        return ["config"] + list(self.tabs.keys())

    @property
    def upload_tabs(self) -> set[str]:
        return {k for k, t in self.tabs.items() if t.section == "upload"}

    @property
    def archive_tabs(self) -> set[str]:
        return {k for k, t in self.tabs.items() if t.section == "archive"}

    @property
    def server_required_tabs(self) -> set[str]:
        return {k for k, t in self.tabs.items() if t.server_required}

    @property
    def serverless_tabs(self) -> set[str]:
        return {k for k, t in self.tabs.items() if t.serverless}

    @property
    def tab_commands(self) -> dict[str, list[str]]:
        return {k: list(t.command) for k, t in self.tabs.items()}

    @property
    def env_key_map(self) -> dict[str, dict[str, str]]:
        return dict(self.secrets)

    def allowed_flags(self, tab_key: str) -> frozenset[str]:
        """All CLI flag names allowed for a tab (replaces TAB_ALLOWED_FLAGS)."""
        return frozenset(d.flag for d in self.flags.get(tab_key, ()) if d.flag)

    def advanced_defs(self, tab_key: str) -> tuple[FlagDef, ...]:
        """Flags that appear in the advanced card."""
        return tuple(
            d
            for d in self.flags.get(tab_key, ())
            if d.mode == "advanced" and not d.hidden
        )

    def simple_keys(self, tab_key: str) -> set[str]:
        """Keys that have simple-mode widgets."""
        return {d.key for d in self.flags.get(tab_key, ()) if d.mode == "simple"}

    def advanced_keys(self, tab_key: str) -> set[str]:
        """Keys that are advanced-only (mode advanced), excluding hidden structural flags."""
        return {
            d.key
            for d in self.flags.get(tab_key, ())
            if d.mode == "advanced" and not d.hidden
        }

    def flag_allowed(self, tab_key: str, flag_name: str) -> bool:
        return flag_name.lstrip("-") in self.allowed_flags(tab_key)


def _load_registry(path: Path = _FLAGS_TOML) -> Registry:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))

    tabs: dict[str, TabDef] = {}
    for key, meta in raw.get("tabs", {}).items():
        tabs[key] = TabDef(
            key=key,
            command=tuple(meta["command"]),
            section=meta["section"],
            server_required=meta.get("server_required", False),
            serverless=meta.get("serverless", False),
        )

    flags: dict[str, tuple[FlagDef, ...]] = {}
    for tab_key, entries in raw.get("flags", {}).items():
        defs = []
        for e in entries:
            wv_raw = e.get("warn_values", {})
            warn_values = {}
            for k, v in wv_raw.items():
                if isinstance(k, str) and k.lower() == "true":
                    warn_values[True] = v
                elif isinstance(k, str) and k.lower() == "false":
                    warn_values[False] = v
                else:
                    warn_values[k] = v

            defs.append(
                FlagDef(
                    key=e["key"],
                    flag=e.get("flag", ""),
                    label=e.get("label", ""),
                    kind=e.get("kind", "text"),
                    mode=e.get("mode", "advanced"),
                    default=e.get("default"),
                    options=tuple(e.get("options", ())),
                    placeholder=e.get("placeholder", ""),
                    hint=e.get("hint", ""),
                    secret_env=e.get("secret_env"),
                    allow_empty=e.get("allow_empty", True),
                    hidden=bool(e.get("hidden", False)),
                    min_val=e.get("min"),
                    max_val=e.get("max"),
                    warn_values=warn_values,
                )
            )
        flags[tab_key] = tuple(defs)

    secrets = raw.get("secrets", {})
    return Registry(tabs=tabs, flags=flags, secrets=secrets)


# Module-level singleton — loaded once at import.
REGISTRY = _load_registry()
