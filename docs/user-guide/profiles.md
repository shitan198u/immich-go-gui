# Profiles

Profiles let you maintain separate configurations for different Immich servers, environments, or use cases. Each profile has its own Configuration-tab settings and API keys.

## Profile Layout

Profiles are stored under the config directory:

```text
~/.config/immich-go-gui/          (Linux example)
├── profiles.toml                 # Index: active profile, profile list
└── profiles/
    ├── default/
    │   ├── config.toml           # Configuration-page settings
    │   └── secrets.toml          # Plaintext secrets (fallback only)
    └── work/
        ├── config.toml
        └── secrets.toml
```

The **default** profile is created automatically on first run. It cannot be renamed or deleted.

## Managing Profiles

From the **Profiles** menu you can:

| Action | Description |
|--------|-------------|
| **Switch profile** | Select a different active profile; the GUI reloads its settings (prompts to save pending changes first) |
| **Create** | New empty profile or copy from an existing one |
| **Duplicate** | Clone an existing profile including config and keyring secrets |
| **Rename** | Change profile name (not available for `default`) |
| **Delete** | Remove a profile and its files (not available for `default`) |

When you duplicate or create from an existing profile, API keys are copied in the OS keyring under the new profile name.

## Profile Naming Rules

Profile names must:

- Start with a letter or number
- Contain only letters, numbers, spaces, hyphens, or underscores
- Be at most 64 characters
- Be unique (case-insensitive)

Invalid characters such as `/` or `\` are rejected.

## What Is Stored Per Profile

Each profile's `config.toml` includes (schema v3):

- Server URL, skip SSL, and **client timeout**
- Theme, advanced mode, preferred terminal, allow untested updates
- Secret provider preference

Workflow tab fields and per-tab advanced rows are **not** stored per profile — they are session-only.

API keys are stored separately in the keyring (or `secrets.toml` as fallback), scoped by profile name.

## Migration from Legacy Config

If you upgraded from an older single-file layout, the GUI automatically migrates:

- `config.toml` to `profiles/default/config.toml`
- `secrets.toml` to `profiles/default/secrets.toml`

Original files are renamed with a `.pre-profile.bak` suffix.

## Environment Override

Set `IMMICH_GO_GUI_CONFIG` to point at a specific config file. The profile directory is derived from that file's parent path. See [Config Schema](../reference/config-schema.md).

## Tips

- Use **work** / **home** profiles when you manage multiple Immich instances.
- Duplicate a working profile before experimenting with advanced flags.
- Switching profiles reloads Configuration settings; workflow tab fields reset to defaults.
- If Configuration settings are unsaved, the GUI prompts once before switching.
- Keep a **staging** profile pointed at a test Immich server for dry-runs of large Takeouts.
- Profile names are case-insensitive for uniqueness — `Home` and `home` collide.

## Related

- [Configuration](configuration.md)
- [Security & Privacy](security-and-privacy.md)
- [Config Schema](../reference/config-schema.md)
