"""Core backend business logic for Immich-Go GUI.

This package contains data models, CLI schemas, configuration persistence,
binary management, and command building routines.
"""

from .activity_monitor import (
    ActivityMonitor,
    ActivityState,
    check_processes_running,
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
from .cli_contract import (
    CompatibilityReport,
    check_binary_help,
    check_fixtures,
)
from .cli_help import (
    help_name_for_tab,
    load_help_fixture,
    parse_help_flags,
)
from .cli_schema import (
    ARCHIVE_TABS,
    COMPATIBILITY_MATRIX,
    ENV_KEY_MAP,
    SECRET_FLAGS,
    SERVER_REQUIRED_TABS,
    SERVERLESS_TABS,
    TAB_ALLOWED_FLAGS,
    TAB_COMMANDS,
    TAB_KEYS,
    UPLOAD_TABS,
    assert_flag_allowed,
    flag_allowed_for_tab,
)
from .command_builder import (
    build_environment,
    build_plan_from_state,
    collect_paths,
    collect_safety_warnings,
    mask_command_for_display,
    validate_date_range,
    validate_state,
    validate_state_light,
)
from .config_manager import (
    SecretSaveResult,
    SecretStore,
    clear_api_key,
    default_config_dir,
    default_config_path,
    default_secrets_path,
    get_api_key,
    get_config_load_warning,
    get_secret_with_fallback,
    load_config,
    load_secrets,
    save_config,
    save_secret_with_fallback,
    save_secrets,
    save_server_url,
    set_api_key,
)
from .flag_registry import (
    REGISTRY,
    FlagDef,
    Registry,
)
from .folder_runner import (
    RunnerState,
    count_pending_files,
    run_folder_upload,
)
from .folder_runner import (
    UploadResult as MonitorUploadResult,
)
from .folder_watcher import (
    DebounceFileQueue,
    FolderWatcher,
    WatchedFolder,
)
from .models import (
    AppConfig,
    BinaryStatus,
    CommandPlan,
    UpdateDecision,
    UpdateSeverity,
    ValidationResult,
    VersionSupport,
)
from .monitor_config import (
    ActivityConfig,
    ActivityPauseMethod,
    FolderFilter,
    MonitorConfig,
    MonitorConfigStore,
    NetworkPolicy,
)
from .monitor_state import (
    FolderUploadState,
    MonitorState,
    MonitorStateStore,
)
from .network import normalize_server_url
from .network_awareness import (
    NetworkMonitor,
    NetworkStatus,
)
from .process_tracker import (
    RunLock,
    cleanup_stale_locks,
    create_lock,
    is_lock_active,
    lock_dir,
    read_lock,
    release_lock,
    reset_all_locks,
    scan_locks,
)
from .profile_manager import (
    ProfileInfo,
    active_profile_name,
    create_profile,
    delete_profile,
    duplicate_profile,
    ensure_default_profile,
    list_profiles,
    rename_profile,
    set_active_profile_name,
    validate_profile_name,
)
from .terminal_launcher import LaunchResult, launch_external_terminal
from .version import __version__, get_app_version

__all__ = [
    # cli_schema
    "ARCHIVE_TABS",
    # binary_manager
    "BINARY_BASE_DIR",
    "COMPATIBILITY_MATRIX",
    "ENV_KEY_MAP",
    "METADATA_PATH",
    "RECOMMENDED_IMMICH_GO_VERSION",
    # flag_registry
    "REGISTRY",
    "SECRET_FLAGS",
    "SERVERLESS_TABS",
    "SERVER_REQUIRED_TABS",
    "TAB_ALLOWED_FLAGS",
    "TAB_COMMANDS",
    "TAB_KEYS",
    "TESTED_IMMICH_GO_VERSION",
    "TESTED_IMMICH_GO_VERSIONS",
    "UPLOAD_TABS",
    # Monitor subsystem
    "ActivityConfig",
    "ActivityMonitor",
    "ActivityPauseMethod",
    "ActivityState",
    # models
    "AppConfig",
    "BinaryManager",
    "BinaryStatus",
    "CommandPlan",
    # cli_contract
    "CompatibilityReport",
    "DebounceFileQueue",
    "FlagDef",
    "FolderFilter",
    "FolderUploadState",
    "FolderWatcher",
    # terminal_launcher
    "LaunchResult",
    "MonitorConfig",
    "MonitorConfigStore",
    "MonitorState",
    "MonitorStateStore",
    "MonitorUploadResult",
    "NetworkMonitor",
    "NetworkPolicy",
    "NetworkStatus",
    # profile_manager
    "ProfileInfo",
    "Registry",
    # process_tracker
    "RunLock",
    "RunnerState",
    # config_manager
    "SecretSaveResult",
    "SecretStore",
    "UpdateDecision",
    "UpdateSeverity",
    "ValidationResult",
    "VersionSupport",
    "WatchedFolder",
    "__version__",
    "active_profile_name",
    "assert_flag_allowed",
    # command_builder
    "build_environment",
    "build_plan_from_state",
    "check_binary_help",
    "check_fixtures",
    "check_processes_running",
    "clean_version",
    "cleanup_stale_locks",
    "clear_api_key",
    "collect_paths",
    "collect_safety_warnings",
    "count_pending_files",
    "create_lock",
    "create_profile",
    "default_config_dir",
    "default_config_path",
    "default_secrets_path",
    "delete_profile",
    "duplicate_profile",
    "ensure_default_profile",
    "flag_allowed_for_tab",
    "get_api_key",
    "get_app_version",
    "get_binary_path",
    "get_config_load_warning",
    "get_secret_with_fallback",
    "get_version_support",
    # cli_help
    "help_name_for_tab",
    "is_lock_active",
    "launch_external_terminal",
    "list_profiles",
    "load_binary_metadata",
    "load_config",
    "load_help_fixture",
    "load_secrets",
    "lock_dir",
    "mask_command_for_display",
    "normalize_server_url",
    "parse_help_flags",
    "parse_version_output",
    "read_lock",
    "release_lock",
    "rename_profile",
    "reset_all_locks",
    "run_folder_upload",
    "save_binary_metadata",
    "save_config",
    "save_secret_with_fallback",
    "save_secrets",
    "save_server_url",
    "scan_locks",
    "set_active_profile_name",
    "set_api_key",
    "validate_date_range",
    "validate_profile_name",
    "validate_state",
    "validate_state_light",
]
