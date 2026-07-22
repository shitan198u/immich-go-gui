"""Core backend business logic for Immich-Go GUI.

This package contains data models, CLI schemas, configuration persistence,
binary management, and command building routines.
"""

from .models import (
    AppConfig,
    BinaryStatus,
    CommandPlan,
    UpdateDecision,
    UpdateSeverity,
    ValidationResult,
    VersionSupport,
)
from .cli_schema import (
    ARCHIVE_TABS,
    COMPATIBILITY_MATRIX,
    ENV_KEY_MAP,
    SECRET_FLAGS,
    SERVER_REQUIRED_TABS,
    SERVERLESS_TABS,
    TAB_COMMANDS,
    TAB_KEYS,
    UPLOAD_TABS,
)
from .config_manager import (
    SecretStore,
    clear_api_key,
    default_config_dir,
    default_config_path,
    default_secrets_path,
    get_api_key,
    load_config,
    load_secrets,
    save_config,
    save_secrets,
    set_api_key,
)
from .binary_manager import (
    BINARY_BASE_DIR,
    METADATA_PATH,
    RECOMMENDED_IMMICH_GO_VERSION,
    TESTED_IMMICH_GO_VERSION,
    TESTED_IMMICH_GO_VERSIONS,
    BinaryManager,
    clean_version,
    get_binary_path,
    get_version_support,
    load_binary_metadata,
    parse_version_output,
    save_binary_metadata,
)
from .command_builder import (
    build_environment,
    build_plan_from_state,
    collect_paths,
    mask_command_for_display,
    normalize_server_url,
    validate_date_range,
    validate_state,
)

__all__ = [
    # models
    "AppConfig",
    "BinaryStatus",
    "CommandPlan",
    "UpdateDecision",
    "UpdateSeverity",
    "ValidationResult",
    "VersionSupport",
    # cli_schema
    "ARCHIVE_TABS",
    "COMPATIBILITY_MATRIX",
    "ENV_KEY_MAP",
    "SECRET_FLAGS",
    "SERVER_REQUIRED_TABS",
    "SERVERLESS_TABS",
    "TAB_COMMANDS",
    "TAB_KEYS",
    "UPLOAD_TABS",
    # config_manager
    "SecretStore",
    "clear_api_key",
    "default_config_dir",
    "default_config_path",
    "default_secrets_path",
    "get_api_key",
    "load_config",
    "load_secrets",
    "save_config",
    "save_secrets",
    "set_api_key",
    # binary_manager
    "BINARY_BASE_DIR",
    "METADATA_PATH",
    "RECOMMENDED_IMMICH_GO_VERSION",
    "TESTED_IMMICH_GO_VERSION",
    "TESTED_IMMICH_GO_VERSIONS",
    "BinaryManager",
    "clean_version",
    "get_binary_path",
    "get_version_support",
    "load_binary_metadata",
    "parse_version_output",
    "save_binary_metadata",
    # command_builder
    "build_environment",
    "build_plan_from_state",
    "collect_paths",
    "mask_command_for_display",
    "normalize_server_url",
    "validate_date_range",
    "validate_state",
]
