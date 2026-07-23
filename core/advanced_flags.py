"""Pure-Python registry and helper functions for schema-driven opt-in advanced flags.

Qt-free module.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

from .models import CommandPlan, ValidationResult
from .validation import clean_date_range, normalize_extensions_csv, normalize_list_csv, validate_date_range as _validate_date_range

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
]


@dataclass(frozen=True)
class AdvancedFlagDef:
    key: str                      # Internal state key
    flag: str                     # CLI flag name without --
    label: str                    # Human-readable label / tooltip
    kind: AdvancedFlagKind
    default: Any = None
    options: tuple[str, ...] = ()
    placeholder: str = ""
    hint: str = ""
    secret_env: str | None = None
    allow_empty: bool = True
    warn_values: dict[Any, str] = field(default_factory=dict)


ADVANCED_FLAGS: dict[str, tuple[AdvancedFlagDef, ...]] = {
    "upload-folder": (
        AdvancedFlagDef(
            key="recursive",
            flag="recursive",
            label="Scan subdirectories recursively",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="date-from-name",
            flag="date-from-name",
            label="Use date from filename",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="ignore-sidecar",
            flag="ignore-sidecar-files",
            label="Ignore sidecar files",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="time-zone",
            flag="time-zone",
            label="Time zone override",
            kind="text",
            placeholder="UTC or America/New_York",
        ),
        AdvancedFlagDef(
            key="album-path-joiner",
            flag="album-path-joiner",
            label="Album path joiner",
            kind="text",
            placeholder=" / ",
        ),
        AdvancedFlagDef(
            key="date-range",
            flag="date-range",
            label="Date range",
            kind="date_range",
            placeholder="YYYY-MM-DD,YYYY-MM-DD",
        ),
        AdvancedFlagDef(
            key="include-ext",
            flag="include-extensions",
            label="Include extensions",
            kind="extensions",
            placeholder=".jpg,.heic,.mp4",
        ),
        AdvancedFlagDef(
            key="exclude-ext",
            flag="exclude-extensions",
            label="Exclude extensions",
            kind="extensions",
            placeholder=".thm,.xmp",
        ),
        AdvancedFlagDef(
            key="ban-file",
            flag="ban-file",
            label="Skip files matching patterns",
            kind="lines_repeat",
            placeholder="@eaDir/\n.DS_Store",
        ),
        AdvancedFlagDef(
            key="tag",
            flag="tag",
            label="Custom tags",
            kind="csv_repeat",
            placeholder="vacation, family/reunion",
        ),
        AdvancedFlagDef(
            key="session-tag",
            flag="session-tag",
            label="Session tag",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="folder-tags",
            flag="folder-as-tags",
            label="Folder as tags",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="overwrite",
            flag="overwrite",
            label="Overwrite existing",
            kind="bool",
            default=False,
            warn_values={
                True: "Overwrite mode will replace existing files on the server."
            },
        ),
        AdvancedFlagDef(
            key="pause-jobs",
            flag="pause-immich-jobs",
            label="Pause Immich background jobs",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="manage-epson",
            flag="manage-epson-fastfoto",
            label="Manage Epson FastFoto photos",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="include-type",
            flag="include-type",
            label="Media type",
            kind="enum",
            options=("all", "IMAGE", "VIDEO"),
            default="all",
        ),
        AdvancedFlagDef(
            key="on-errors",
            flag="on-errors",
            label="On errors",
            kind="enum",
            options=("stop", "continue"),
            default="stop",
        ),
        AdvancedFlagDef(
            key="log-level",
            flag="log-level",
            label="Log level",
            kind="enum",
            options=("INFO", "DEBUG", "WARN", "ERROR"),
            default="INFO",
        ),
        AdvancedFlagDef(
            key="api-trace",
            flag="api-trace",
            label="Enable API trace",
            kind="bool",
            default=False,
        ),
    ),
    "upload-gp": (
        AdvancedFlagDef(
            key="include-type",
            flag="include-type",
            label="Media type",
            kind="enum",
            options=("all", "IMAGE", "VIDEO"),
            default="all",
        ),
        AdvancedFlagDef(
            key="include-unmatched",
            flag="include-unmatched",
            label="Include unmatched photos",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="from-album-name",
            flag="from-album-name",
            label="Only import from album",
            kind="text",
            placeholder="Family Album",
        ),
        AdvancedFlagDef(
            key="partner-album",
            flag="partner-shared-album",
            label="Add partner photos to album",
            kind="text",
            placeholder="Partner Photos",
        ),
        AdvancedFlagDef(
            key="include-trashed",
            flag="include-trashed",
            label="Include trashed photos",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="include-untitled-albums",
            flag="include-untitled-albums",
            label="Include untitled albums",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="takeout-tag",
            flag="takeout-tag",
            label="Takeout tag",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="people-tag",
            flag="people-tag",
            label="People tag",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="manage-raw-jpeg",
            flag="manage-raw-jpeg",
            label="RAW/JPEG mode",
            kind="enum",
            options=("NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"),
            default="NoStack",
        ),
        AdvancedFlagDef(
            key="manage-epson",
            flag="manage-epson-fastfoto",
            label="Manage Epson FastFoto photos",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="date-range",
            flag="date-range",
            label="Date range",
            kind="date_range",
            placeholder="YYYY-MM-DD,YYYY-MM-DD",
        ),
        AdvancedFlagDef(
            key="include-ext",
            flag="include-extensions",
            label="Include extensions",
            kind="extensions",
            placeholder=".jpg,.heic,.mp4",
        ),
        AdvancedFlagDef(
            key="exclude-ext",
            flag="exclude-extensions",
            label="Exclude extensions",
            kind="extensions",
            placeholder=".thm,.xmp",
        ),
        AdvancedFlagDef(
            key="ban-file",
            flag="ban-file",
            label="Skip files matching patterns",
            kind="lines_repeat",
            placeholder="@eaDir/\n.DS_Store",
        ),
        AdvancedFlagDef(
            key="tag",
            flag="tag",
            label="Custom tags",
            kind="csv_repeat",
            placeholder="vacation, family/reunion",
        ),
        AdvancedFlagDef(
            key="session-tag",
            flag="session-tag",
            label="Session tag",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="overwrite",
            flag="overwrite",
            label="Overwrite existing",
            kind="bool",
            default=False,
            warn_values={
                True: "Overwrite mode will replace existing files on the server."
            },
        ),
        AdvancedFlagDef(
            key="on-errors",
            flag="on-errors",
            label="On errors",
            kind="enum",
            options=("stop", "continue"),
            default="stop",
        ),
        AdvancedFlagDef(
            key="pause-jobs",
            flag="pause-immich-jobs",
            label="Pause Immich background jobs",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="time-zone",
            flag="time-zone",
            label="Time zone override",
            kind="text",
            placeholder="UTC",
        ),
        AdvancedFlagDef(
            key="log-level",
            flag="log-level",
            label="Log level",
            kind="enum",
            options=("INFO", "DEBUG", "WARN", "ERROR"),
            default="INFO",
        ),
        AdvancedFlagDef(
            key="api-trace",
            flag="api-trace",
            label="Enable API trace",
            kind="bool",
            default=False,
        ),
    ),
    "upload-immich": (
        AdvancedFlagDef(
            key="from-admin-api-key",
            flag="from-admin-api-key",
            label="Source admin API key",
            kind="text",
            secret_env="IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_ADMIN_API_KEY",
        ),
        AdvancedFlagDef(
            key="from-client-timeout",
            flag="from-client-timeout",
            label="Source client timeout",
            kind="duration_minutes",
            default=20,
        ),
        AdvancedFlagDef(
            key="from-favorite",
            flag="from-favorite",
            label="Only favorite assets",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="from-archived",
            flag="from-archived",
            label="Include source archived",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="from-trash",
            flag="from-trash",
            label="Include source trash",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="from-partners",
            flag="from-partners",
            label="Include source partner assets",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="from-no-album",
            flag="from-no-album",
            label="Only assets without album",
            kind="bool",
            default=False,
        ),

        AdvancedFlagDef(
            key="from-minimal-rating",
            flag="from-minimal-rating",
            label="Source minimal rating",
            kind="int",
            default=0,
        ),
        AdvancedFlagDef(
            key="from-people",
            flag="from-people",
            label="Source people tags",
            kind="csv_repeat",
            placeholder="John, Jane",
        ),
        AdvancedFlagDef(
            key="from-tags",
            flag="from-tags",
            label="Source tags",
            kind="csv_repeat",
            placeholder="Tag1, Tag2",
        ),
        AdvancedFlagDef(
            key="from-city",
            flag="from-city",
            label="Source city",
            kind="text",
        ),
        AdvancedFlagDef(
            key="from-state",
            flag="from-state",
            label="Source state",
            kind="text",
        ),
        AdvancedFlagDef(
            key="from-country",
            flag="from-country",
            label="Source country",
            kind="text",
        ),
        AdvancedFlagDef(
            key="from-make",
            flag="from-make",
            label="Source camera make",
            kind="text",
        ),
        AdvancedFlagDef(
            key="from-model",
            flag="from-model",
            label="Source camera model",
            kind="text",
        ),
        AdvancedFlagDef(
            key="from-include-type",
            flag="from-include-type",
            label="Source media type",
            kind="enum",
            options=("all", "IMAGE", "VIDEO"),
            default="all",
        ),
        AdvancedFlagDef(
            key="from-include-ext",
            flag="from-include-extensions",
            label="Source include extensions",
            kind="extensions",
        ),
        AdvancedFlagDef(
            key="from-exclude-ext",
            flag="from-exclude-extensions",
            label="Source exclude extensions",
            kind="extensions",
        ),
        AdvancedFlagDef(
            key="from-time-zone",
            flag="from-time-zone",
            label="Source time zone",
            kind="text",
        ),
        AdvancedFlagDef(
            key="from-device-uuid",
            flag="from-device-uuid",
            label="Source device UUID",
            kind="text",
        ),
        AdvancedFlagDef(
            key="from-skip-ssl",
            flag="from-skip-verify-ssl",
            label="Source skip SSL verification",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="from-api-trace",
            flag="from-api-trace",
            label="Source API trace",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="from-pause-jobs",
            flag="from-pause-immich-jobs",
            label="Source pause jobs",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="tag",
            flag="tag",
            label="Destination tags",
            kind="csv_repeat",
        ),
        AdvancedFlagDef(
            key="session-tag",
            flag="session-tag",
            label="Destination session tag",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="overwrite",
            flag="overwrite",
            label="Destination overwrite",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="time-zone",
            flag="time-zone",
            label="Destination time zone",
            kind="text",
        ),
        AdvancedFlagDef(
            key="manage-burst",
            flag="manage-burst",
            label="Destination burst mode",
            kind="enum",
            options=("NoStack", "Stack", "StackKeepRaw", "StackKeepJPEG"),
            default="NoStack",
        ),
        AdvancedFlagDef(
            key="manage-raw-jpeg",
            flag="manage-raw-jpeg",
            label="Destination RAW/JPEG mode",
            kind="enum",
            options=("NoStack", "KeepRaw", "KeepJPG", "StackCoverRaw", "StackCoverJPG"),
            default="NoStack",
        ),
        AdvancedFlagDef(
            key="manage-heic-jpeg",
            flag="manage-heic-jpeg",
            label="Destination HEIC/JPEG mode",
            kind="enum",
            options=("NoStack", "KeepHeic", "KeepJPG", "StackCoverHeic", "StackCoverJPG"),
            default="NoStack",
        ),
        AdvancedFlagDef(
            key="manage-epson",
            flag="manage-epson-fastfoto",
            label="Destination Epson FastFoto",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="on-errors",
            flag="on-errors",
            label="On errors",
            kind="enum",
            options=("stop", "continue"),
            default="stop",
        ),
        AdvancedFlagDef(
            key="log-level",
            flag="log-level",
            label="Log level",
            kind="enum",
            options=("INFO", "DEBUG", "WARN", "ERROR"),
            default="INFO",
        ),
    ),
    "upload-icloud": (
        AdvancedFlagDef(
            key="memories",
            flag="memories",
            label="Import iCloud Memories as albums",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="date-range",
            flag="date-range",
            label="Date range",
            kind="date_range",
            placeholder="YYYY-MM-DD,YYYY-MM-DD",
        ),
        AdvancedFlagDef(
            key="include-ext",
            flag="include-extensions",
            label="Include extensions",
            kind="extensions",
            placeholder=".jpg,.heic,.mp4",
        ),
        AdvancedFlagDef(
            key="exclude-ext",
            flag="exclude-extensions",
            label="Exclude extensions",
            kind="extensions",
            placeholder=".thm,.xmp",
        ),
        AdvancedFlagDef(
            key="include-type",
            flag="include-type",
            label="Media type",
            kind="enum",
            options=("all", "IMAGE", "VIDEO"),
            default="all",
        ),
        AdvancedFlagDef(
            key="ban-file",
            flag="ban-file",
            label="Skip files matching patterns",
            kind="lines_repeat",
            placeholder="@eaDir/\n.DS_Store",
        ),
        AdvancedFlagDef(
            key="tag",
            flag="tag",
            label="Custom tags",
            kind="csv_repeat",
            placeholder="vacation, family/reunion",
        ),
        AdvancedFlagDef(
            key="session-tag",
            flag="session-tag",
            label="Session tag",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="overwrite",
            flag="overwrite",
            label="Overwrite existing",
            kind="bool",
            default=False,
            warn_values={True: "Overwrite mode will replace existing files on the server."},
        ),
        AdvancedFlagDef(
            key="pause-jobs",
            flag="pause-immich-jobs",
            label="Pause Immich background jobs",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="time-zone",
            flag="time-zone",
            label="Time zone override",
            kind="text",
            placeholder="UTC or America/New_York",
        ),
        AdvancedFlagDef(
            key="on-errors",
            flag="on-errors",
            label="On errors",
            kind="enum",
            options=("stop", "continue"),
            default="stop",
        ),
        AdvancedFlagDef(
            key="log-level",
            flag="log-level",
            label="Log level",
            kind="enum",
            options=("INFO", "DEBUG", "WARN", "ERROR"),
            default="INFO",
        ),
        AdvancedFlagDef(
            key="api-trace",
            flag="api-trace",
            label="Enable API trace",
            kind="bool",
            default=False,
        ),
    ),
    "upload-picasa": (
        AdvancedFlagDef(
            key="album-picasa",
            flag="album-picasa",
            label="Use Picasa album name found in .picasa.ini file",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="recursive",
            flag="recursive",
            label="Scan subdirectories recursively",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="date-from-name",
            flag="date-from-name",
            label="Use date from filename",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="ignore-sidecar",
            flag="ignore-sidecar-files",
            label="Ignore sidecar files",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="include-ext",
            flag="include-extensions",
            label="Include extensions",
            kind="extensions",
            placeholder=".jpg,.png",
        ),
        AdvancedFlagDef(
            key="exclude-ext",
            flag="exclude-extensions",
            label="Exclude extensions",
            kind="extensions",
            placeholder=".thm,.xmp",
        ),
        AdvancedFlagDef(
            key="include-type",
            flag="include-type",
            label="Media type",
            kind="enum",
            options=("all", "IMAGE", "VIDEO"),
            default="all",
        ),
        AdvancedFlagDef(
            key="ban-file",
            flag="ban-file",
            label="Skip files matching patterns",
            kind="lines_repeat",
            placeholder="@eaDir/\n.DS_Store",
        ),
        AdvancedFlagDef(
            key="date-range",
            flag="date-range",
            label="Date range",
            kind="date_range",
            placeholder="YYYY-MM-DD,YYYY-MM-DD",
        ),
        AdvancedFlagDef(
            key="folder-album",
            flag="folder-as-album",
            label="Folder as album mode",
            kind="enum",
            options=("NONE", "FOLDER", "PATH"),
            default="NONE",
        ),
        AdvancedFlagDef(
            key="folder-tags",
            flag="folder-as-tags",
            label="Folder as tags",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="album-joiner",
            flag="album-path-joiner",
            label="Album path joiner",
            kind="text",
            placeholder=" / ",
        ),
        AdvancedFlagDef(
            key="into-album",
            flag="into-album",
            label="Import all files into album",
            kind="text",
            placeholder="Vacation 2024",
        ),
        AdvancedFlagDef(
            key="tag",
            flag="tag",
            label="Custom tags",
            kind="csv_repeat",
            placeholder="vacation, family/reunion",
        ),
        AdvancedFlagDef(
            key="session-tag",
            flag="session-tag",
            label="Session tag",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="overwrite",
            flag="overwrite",
            label="Overwrite existing",
            kind="bool",
            default=False,
            warn_values={True: "Overwrite mode will replace existing files on the server."},
        ),
        AdvancedFlagDef(
            key="pause-jobs",
            flag="pause-immich-jobs",
            label="Pause Immich background jobs",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="time-zone",
            flag="time-zone",
            label="Time zone override",
            kind="text",
            placeholder="UTC or America/New_York",
        ),
        AdvancedFlagDef(
            key="on-errors",
            flag="on-errors",
            label="On errors",
            kind="enum",
            options=("stop", "continue"),
            default="stop",
        ),
        AdvancedFlagDef(
            key="log-level",
            flag="log-level",
            label="Log level",
            kind="enum",
            options=("INFO", "DEBUG", "WARN", "ERROR"),
            default="INFO",
        ),
        AdvancedFlagDef(
            key="api-trace",
            flag="api-trace",
            label="Enable API trace",
            kind="bool",
            default=False,
        ),
    ),
    "archive-folder": (
        AdvancedFlagDef(
            key="date-range",
            flag="date-range",
            label="Date range",
            kind="date_range",
            placeholder="YYYY-MM-DD,YYYY-MM-DD",
        ),
        AdvancedFlagDef(
            key="include-type",
            flag="include-type",
            label="Media type",
            kind="enum",
            options=("all", "IMAGE", "VIDEO"),
            default="all",
        ),
        AdvancedFlagDef(
            key="include-ext",
            flag="include-extensions",
            label="Include extensions",
            kind="extensions",
        ),
        AdvancedFlagDef(
            key="exclude-ext",
            flag="exclude-extensions",
            label="Exclude extensions",
            kind="extensions",
        ),
        AdvancedFlagDef(
            key="ban-file",
            flag="ban-file",
            label="Skip files matching patterns",
            kind="lines_repeat",
        ),
        AdvancedFlagDef(
            key="recursive",
            flag="recursive",
            label="Scan subdirectories recursively",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="ignore-sidecar",
            flag="ignore-sidecar-files",
            label="Ignore sidecar files",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="date-from-name",
            flag="date-from-name",
            label="Use date from filename",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="folder-album",
            flag="folder-as-album",
            label="Folder as album mode",
            kind="enum",
            options=("NONE", "FOLDER", "PATH"),
            default="NONE",
        ),
        AdvancedFlagDef(
            key="folder-tags",
            flag="folder-as-tags",
            label="Folder as tags",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="into-album",
            flag="into-album",
            label="Into album",
            kind="text",
        ),
        AdvancedFlagDef(
            key="album-path-joiner",
            flag="album-path-joiner",
            label="Album path joiner",
            kind="text",
        ),
        AdvancedFlagDef(
            key="on-errors",
            flag="on-errors",
            label="On errors",
            kind="enum",
            options=("stop", "continue"),
            default="stop",
        ),
        AdvancedFlagDef(
            key="log-level",
            flag="log-level",
            label="Log level",
            kind="enum",
            options=("INFO", "DEBUG", "WARN", "ERROR"),
            default="INFO",
        ),
    ),
    "archive-immich": (

        AdvancedFlagDef(
            key="from-favorite",
            flag="from-favorite",
            label="Only favorite assets",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="from-archived",
            flag="from-archived",
            label="Include source archived",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="from-trash",
            flag="from-trash",
            label="Include source trash",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="from-no-album",
            flag="from-no-album",
            label="Only assets without album",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="from-partners",
            flag="from-partners",
            label="Include source partner assets",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="from-minimal-rating",
            flag="from-minimal-rating",
            label="Source minimal rating",
            kind="int",
            default=0,
        ),
        AdvancedFlagDef(
            key="from-people",
            flag="from-people",
            label="Source people tags",
            kind="csv_repeat",
        ),
        AdvancedFlagDef(
            key="from-tags",
            flag="from-tags",
            label="Source tags",
            kind="csv_repeat",
        ),
        AdvancedFlagDef(
            key="from-city",
            flag="from-city",
            label="Source city",
            kind="text",
        ),
        AdvancedFlagDef(
            key="from-state",
            flag="from-state",
            label="Source state",
            kind="text",
        ),
        AdvancedFlagDef(
            key="from-country",
            flag="from-country",
            label="Source country",
            kind="text",
        ),
        AdvancedFlagDef(
            key="from-make",
            flag="from-make",
            label="Source camera make",
            kind="text",
        ),
        AdvancedFlagDef(
            key="from-model",
            flag="from-model",
            label="Source camera model",
            kind="text",
        ),
        AdvancedFlagDef(
            key="from-include-type",
            flag="from-include-type",
            label="Source media type",
            kind="enum",
            options=("all", "IMAGE", "VIDEO"),
            default="all",
        ),
        AdvancedFlagDef(
            key="from-include-ext",
            flag="from-include-extensions",
            label="Source include extensions",
            kind="extensions",
        ),
        AdvancedFlagDef(
            key="from-exclude-ext",
            flag="from-exclude-extensions",
            label="Source exclude extensions",
            kind="extensions",
        ),
        AdvancedFlagDef(
            key="from-time-zone",
            flag="from-time-zone",
            label="Source time zone",
            kind="text",
        ),
        AdvancedFlagDef(
            key="from-device-uuid",
            flag="from-device-uuid",
            label="Source device UUID",
            kind="text",
        ),
        AdvancedFlagDef(
            key="from-client-timeout",
            flag="from-client-timeout",
            label="Source client timeout",
            kind="duration_minutes",
            default=20,
        ),
        AdvancedFlagDef(
            key="from-skip-ssl",
            flag="from-skip-verify-ssl",
            label="Source skip SSL verification",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="from-api-trace",
            flag="from-api-trace",
            label="Source API trace",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="from-pause-jobs",
            flag="from-pause-immich-jobs",
            label="Source pause jobs",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="log-level",
            flag="log-level",
            label="Log level",
            kind="enum",
            options=("INFO", "DEBUG", "WARN", "ERROR"),
            default="INFO",
        ),
    ),
    "stack": (
        AdvancedFlagDef(
            key="date-range",
            flag="date-range",
            label="Date range",
            kind="date_range",
            placeholder="YYYY-MM-DD,YYYY-MM-DD",
        ),
        AdvancedFlagDef(
            key="time-zone",
            flag="time-zone",
            label="Time zone override",
            kind="text",
        ),
        AdvancedFlagDef(
            key="manage-epson",
            flag="manage-epson-fastfoto",
            label="Manage Epson FastFoto photos",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="pause-jobs",
            flag="pause-immich-jobs",
            label="Pause Immich background jobs",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="log-level",
            flag="log-level",
            label="Log level",
            kind="enum",
            options=("INFO", "DEBUG", "WARN", "ERROR"),
            default="INFO",
        ),
        AdvancedFlagDef(
            key="api-trace",
            flag="api-trace",
            label="Enable API trace",
            kind="bool",
            default=False,
        ),
    ),
    "archive-gp": (
        AdvancedFlagDef(
            key="include-unmatched",
            flag="include-unmatched",
            label="Include unmatched photos (no JSON)",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="include-trashed",
            flag="include-trashed",
            label="Include trashed photos",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="from-album-name",
            flag="from-album-name",
            label="Only import from album",
            kind="text",
            placeholder="Family Album",
        ),
        AdvancedFlagDef(
            key="partner-album",
            flag="partner-shared-album",
            label="Add partner photos to album",
            kind="text",
            placeholder="Partner Photos",
        ),
        AdvancedFlagDef(
            key="include-untitled-albums",
            flag="include-untitled-albums",
            label="Include untitled albums",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="takeout-tag",
            flag="takeout-tag",
            label="Tag photos with Takeout timestamp",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="people-tag",
            flag="people-tag",
            label="Tag photos with people names from JSON",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="date-range",
            flag="date-range",
            label="Date range",
            kind="date_range",
            placeholder="YYYY-MM-DD,YYYY-MM-DD",
        ),
        AdvancedFlagDef(
            key="include-ext",
            flag="include-extensions",
            label="Include extensions",
            kind="extensions",
            placeholder=".jpg,.heic",
        ),
        AdvancedFlagDef(
            key="exclude-ext",
            flag="exclude-extensions",
            label="Exclude extensions",
            kind="extensions",
            placeholder=".thm,.xmp",
        ),
        AdvancedFlagDef(
            key="include-type",
            flag="include-type",
            label="Media type",
            kind="enum",
            options=("all", "IMAGE", "VIDEO"),
            default="all",
        ),
        AdvancedFlagDef(
            key="ban-file",
            flag="ban-file",
            label="Skip files matching patterns",
            kind="lines_repeat",
            placeholder="@eaDir/\n.DS_Store",
        ),
        AdvancedFlagDef(
            key="on-errors",
            flag="on-errors",
            label="On errors",
            kind="enum",
            options=("stop", "continue"),
            default="stop",
        ),
        AdvancedFlagDef(
            key="log-level",
            flag="log-level",
            label="Log level",
            kind="enum",
            options=("INFO", "DEBUG", "WARN", "ERROR"),
            default="INFO",
        ),
    ),
    "archive-icloud": (
        AdvancedFlagDef(
            key="memories",
            flag="memories",
            label="Import iCloud Memories as albums",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="date-range",
            flag="date-range",
            label="Date range",
            kind="date_range",
            placeholder="YYYY-MM-DD,YYYY-MM-DD",
        ),
        AdvancedFlagDef(
            key="include-ext",
            flag="include-extensions",
            label="Include extensions",
            kind="extensions",
            placeholder=".jpg,.heic,.mp4",
        ),
        AdvancedFlagDef(
            key="exclude-ext",
            flag="exclude-extensions",
            label="Exclude extensions",
            kind="extensions",
            placeholder=".thm,.xmp",
        ),
        AdvancedFlagDef(
            key="include-type",
            flag="include-type",
            label="Media type",
            kind="enum",
            options=("all", "IMAGE", "VIDEO"),
            default="all",
        ),
        AdvancedFlagDef(
            key="ban-file",
            flag="ban-file",
            label="Skip files matching patterns",
            kind="lines_repeat",
            placeholder="@eaDir/\n.DS_Store",
        ),
        AdvancedFlagDef(
            key="recursive",
            flag="recursive",
            label="Scan subdirectories recursively",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="ignore-sidecar",
            flag="ignore-sidecar-files",
            label="Ignore sidecar files",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="date-from-name",
            flag="date-from-name",
            label="Use date from filename",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="folder-album",
            flag="folder-as-album",
            label="Folder as album mode",
            kind="enum",
            options=("NONE", "FOLDER", "PATH"),
            default="NONE",
        ),
        AdvancedFlagDef(
            key="folder-tags",
            flag="folder-as-tags",
            label="Folder as tags",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="into-album",
            flag="into-album",
            label="Into album",
            kind="text",
        ),
        AdvancedFlagDef(
            key="album-path-joiner",
            flag="album-path-joiner",
            label="Album path joiner",
            kind="text",
        ),
        AdvancedFlagDef(
            key="on-errors",
            flag="on-errors",
            label="On errors",
            kind="enum",
            options=("stop", "continue"),
            default="stop",
        ),
        AdvancedFlagDef(
            key="log-level",
            flag="log-level",
            label="Log level",
            kind="enum",
            options=("INFO", "DEBUG", "WARN", "ERROR"),
            default="INFO",
        ),
    ),
    "archive-picasa": (
        AdvancedFlagDef(
            key="album-picasa",
            flag="album-picasa",
            label="Use Picasa album name found in .picasa.ini file",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="date-range",
            flag="date-range",
            label="Date range",
            kind="date_range",
            placeholder="YYYY-MM-DD,YYYY-MM-DD",
        ),
        AdvancedFlagDef(
            key="include-type",
            flag="include-type",
            label="Media type",
            kind="enum",
            options=("all", "IMAGE", "VIDEO"),
            default="all",
        ),
        AdvancedFlagDef(
            key="include-ext",
            flag="include-extensions",
            label="Include extensions",
            kind="extensions",
        ),
        AdvancedFlagDef(
            key="exclude-ext",
            flag="exclude-extensions",
            label="Exclude extensions",
            kind="extensions",
        ),
        AdvancedFlagDef(
            key="ban-file",
            flag="ban-file",
            label="Skip files matching patterns",
            kind="lines_repeat",
        ),
        AdvancedFlagDef(
            key="recursive",
            flag="recursive",
            label="Scan subdirectories recursively",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="ignore-sidecar",
            flag="ignore-sidecar-files",
            label="Ignore sidecar files",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="date-from-name",
            flag="date-from-name",
            label="Use date from filename",
            kind="bool",
            default=True,
        ),
        AdvancedFlagDef(
            key="folder-album",
            flag="folder-as-album",
            label="Folder as album mode",
            kind="enum",
            options=("NONE", "FOLDER", "PATH"),
            default="NONE",
        ),
        AdvancedFlagDef(
            key="folder-tags",
            flag="folder-as-tags",
            label="Folder as tags",
            kind="bool",
            default=False,
        ),
        AdvancedFlagDef(
            key="into-album",
            flag="into-album",
            label="Into album",
            kind="text",
        ),
        AdvancedFlagDef(
            key="album-path-joiner",
            flag="album-path-joiner",
            label="Album path joiner",
            kind="text",
        ),
        AdvancedFlagDef(
            key="on-errors",
            flag="on-errors",
            label="On errors",
            kind="enum",
            options=("stop", "continue"),
            default="stop",
        ),
        AdvancedFlagDef(
            key="log-level",
            flag="log-level",
            label="Log level",
            kind="enum",
            options=("INFO", "DEBUG", "WARN", "ERROR"),
            default="INFO",
        ),
    ),
}


def advanced_flag_args(def_: AdvancedFlagDef, value: Any) -> list[str]:
    """Generates CLI argument list for an enabled advanced flag definition and value."""
    flag = def_.flag

    if def_.kind == "bool":
        if bool(value):
            return [f"--{flag}"]
        return [f"--{flag}=false"]

    if value is None:
        return []

    if def_.kind in ("text", "enum"):
        text = str(value).strip()
        if not text:
            return []
        return [f"--{flag}={text}"]

    if def_.kind == "int":
        return [f"--{flag}={int(value)}"]

    if def_.kind == "duration_minutes":
        return [f"--{flag}={int(value)}m"]

    if def_.kind == "date_range":
        cleaned = clean_date_range(str(value))
        if not cleaned:
            return []
        return [f"--{flag}={cleaned}"]

    if def_.kind == "extensions":
        normalized = normalize_extensions_csv(str(value))
        if not normalized:
            return []
        return [f"--{flag}={normalized}"]

    if def_.kind == "csv_repeat":
        items = normalize_list_csv(str(value))
        return [f"--{flag}={item}" for item in items if item]

    if def_.kind == "lines_repeat":
        args = []
        for line in str(value).splitlines():
            line = line.strip()
            if line:
                args.append(f"--{flag}={line}")
        return args

    return []


def apply_advanced_flags_to_plan(
    plan: CommandPlan,
    emitter: Any,
    tab_key: str,
    advanced_state: dict,
):
    """Applies active (enabled) advanced flags to a CommandPlan and FlagEmitter."""
    from .cli_schema import flag_allowed_for_tab

    if not isinstance(advanced_state, dict):
        return

    for def_ in ADVANCED_FLAGS.get(tab_key, ()):
        entry = advanced_state.get(def_.key)
        if not isinstance(entry, dict) or not entry.get("enabled"):
            continue

        value = entry.get("value", def_.default)

        # Secret advanced flags set env var instead of argv
        if def_.secret_env:
            if value:
                plan.env[def_.secret_env] = str(value).strip()
            continue

        args = advanced_flag_args(def_, value)
        if not args:
            continue

        if not flag_allowed_for_tab(tab_key, def_.flag):
            emitter.errors.append(
                f"Flag '--{def_.flag}' is not allowed for tab '{tab_key}'"
            )
            continue

        for arg in args:
            if hasattr(emitter, "add_raw_checked"):
                emitter.add_raw_checked(arg)
            else:
                emitter.opts.append(arg)

        warning = def_.warn_values.get(value)
        if warning:
            plan.warnings.append(warning)


def validate_advanced_state(tab_key: str, advanced_state: dict) -> ValidationResult:
    """Validates enabled advanced flags for a given tab."""
    res = ValidationResult()
    if not isinstance(advanced_state, dict):
        return res

    for def_ in ADVANCED_FLAGS.get(tab_key, ()):
        entry = advanced_state.get(def_.key)
        if not isinstance(entry, dict) or not entry.get("enabled"):
            continue

        value = entry.get("value", def_.default)

        if def_.kind == "date_range":
            text = str(value or "").strip()
            if text:
                ok, err = _validate_date_range(text)
                if not ok:
                    res.errors.append(f"Invalid {def_.label}: {err}")

        elif def_.kind in ("text", "extensions", "csv_repeat", "lines_repeat"):
            text = str(value or "").strip()
            if not text and not def_.allow_empty:
                res.errors.append(f"{def_.label} is enabled but empty.")

    return res
