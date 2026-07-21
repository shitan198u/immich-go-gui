# The Complete Immich-Go Guide

> A detailed, example-driven reference for **Immich-Go**, the Go-based command-line alternative to the `immich-CLI` tool for uploading, archiving, and organizing photo/video collections on a self-hosted [Immich](https://immich.app) server.
>
> Source: [github.com/simulot/immich-go](https://github.com/simulot/immich-go) — documentation compiled from the project's `/docs` folder.

---

## Table of Contents

1. [What Is Immich-Go?](#1-what-is-immich-go)
2. [Installation](#2-installation)
3. [API Key & Permissions Setup](#3-api-key--permissions-setup)
4. [Core Concepts: Command Structure](#4-core-concepts-command-structure)
5. [Global Options & Logging](#5-global-options--logging)
6. [The `upload` Command](#6-the-upload-command)
7. [The `archive` Command](#7-the-archive-command)
8. [The `stack` Command](#8-the-stack-command)
9. [Configuration Files (TOML / YAML / JSON)](#9-configuration-files-toml--yaml--json)
10. [Environment Variables](#10-environment-variables)
11. [Technical Deep Dive](#11-technical-deep-dive)
12. [Practical Examples & Recipes](#12-practical-examples--recipes)
13. [Best Practices](#13-best-practices)
14. [Automation Scripts](#14-automation-scripts)
15. [Troubleshooting](#15-troubleshooting)
16. [Quick-Reference Cheat Sheet](#16-quick-reference-cheat-sheet)

---

## 1. What Is Immich-Go?

**Immich-Go** is an open-source, single-binary command-line tool that streamlines uploading and managing large photo/video collections on a self-hosted **Immich** server. It was created as an alternative to the official `immich-CLI`, with one key advantage: **it does not require Node.js** — it's a self-contained Go binary that runs anywhere.

It is especially well known for how well it handles **Google Photos Takeout** archives, which are notoriously messy (split ZIPs, JSON sidecars that don't always match filenames, edited/original duplicates, partner-shared photos, etc.).

### Key Features

- **Multiple Sources** — Upload from Google Photos Takeouts, iCloud exports, local folders, ZIP archives, Picasa collections, and even directly from another Immich server.
- **Large Collections** — Built to reliably handle libraries of 100,000+ photos.
- **Smart Management** — Automatic duplicate detection, burst-photo stacking, and RAW+JPEG / HEIC+JPEG pairing.
- **Cross-Platform** — Prebuilt binaries for Windows, macOS, Linux, and FreeBSD (AMD64 and ARM).
- **No Runtime Dependencies** — No NodeJS or Docker required to run it.
- **Efficient Uploads** — Can pause Immich's own background jobs (thumbnail generation, etc.) during an upload for better throughput, and supports parallel/concurrent uploads.
- **Archival/Export** — Can pull assets *out* of Immich (or any other source) into a clean, date-organized folder structure with full metadata sidecars — effectively a backup/export tool as well as an import tool.
- **Reorganization** — A dedicated `stack` command groups related assets already on the server (bursts, RAW+JPEG pairs, etc.) without needing to re-upload anything.

> ⚠️ **Compatibility note**: Immich-Go targets Immich V2 and V3. Since it tracks a frequently-changing upstream API, always check the [releases page](https://github.com/simulot/immich-go/releases) for compatibility notes with your specific Immich server version.
>
> ⚠️ **Breaking change (v0.32.0)**: The `ReplaceAsset` API method was removed upstream. The `asset.replace` API-key permission is no longer needed — if your key still has it, the server simply ignores it. Use `asset.copy` for asset-duplication needs instead.

---

## 2. Installation

### Prerequisites

- **Pre-built binaries**: no prerequisites — just download and run.
- **Building from source**: Go 1.25+ and Git.
- You will always need: a **running Immich server** and an **API key** generated from *Account Settings → API Keys → New API Key*.

### Option 1: Pre-Built Binaries (Recommended)

Supported OS: **Windows, macOS, Linux, FreeBSD**. Supported architectures: **AMD64 (x86_64)** and **ARM**.

1. Download the archive matching your platform from the [releases page](https://github.com/simulot/immich-go/releases/latest):
   - Windows: `immich-go_Windows_x86_64.zip`
   - macOS: `immich-go_Darwin_x86_64.tar.gz`
   - Linux: `immich-go_Linux_x86_64.tar.gz`
   - FreeBSD: `immich-go_Freebsd_x86_64.tar.gz`
2. Extract it:

```bash
# Linux/macOS/FreeBSD
tar -xzf immich-go*.tar.gz

# Windows — use Explorer or your preferred zip tool
```

3. (Optional) Put the binary on your `PATH`:

```bash
# Linux/macOS/FreeBSD
sudo mv immich-go /usr/local/bin/

# Windows — move immich-go.exe into a folder that's already on PATH
```

### Option 2: Build From Source

```bash
git clone https://github.com/simulot/immich-go.git
cd immich-go
go build
go install   # optional — installs into $GOPATH/bin
```

### Option 3: Nix Package Manager

Immich-Go is packaged in `nixpkgs`:

```bash
# Try without installing
nix-shell -I "nixpkgs=https://github.com/NixOS/nixpkgs/archive/nixos-unstable-small.tar.gz" -p immich-go

# With flakes enabled
nix run "github:nixos/nixpkgs?ref=nixos-unstable-small#immich-go" -- --help
```

For NixOS system-wide installs, add it to `configuration.nix`:

```nix
environment.systemPackages = with pkgs; [
  immich-go
];
```

### Special Case: Termux (Android)

Pre-built ARM64 binaries **don't work** in Termux — you must build from source:

```bash
pkg install git golang
# ...follow the "build from source" steps above...
echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc
source ~/.bashrc
```

### Verifying the Install

```bash
immich-go --version
```

### Basic Syntax Reminder

```bash
immich-go command sub-command [options] [path]
```

- Linux/macOS/FreeBSD, running from the current directory: `./immich-go`
- Windows, running from the current directory: `.\immich-go`

### Troubleshooting Installation

| Problem | Fix |
|---|---|
| `Permission denied` (Linux/macOS) | `chmod +x immich-go` |
| `Command not found` | Ensure the binary is on `PATH`, or call it with a full path |
| SSL/TLS certificate errors | Use `--skip-verify-ssl` (not recommended for production — see [Security](#security-and-privacy)) |

---

## 3. API Key & Permissions Setup

Create an Immich API key (**Account Settings → API Keys → New API Key**) with, at minimum, the following scopes:

- `asset.read`
- `asset.statistics`
- `asset.update`
- `asset.upload`
- `asset.copy`
- `asset.replace`
- `asset.delete`
- `asset.download`
- `album.create`
- `album.read`
- `albumAsset.create`
- `server.about`
- `stack.create`
- `tag.asset`
- `tag.create`
- `user.read`

Because Immich-Go can pause Immich's own background jobs during upload/stacking operations for better performance, it can use an **admin-linked API key** (supplied via the `--admin-api-key` flag) with two extra permissions if you want to use that feature (`--pause-immich-jobs`):

- `job.create`
- `job.read`

> **Tip**: In multi-user setups, create separate keys per purpose (upload vs. read-only backup vs. admin) — see the [Security and Privacy](#security-and-privacy) section below for a full strategy.

---

## 4. Core Concepts: Command Structure

Immich-Go uses a **hierarchical command structure**:

```bash
immich-go [global-options] command sub-command [command-options] [path]
```

| Command | Description | Sub-commands |
|---|---|---|
| `upload` | Upload photos/videos **to** an Immich server | `from-folder`, `from-google-photos`, `from-icloud`, `from-picasa`, `from-immich` |
| `archive` | Export/archive photos **from** any source **to** a local, date-organized folder structure | `from-folder`, `from-google-photos`, `from-icloud`, `from-picasa`, `from-immich` |
| `stack` | Organize related assets already on the server into stacks (no upload) | *(none)* |
| `completion` | Generate the autocompletion script for the specified shell | `bash`, `fish`, `powershell`, `zsh` |
| `help` | Help about any command | *(none)* |
| `version` | Display version information | *(none)* |

Notice that `upload` and `archive` share the exact same set of five sub-commands — the only difference is the **destination**: `upload` pushes assets into an Immich server, while `archive` writes them to a local folder. This symmetry means everything you learn about filtering/organizing options for `upload from-google-photos`, for instance, applies identically to `archive from-google-photos`.

### Quick Syntax Examples

```bash
# Upload from a local folder
immich-go upload from-folder --server=http://localhost:2283 --api-key=your-key /photos

# Archive (export) everything from a server to a local backup folder
immich-go archive from-immich --server=http://localhost:2283 --api-key=your-key --write-to-folder=/backup

# Stack existing photos on the server
immich-go stack --server=http://localhost:2283 --api-key=your-key --manage-burst=Stack

# Show version
immich-go version
```

### 4.1 Shell Autocompletion (`completion`)

Generate the autocompletion script for `immich-go` for the specified shell. 

**Usage:**
```bash
immich-go completion [command]
```

**Available Shells:**
*   `bash`: Generate the autocompletion script for bash
*   `fish`: Generate the autocompletion script for fish
*   `powershell`: Generate the autocompletion script for powershell
*   `zsh`: Generate the autocompletion script for zsh

**Flags:**
*   `-h, --help`: Help for completion
*   `--no-descriptions`: Disable completion descriptions

#### Loading completions in your current session:
*   **Bash**: `source <(immich-go completion bash)`
*   **Fish**: `immich-go completion fish | source`
*   **PowerShell**: `immich-go completion powershell | Out-String | Invoke-Expression`
*   **Zsh**: `source <(immich-go completion zsh)`

#### Persisting completions (once-off setup):
*   **Linux (Bash)**: `immich-go completion bash > /etc/bash_completion.d/immich-go`
*   **macOS (Bash)**: `immich-go completion bash > $(brew --prefix)/etc/bash_completion.d/immich-go`
*   **Fish**: `immich-go completion fish > ~/.config/fish/completions/immich-go.fish`
*   **Linux (Zsh)**: `immich-go completion zsh > "${fpath[1]}/_immich-go"`
*   **macOS (Zsh)**: `immich-go completion zsh > $(brew --prefix)/share/zsh/site-functions/_immich-go`

---

## 5. Global Options & Logging

These options work with **every** command:

| Option | Default | Description |
|---|---|---|
| `-h, --help` | – | Show help information |
| `-l, --log-file` | Auto-generated | Write log messages to the specified file |
| `--log-level` | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARN`, `ERROR` |
| `--log-type` | `text` | Log format: `text` or `json` |
| `--config` | `./immich-go.yaml` | Specify a custom configuration file path |
| `--concurrent-tasks` | `16` | Number of concurrent tasks (1-20) |
| `--dry-run` | `false` | Dry run mode |
| `--on-errors` | `stop` | What to do when an error occurs (`stop`, `continue`, or `accept N errors at max`) |
| `--save-config` | `false` | Save the command parameters to the config file `immich-go.yaml` |
| `-v, --version` | – | Display the current version |

### Default Log File Locations

| OS | Default Path |
|---|---|
| Linux | `$HOME/.cache/immich-go/immich-go_YYYY-MM-DD_HH-MI-SS.log` |
| Windows | `%LocalAppData%\immich-go\immich-go_YYYY-MM-DD_HH-MI-SS.log` |
| macOS | `$HOME/Library/Caches/immich-go/immich-go_YYYY-MM-DD_HH-MI-SS.log` |

### Global Environment Variable

| Variable | Purpose |
|---|---|
| `IMMICHGO_TEMPDIR` | Overrides the temporary directory used for internal operations |

---

## 6. The `upload` Command

The `upload` command transfers photos and videos **from various sources into your Immich server**.

```bash
immich-go upload <sub-command> [options] <source-path>
```

| Sub-command | Source | Description |
|---|---|---|
| `from-folder` | Local filesystem | Upload from local folders or ZIP archives |
| `from-google-photos` | Google Takeout | Upload from Google Photos takeout archives |
| `from-icloud` | iCloud export | Upload from an iCloud takeout |
| `from-picasa` | Picasa | Upload from a Picasa photo collection |
| `from-immich` | Immich server | Transfer assets between two Immich servers |

### 6.1 Options Shared by All `upload` Sub-Commands

**Server connection**

| Option | Required | Description |
|---|---|---|
| `-s, --server` | ✅ | Immich server URL (e.g., `http://localhost:2283`) |
| `-k, --api-key` | ✅ | Your API key |
| `--admin-api-key` | | Admin's API key for managing server's jobs |
| `--skip-verify-ssl` | | Skip SSL certificate verification |
| `--client-timeout` | | Server-call timeout (default: `20m`) |

**Upload behavior**

| Option | Default | Description |
|---|---|---|
| `--dry-run` | `false` | Simulate the upload without transferring anything |
| `--concurrent-tasks` | CPU cores | Number of parallel upload tasks (1–20) |
| `--overwrite` | `false` | Replace existing files on the server |
| `--pause-immich-jobs` | `true` | Pause Immich's own background jobs during upload |
| `--on-errors` | `stop` | What to do on error: `stop`, `continue`, or a tolerated error count |

**Tagging & organization**

| Option | Default | Description |
|---|---|---|
| `--session-tag` | `false` | Tag uploaded assets with the upload-session timestamp |
| `--tag` | – | Add a custom tag (repeatable; supports hierarchy with `/`, e.g. `tag1/subtag1`) |
| `--device-uuid` | `$LOCALHOST` (hostname) | Sets a device identifier used by Immich |

**User interface**

| Option | Default | Description |
|---|---|---|
| `--no-ui` | `false` | Disable the interactive terminal UI (useful for scripts/cron) |
| `--api-trace` | `false` | Log every API call/response — great for debugging |

---

### 6.2 `upload from-folder`

Uploads photos from local folders **or ZIP archives** — no need to unzip first.

```bash
immich-go upload from-folder [options] <folder-path>
```

**Specific options**

| Option | Default | Description |
|---|---|---|
| `--recursive` | `true` | Recurse into sub-folders |
| `--date-from-name` | `true` | Extract the date from the filename if no metadata date exists |
| `--ignore-sidecar-files` | `false` | Skip `.xmp` sidecar files |

**File filtering**

| Option | Default | Description |
|---|---|---|
| `--include-extensions` | all | Comma-separated list of extensions to include |
| `--exclude-extensions` | – | Comma-separated list of extensions to exclude |
| `--include-type` | all | `IMAGE`, `VIDEO`, or `all` |
| `--ban-file` | See [banned files](#banned-files) | Exclude files by pattern (repeatable) |
| `--date-range` | – | Restrict to a date range (see [Date Range Formats](#date-range-formats)) |

**Album management**

| Option | Default | Description |
|---|---|---|
| `--folder-as-album` | `NONE` | Create albums from folder structure: `FOLDER`, `PATH`, or `NONE` |
| `--folder-as-tags` | `false` | Turn the folder structure into hierarchical tags |
| `--album-path-joiner` | `" / "` | String used to join nested folder names into an album title |
| `--album-picasa` | `false` | Use the album name found in `.picasa.ini` files |
| `--into-album` | – | Force everything into one specified album |

**File management (burst / RAW+JPEG / HEIC+JPEG / Epson)**

| Option | Values | Description |
|---|---|---|
| `--manage-burst` | `NoStack`, `Stack`, `StackKeepRaw`, `StackKeepJPEG` | [Burst photo handling](#burst-detection) |
| `--manage-raw-jpeg` | `NoStack`, `KeepRaw`, `KeepJPG`, `StackCoverRaw`, `StackCoverJPG` | [RAW+JPEG handling](#raw--jpeg-pairing) |
| `--manage-heic-jpeg` | `NoStack`, `KeepHeic`, `KeepJPG`, `StackCoverHeic`, `StackCoverJPG` | [HEIC+JPEG handling](#heic--jpeg-pairing) |
| `--manage-epson-fastfoto` | `false` | Stack Epson FastFoto scanner triplets |

**Examples**

```bash
# Basic folder upload
immich-go upload from-folder --server=http://localhost:2283 --api-key=your-key /path/to/photos

# Create albums from folder structure
immich-go upload from-folder --folder-as-album=FOLDER --server=http://localhost:2283 --api-key=your-key /photos

# Stack RAW+JPEG files, keeping RAW as the cover image
immich-go upload from-folder --manage-raw-jpeg=StackCoverRaw --server=http://localhost:2283 --api-key=your-key /photos

# Filter by year and file type
immich-go upload from-folder --date-range=2023 --include-type=IMAGE --server=http://localhost:2283 --api-key=your-key /photos

# Upload straight from a ZIP archive (no extraction needed)
immich-go upload from-folder --server=http://localhost:2283 --api-key=your-key /path/to/photo-archive.zip
```

---

### 6.3 `upload from-google-photos`

The flagship feature of the tool — imports **Google Photos Takeout** archives, doing its best to reconcile the messy JSON-sidecar metadata Google produces.

```bash
immich-go upload from-google-photos [options] <takeout-path>
```

**Takeout handling**

| Option | Default | Description |
|---|---|---|
| `-u, --include-unmatched` | `false` | Import files that have **no** matching JSON metadata file |
| `-a, --include-archived` | `true` | Import photos marked "archived" in Google Photos |
| `-t, --include-trashed` | `false` | Import photos marked as trashed |
| `-p, --include-partner` | `true` | Import your partner-shared photos |

**Album options**

| Option | Default | Description |
|---|---|---|
| `--sync-albums` | `true` | Auto-create Immich albums matching your Google Photos albums |
| `--include-untitled-albums` | `false` | Also include photos that only belong to untitled albums |
| `--from-album-name` | – | Only import photos from one specific Google Photos album |
| `--partner-shared-album` | – | Put partner-shared photos into a specific named album |

**Tagging**

| Option | Default | Description |
|---|---|---|
| `--takeout-tag` | `true` | Tag assets with `{takeout}/takeout-YYYYMMDDTHHMMSSZ` |
| `--people-tag` | `true` | Tag assets with `people/<name>` from Google's face-recognition JSON data |

**File management**: identical burst / RAW+JPEG / HEIC+JPEG options as `from-folder` (see §6.2).

**Examples**

```bash
# Basic import — can pass multiple split ZIPs via a glob
immich-go upload from-google-photos --server=http://localhost:2283 --api-key=your-key /path/to/takeout-*.zip

# Import including files with no JSON metadata match
immich-go upload from-google-photos --include-unmatched --server=http://localhost:2283 --api-key=your-key /takeout

# Import only one specific album
immich-go upload from-google-photos --from-album-name="Vacation 2023" --server=http://localhost:2283 --api-key=your-key /takeout

# Exclude partner photos and trashed items
immich-go upload from-google-photos --include-partner=false --include-trashed=false --server=http://localhost:2283 --api-key=your-key /downloads/takeout-*.zip
```

> See [§11 Technical Deep Dive](#google-photos-json-processing) for exactly what data Immich-Go extracts from Google's JSON sidecars (GPS, people, capture time, album, favorite/archive/trash flags).

---

### 6.4 `upload from-icloud`

Uploads photos from an **iCloud takeout export**.

```bash
immich-go upload from-icloud [options] <icloud-path>
```

| Option | Default | Description |
|---|---|---|
| `--memories` | `false` | Import iCloud "Memories" as albums |

**Examples**

```bash
# Basic iCloud import
immich-go upload from-icloud --server=http://localhost:2283 --api-key=your-key /path/to/icloud-export

# Include Memories as albums, stacking HEIC/JPEG pairs
immich-go upload from-icloud --memories --manage-heic-jpeg=StackCoverJPG --server=http://localhost:2283 --api-key=your-key /path/to/icloud-export
```

---

### 6.5 `upload from-picasa`

Uploads a **Picasa** photo collection, automatically detecting Picasa metadata (`.picasa.ini` files for album names, etc.).

```bash
immich-go upload from-picasa [options] <picasa-path>
```

It uses the exact same option set as `from-folder`, plus automatic Picasa metadata detection (`--album-picasa`).

---

### 6.6 `upload from-immich`

Transfers assets **directly between two Immich servers** — no intermediate local export needed. This is the primary tool for server-to-server migrations.

```bash
immich-go upload from-immich [source-options] [destination-options]
```

Destination options are the same server-connection flags used everywhere else (`--server`, `--api-key`, etc.) — the source server gets its own mirrored set of flags, all prefixed with `from-`.

**Source server options**

| Option | Description |
|---|---|
| `--from-server` | Source Immich server URL |
| `--from-api-key` | Source server API key |
| `--from-admin-api-key` | Source server admin API key |
| `--from-client-timeout` | Source server call timeout (default `20m0s`) |
| `--from-skip-verify-ssl` | Skip SSL verification for the source |
| `--from-device-uuid` | Set a device UUID for the source (default `"K3502ZA"`) |
| `--from-api-trace` | Enable API trace logging on the source |
| `--from-dry-run` | Simulate source actions |
| `--from-pause-immich-jobs` | Pause jobs on the source server during read (default `true`) |

**Source filtering** (the fullest filtering surface in the whole tool — see the [environment variable table](#10-environment-variables) for the complete list, which also includes `--from-city`, `--from-country`, `--from-state`, `--from-make`, `--from-model`, `--from-no-album`, `--from-albums`, `--from-people`, `--from-tags`, and more)

| Option | Description |
|---|---|
| `--from-date-range` | Date-range filter applied to the source |
| `--from-archived` | Include archived source assets |
| `--from-trash` | Include trashed source assets |
| `--from-favorite` | Only include favorited source assets |
| `--from-minimal-rating` | Minimum star rating filter |
| `--from-exclude-extensions` | Comma-separated list of extensions to exclude |
| `--from-include-extensions` | Comma-separated list of extensions to include |
| `--from-include-type` | Single file type to include (`VIDEO` or `IMAGE`) |
| `--from-partners` | Get partner's assets as well |
| `--from-time-zone` | Override time zone for source assets |

**Examples**

```bash
# Transfer everything between two servers
immich-go upload from-immich \
  --from-server=http://old-server:2283 --from-api-key=old-key \
  --server=http://new-server:2283 --api-key=new-key

# Transfer only assets rated 3 stars or higher
immich-go upload from-immich \
  --from-server=http://old-server:2283 --from-api-key=old-key --from-minimal-rating=3 \
  --server=http://new-server:2283 --api-key=new-key

# Transfer a specific date range
immich-go upload from-immich \
  --from-server=http://old-server:2283 --from-api-key=old-key --from-date-range=2023-01-01,2023-06-30 \
  --server=http://new-server:2283 --api-key=new-key
```

### 6.7 Upload Performance Tips

- **Concurrent tasks**: start with the default (CPU-core count), then tune up or down based on your network/server capacity.
- **Large video files**: increase `--client-timeout`.
- **Unstable networks**: lower `--concurrent-tasks`.
- **Heavy uploads**: keep `--pause-immich-jobs=true` so the server isn't fighting thumbnail/ML jobs while ingesting.

---

## 7. The `archive` Command

The `archive` command **exports** photos and videos from any of the same five sources into a **local, date-organized folder structure**. It is not destructive — the destination folder is **never wiped**, so you can run it repeatedly to add newly-created assets to an existing archive.

```bash
immich-go archive <sub-command> --write-to-folder=<destination> [options] <source>
```

### 7.1 Required Option

| Option | Description |
|---|---|
| `--write-to-folder` | Destination folder for the archive |

### 7.2 Sub-Commands

All five `upload` sub-commands are available under `archive` as well, with identical filtering/organization options — only the destination changes (disk instead of a server):

| Sub-command | Source |
|---|---|
| `from-folder` | Local filesystem / ZIP archives |
| `from-google-photos` | Google Takeout |
| `from-icloud` | iCloud export |
| `from-picasa` | Picasa collection |
| `from-immich` | Another Immich server |

### 7.3 Output Structure

Assets are organized **chronologically by year and month**:

```
destination-folder/
├── 2022/
│   ├── 2022-01/
│   │   ├── photo01.jpg
│   │   └── photo01.jpg.JSON     ← metadata sidecar
│   └── 2022-02/
│       ├── photo02.jpg
│       └── photo02.jpg.JSON
├── 2023/
│   ├── 2023-03/
│   └── 2023-04/
└── 2024/
    ├── 2024-05/
    └── 2024-06/
```

### 7.4 Metadata Sidecar Files

Every archived asset gets a companion `.JSON` file capturing everything Immich-Go knows about it:

- Original filename and capture date
- GPS coordinates (lat/long)
- Album associations
- Tags and descriptions
- Rating and favorite status
- Archive/trash status

**Example metadata file**

```json
{
  "fileName": "example.jpg",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "dateTaken": "2023-10-01T12:34:56Z",
  "description": "Golden Gate Bridge view",
  "albums": [
    {
      "title": "San Francisco Trip",
      "description": "Photos from my trip"
    }
  ],
  "tags": [
    { "value": "USA/California/San Francisco" }
  ],
  "rating": 5,
  "trashed": false,
  "archived": false,
  "favorited": true,
  "fromPartner": false
}
```

### 7.5 Examples

```bash
# Archive everything currently on the server
immich-go archive from-immich \
  --server=http://localhost:2283 --api-key=your-key \
  --write-to-folder=/backup/photos

# Archive only a specific year
immich-go archive from-immich \
  --server=http://localhost:2283 --api-key=your-key \
  --from-date-range=2023 \
  --write-to-folder=/backup/2023-photos

# Archive one album only
immich-go archive from-immich \
  --server=http://localhost:2283 --api-key=your-key \
  --from-albums="Family" \
  --write-to-folder=/backup/albums

# Turn a raw Google Takeout into a clean, organized folder tree
immich-go archive from-google-photos \
  --write-to-folder=/organized-photos \
  /path/to/takeout-*.zip

# Reorganize a messy local folder into a date-based structure
immich-go archive from-folder \
  --write-to-folder=/organized \
  /messy/photo/folders

# Archive from iCloud export
immich-go archive from-icloud \
  --write-to-folder=/organized-icloud \
  --memories \
  /path/to/icloud-export

# Archive from Picasa folders
immich-go archive from-picasa \
  --write-to-folder=/organized-picasa \
  /path/to/picasa-export
```

### 7.6 Common Use Cases

1. **Server backup** — a complete, human-readable copy of everything on your Immich server.
2. **Migration preparation** — stage assets before importing into a different system.
3. **Photo organization** — turn a chaotic pile of folders into a clean date-based hierarchy.
4. **Selective archival** — export just one year, one album, or a filtered subset.

### 7.7 Important Behavior Notes

- **Incremental**: you can re-run an archive command against the same destination — new assets are added, existing ones are left alone.
- **Metadata preservation**: nothing is lost — everything ends up in the `.JSON` sidecar.
- **Cross-platform**: an archive folder can later be re-imported into any Immich-compatible tool.
- **Space-efficient**: no duplicate copies are created on repeat runs.
- **Archive-only**: deletions on the source are **not** mirrored — files already archived are never removed from the archive folder.

---

## 8. The `stack` Command

`stack` organizes **assets that are already on your Immich server** into stacks — it does **not** upload anything new.

```bash
immich-go stack [options]
```

### 8.1 What Stacking Is For

- **Burst photos** from rapid continuous shooting
- **RAW + JPEG** pairs from cameras shooting both formats simultaneously
- **HEIC + JPEG** pairs, common with iPhone Live Photos
- **Epson FastFoto** scan triplets (original / corrected / back side)

### 8.2 Required & Connection Options

| Option | Required | Description |
|---|---|---|
| `-s, --server` | ✅ | Immich server URL |
| `-k, --api-key` | ✅ | API key |
| `--admin-api-key` | | Admin API key (needed to manage and pause server jobs) |
| `--skip-verify-ssl` | | Skip SSL verification (default `false`) |
| `--client-timeout` | | Server call timeout (default `20m`) |
| `--api-trace` | | Trace API calls (default `false`) |

### 8.3 Behavior Options

| Option | Default | Description |
|---|---|---|
| `--dry-run` | `false` | Preview stacking without making changes |
| `--time-zone` | System | Override the timezone used for date-based comparisons |

### 8.4 Stacking Rules

**Burst photos** — `--manage-burst`: `NoStack`, `Stack`, `StackKeepRaw`, `StackKeepJPEG`

Detection combines:
- **Time-based**: photos taken within **900ms** of each other
- **Filename patterns**: device-specific naming schemes (see the device table in [§11](#filename-based-detection))

**RAW + JPEG** — `--manage-raw-jpeg`: `NoStack` | `KeepRaw` | `KeepJPG` | `StackCoverRaw` | `StackCoverJPG`

| Value | Effect |
|---|---|
| `NoStack` | Leave files separate |
| `KeepRaw` | Delete the JPEG, keep only RAW |
| `KeepJPG` | Delete the RAW, keep only JPEG |
| `StackCoverRaw` | Stack the pair with the RAW file as the visible cover |
| `StackCoverJPG` | Stack the pair with the JPEG file as the visible cover |

**HEIC + JPEG** — `--manage-heic-jpeg`: same five-value logic as RAW+JPEG (`NoStack`, `KeepHeic`, `KeepJPG`, `StackCoverHeic`, `StackCoverJPG`).

**Epson FastFoto** — `--manage-epson-fastfoto` (boolean, default `false`)

File pattern:
```
image-name.jpg      (original scan)
image-name_a.jpg    (corrected scan)
image-name_b.jpg    (back of the photo)
```
When enabled, all three are stacked together with the corrected scan (`_a`) as the cover.

### 8.5 Examples

```bash
# Stack burst photos automatically
immich-go stack --server=http://localhost:2283 --api-key=your-key --manage-burst=Stack

# Preview stacking without applying it
immich-go stack --server=http://localhost:2283 --api-key=your-key --manage-burst=Stack --dry-run

# Stack RAW+JPEG with RAW as cover
immich-go stack --server=http://localhost:2283 --api-key=your-key --manage-raw-jpeg=StackCoverRaw

# Handle everything at once: bursts, RAW+JPEG, HEIC+JPEG, and Epson scans
immich-go stack \
  --server=http://localhost:2283 --api-key=your-key \
  --manage-burst=Stack \
  --manage-raw-jpeg=StackCoverRaw \
  --manage-heic-jpeg=StackCoverJPG \
  --manage-epson-fastfoto=true
```

### 8.6 Detection Logic Summary

**Burst detection priority**: 1) device-specific filename pattern, 2) 900ms time-based fallback.

**File-pairing logic**: 1) exact filename match (different extension), 2) same directory, 3) similar/close timestamps.

### 8.7 Stack Best Practices

1. **Always test first** with `--dry-run`.
2. **Go incrementally** — handle bursts, then RAW+JPEG, then HEIC+JPEG as separate runs, rather than everything at once, so you can verify each stage.
3. **Back up before major reorganization**, e.g. with `archive from-immich --write-to-folder=/backup`.
4. **Monitor with logging**: `--log-level=DEBUG --log-file=/tmp/stacking.log`.

### 8.8 Stack Troubleshooting

| Symptom | What to check |
|---|---|
| Nothing gets stacked | Verify timestamps/filenames match a supported device pattern; try `--api-trace`; try `--dry-run --log-level=DEBUG` |
| Unexpected/over-aggressive stacking | Review whether the 900ms time-based fallback is grouping unrelated shots; prefer filename-pattern detection for known devices |
| Slow performance on large libraries | Increase `--client-timeout`; process in smaller date-range batches |

---

## 9. Configuration Files (TOML / YAML / JSON)

Instead of typing out long command lines every time, Immich-Go can read settings from a config file. By default it looks for a file named **`immich-go.toml`** in the current directory. **TOML, YAML, and JSON** are all supported — pick whichever syntax you prefer.

The configuration file mirrors the CLI flag structure exactly: top-level global settings (`concurrent-tasks`, `dry-run`, `log-file`, `log-level`, `log-type`, `on-errors`, `save-config`), then a section per command (`[upload]`, `[archive]`, `[stack]`), each containing sub-sections per sub-command (`[upload.from-folder]`, `[upload.from-google-photos]`, etc.).

### 9.1 TOML Example (abridged — top-level + one sub-command)

```toml
concurrent-tasks = 12
dry-run = false
log-file = ''
log-level = 'INFO'
log-type = 'text'
on-errors = 'stop'
save-config = false

[upload]
api-key = 'YOUR-API-KEY'
server = 'https://immich.app'
client-timeout = '20m'
device-uuid = 'HOSTNAME'
dry-run = false
manage-burst = 'NoStack'
manage-heic-jpeg = 'NoStack'
manage-raw-jpeg = 'NoStack'
overwrite = false
pause-immich-jobs = true
session-tag = false
skip-verify-ssl = false

[upload.from-folder]
album-path-joiner = ' / '
date-from-name = true
date-range = '2024-01-15,2024-03-31'
folder-as-album = 'NONE'
folder-as-tags = false
ignore-sidecar-files = false
into-album = ''
recursive = true

[upload.from-google-photos]
date-range = '2024-01-15,2024-03-31'
from-album-name = ''
include-archived = true
include-partner = true
include-trashed = false
include-unmatched = false
include-untitled-albums = false
people-tag = true
sync-albums = true
takeout-tag = true
```

> The full structure also includes `[archive]` and `[stack]` sections plus every `from-*` sub-command (`from-icloud`, `from-picasa`, `from-immich`) for both `upload` and `archive` — each with its own complete option block. Nested tables like `[upload.from-immich.from-albums]`, `[...from-people]`, and `[...from-tags]` hold list-type filters (album names, people, tags).

### 9.2 YAML Equivalent (excerpt)

```yaml
concurrent-tasks: 12
dry-run: false
log-level: INFO
upload:
  api-key: YOUR-API-KEY
  server: https://immich.app
  from-folder:
    date-range: 2024-01-15,2024-03-31
    folder-as-album: NONE
    recursive: true
  from-google-photos:
    include-partner: true
    sync-albums: true
    takeout-tag: true
```

### 9.3 JSON Equivalent (excerpt)

```json
{
  "concurrent-tasks": 12,
  "dry-run": false,
  "upload": {
    "api-key": "YOUR-API-KEY",
    "server": "https://immich.app",
    "from-folder": {
      "date-range": "2024-01-15,2024-03-31",
      "folder-as-album": "NONE",
      "recursive": true
    }
  }
}
```

### 9.4 Auto-Saving Your Config

Set the global flag/setting `--save-config=true` (or `save-config = true` in the file) and Immich-Go will persist your current settings to `immich-go.yaml`, so you can build a working command once interactively and then reuse it non-interactively later (e.g. in cron).

### 9.5 Custom Configuration Path

By default, `immich-go` looks for `immich-go.toml` (or `.yaml` / `.json`) in the current directory. You can specify a custom configuration file path using the global `--config` flag:

```bash
immich-go --config=/path/to/my-config.yaml upload from-folder /photos
```

---

## 10. Environment Variables

Every single CLI flag also has a corresponding environment variable, which is extremely useful for containerized deployments, CI pipelines, or keeping secrets out of shell history. The naming pattern is:

```
IMMICH_GO_<COMMAND>[_<SUBCOMMAND>]_<OPTION_NAME>
```

all upper-case, with dashes in the flag name replaced by underscores.

### 10.1 Global Variables

| Variable | Flag | Default | Description |
|---|---|---|---|
| `IMMICH_GO_CONCURRENT_TASKS` | `--concurrent-tasks` | `12` | Number of concurrent tasks (1–20) |
| `IMMICH_GO_DRY_RUN` | `--dry-run` | `false` | Dry run |
| `IMMICH_GO_LOG_FILE` | `--log-file` | – | Write logs to this file |
| `IMMICH_GO_LOG_LEVEL` | `--log-level` | `INFO` | `DEBUG`/`INFO`/`WARN`/`ERROR` |
| `IMMICH_GO_LOG_TYPE` | `--log-type` | `text` | `text` or `json` |
| `IMMICH_GO_ON_ERRORS` | `--on-errors` | `stop` | `stop`, `continue`, or a tolerated error count |
| `IMMICH_GO_SAVE_CONFIG` | `--save-config` | `false` | Persist current config to `immich-go.yaml` |

### 10.2 Pattern for Command-Specific Variables

Rather than reproduce all ~150 environment-variable rows here (one per CLI flag across `upload`, `archive`, and `stack`, and each of their five `from-*` sub-commands), the pattern is entirely predictable. A few representative examples:

| Variable | Equivalent Flag | Default | Description |
|---|---|---|---|
| `IMMICH_GO_UPLOAD_SERVER` | `upload --server` | – | Immich server address |
| `IMMICH_GO_UPLOAD_API_KEY` | `upload --api-key` | – | API key |
| `IMMICH_GO_UPLOAD_SESSION_TAG` | `upload --session-tag` | `false` | Tag with `{immich-go}/YYYY-MM-DD HH-MM-SS` |
| `IMMICH_GO_UPLOAD_MANAGE_RAW_JPEG` | `upload --manage-raw-jpeg` | `NoStack` | RAW+JPEG handling mode |
| `IMMICH_GO_UPLOAD_FROM_FOLDER_FOLDER_AS_ALBUM` | `upload from-folder --folder-as-album` | `NONE` | `FOLDER`, `PATH`, or `NONE` |
| `IMMICH_GO_UPLOAD_FROM_GOOGLE_PHOTOS_INCLUDE_UNMATCHED` | `upload from-google-photos --include-unmatched` | `false` | Import files with no JSON metadata |
| `IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_MINIMAL_RATING` | `upload from-immich --from-minimal-rating` | `0` | Minimum rating filter on source |
| `IMMICH_GO_ARCHIVE_WRITE_TO_FOLDER` | `archive --write-to-folder` | – | Destination path for the archive |
| `IMMICH_GO_STACK_MANAGE_BURST` | `stack --manage-burst` | `NoStack` | Burst-stacking mode |

**Ban-file default** (applies to every `*_BAN_FILE` variable across all sub-commands):

```
'@eaDir/', '@__thumb/', 'SYNOFILE_THUMB_*.*', 'Lightroom Catalog/', 'thumbnails/',
'.DS_Store', '/._*', '.Spotlight-V100/', '.photostructure/', 'Recently Deleted/'
```

> **Rule of thumb**: take any flag name from the tables in §6–§8, upper-case it, replace `-` with `_`, and prefix with `IMMICH_GO_<COMMAND>_[<SUBCOMMAND>_]`. For example, `--from-city` under `archive from-immich` becomes `IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_CITY`.

### 10.3 Filter Variables That Take Lists

A handful of `from-immich` filtering options are **repeatable lists** rather than scalars, both as flags and as environment/config values:

- `--from-albums` (env: `..._FROM_ALBUMS`, default `[]`) — restrict to specific albums, usable multiple times
- `--from-people` (env: `..._FROM_PEOPLE`, default `[]`) — restrict to specific tagged people
- `--from-tags` (env: `..._FROM_TAGS`, default `[]`) — restrict to specific tags

These exist for both `upload from-immich` and `archive from-immich`.

---

## 11. Technical Deep Dive

### 11.1 Supported File Types

Immich-Go supports the same formats Immich itself supports:

**Images**: `.jpg`/`.jpeg`, `.heic`/`.heif` (Apple), RAW formats (`.dng`, `.cr2`, `.cr3`, `.arw`, `.raf`, `.nef`, `.rw2`, `.orf`), plus `.png`, `.gif`, `.bmp`, `.tiff`, `.webp`.

**Videos**: `.mp4`, `.mov`, `.avi`, `.mkv` (common); `.3gp`, `.m4v` (mobile); `.mts`, `.m2ts` (professional).

**Metadata**: `.xmp` sidecar files, Google Photos `.json` files, Immich-Go's own archive `.JSON` files.

### 11.2 Banned Files

Immich-Go automatically excludes common junk/clutter patterns. A **trailing `/`** means the pattern matches a **directory**; no trailing slash means it matches individual **files**.

| Pattern | Source | Description |
|---|---|---|
| `@eaDir/` | Synology NAS | Thumbnail directory |
| `@__thumb/` | Synology NAS | Thumbnail directory |
| `SYNOFILE_THUMB_*.*` | Synology NAS | Thumbnail files |
| `Lightroom Catalog/` | Adobe Lightroom | Catalog directory |
| `thumbnails/` | Various | Generic thumbnail folder |
| `.DS_Store` | macOS | Finder metadata file |
| `/._*` | macOS | Resource-fork stub files |
| `.Spotlight-V100/` | macOS | Spotlight index folder |
| `.photostructure/` | PhotoStructure | Application data |
| `Recently Deleted/` | iCloud | Recently-deleted items |

Add more with repeated `--ban-file` flags, e.g. `--ban-file="*screenshot*" --ban-file="*Screen Shot*"`.

### 11.3 Date Extraction

Immich-Go tries multiple sources in this priority order:

1. **EXIF metadata** (primary — read directly from the image file)
2. **XMP sidecar** file
3. **JSON metadata** (Google Photos or Immich-Go's own archive format)
4. **Filename parsing** (last resort)

#### Filename Date Patterns Recognized

| Pattern | Example | Format |
|---|---|---|
| ISO Format | `2023-07-15_14-30-25.jpg` | `YYYY-MM-DD_HH-MM-SS` |
| Timestamp | `IMG_20230715_143025.jpg` | `IMG_YYYYMMDD_HHMMSS` |
| Phone Format | `20230715_143025.jpg` | `YYYYMMDD_HHMMSS` |
| Screenshot | `Screenshot 2023-07-15 at 14.30.25.jpg` | Various |

#### Date Range Formats

| Input | Interpretation |
|---|---|
| `2023` | Jan 1 – Dec 31, 2023 |
| `2023-07` | July 1–31, 2023 |
| `2023-07-15` | Single day |
| `2023-01-15,2023-03-15` | Explicit start,end range |

### 11.4 Metadata Handling

#### XMP Sidecar Processing

XMP files are passed through to the Immich server **without modification**. Immich itself reads them for: date/time, GPS location, hierarchical tags/keywords, descriptions/titles, and technical camera data.

#### Google Photos JSON Processing

Google's per-photo JSON sidecar contains rich metadata that Immich-Go parses and applies:

```json
{
  "title": "IMG_20230715_143025.jpg",
  "description": "Family vacation photo",
  "imageViews": "1",
  "creationTime": {
    "timestamp": "1689424225",
    "formatted": "Jul 15, 2023, 2:30:25 PM UTC"
  },
  "geoData": {
    "latitude": 37.7749,
    "longitude": -122.4194,
    "altitude": 0.0,
    "latitudeSpan": 0.0,
    "longitudeSpan": 0.0
  },
  "people": [
    { "name": "John Doe" }
  ]
}
```

Extracted: album memberships, GPS coordinates, capture date, people tags, and status flags (favorite / archived / trashed / partner-shared).

#### Immich-Go's Own Archive Metadata Format

When you run `archive`, each asset gets a `.JSON` sidecar in this format (see §7.4 for the full example) — it round-trips cleanly if you later `upload from-folder` the archive back in.

### 11.5 Burst Detection

**Time-based detection**: groups consecutive photos taken within a **900ms** threshold. Simple, but can occasionally over-group unrelated rapid shots.

**Filename-based detection** (preferred, more precise — checked first):

| Device | Pattern | Example |
|---|---|---|
| Huawei | `IMG_YYYYMMDD_HHMMSS_BURSTXXX[_COVER].jpg` | `IMG_20231014_183246_BURST001_COVER.jpg` / `..._BURST002.jpg` |
| Google Pixel | `PXL_YYYYMMDD_HHMMSSXXX.MOTION-XX.COVER/ORIGINAL.jpg` | `PXL_20230330_184138390.MOTION-01.COVER.jpg` |
| Samsung | `YYYYMMDD_HHMMSS_XXX.jpg` | `20231207_101605_001.jpg` |
| Sony Xperia | `DSC_XXXX_BURSTYYYYMMDDHHMMSSXXX[_COVER].JPG` | `DSC_0001_BURST20230709220904977.JPG` |
| Google Nexus | `0000XIMG_0000X_BURSTYYYYMMDDHHMMSS[_COVER].jpg` | `00001IMG_00001_BURST20171111030039.jpg` |
| Nothing Phone | `0000XIMG_0000X_BURSTXXXXXXXXXXXXX[_COVER].jpg` | `00001IMG_00001_BURST1723801037429_COVER.jpg` |

**Detection priority**: filename pattern first, then the 900ms time-based fallback.

### 11.6 RAW + JPEG Pairing

**Detection algorithm**: 1) matching filename (different extension), 2) same directory, 3) close timestamps, 4) sanity check that the RAW file is meaningfully larger than the JPEG.

**Supported RAW extensions**: `.cr2`/`.cr3` (Canon), `.nef` (Nikon), `.arw` (Sony), `.raf` (Fujifilm), `.orf` (Olympus), `.rw2` (Panasonic), `.dng` (Adobe/generic).

```
IMG_1234.CR3  (RAW)
IMG_1234.JPG  (JPEG)
→ paired automatically for stacking/management
```

### 11.7 HEIC + JPEG Pairing

Common on Apple devices that export both formats for the same shot. Detection: same base filename, different extension.

### 11.8 Epson FastFoto Detection

```
photo-name.jpg      (original scan)
photo-name_a.jpg    (corrected scan)
photo-name_b.jpg    (back of the photo)
→ all three stacked with the corrected (_a) version as cover
```

### 11.9 Upload Processing: Duplicate Detection

**Server-side deduplication logic**:

1. **Checksum comparison** — SHA-1 hash of file content
2. **Metadata match** — filename + timestamp comparison
3. **Size validation**
4. **Skip logic** — existing files are skipped unless `--overwrite` is passed

**Benefits**: uploads are safely **resumable**, the same photo arriving from multiple sources is handled gracefully, and no wasted storage from accidental duplicates.

### 11.10 Concurrency Management

- **Default workers**: number of CPU cores
- **Range**: 1–20 concurrent uploads
- **Bottleneck**: almost always network bandwidth, not CPU (uploads are I/O bound)

| Concurrent Uploads | Network Utilization | Server Load | Reliability |
|---|---|---|---|
| 1 | Low | Minimal | Highest |
| 2–4 | Moderate | Low | High |
| 8–12 | High | Moderate | Good |
| 16+ | Maximum | High | Variable |

**Resource usage**: roughly 10–50 MB of memory per concurrent upload; network usage scales linearly with concurrency; CPU impact is minimal.

### 11.11 Archive Structure Internals

- **Filename preservation**: original filenames are kept where possible; numeric suffixes (`IMG_001(1).jpg`) resolve conflicts; filesystem-incompatible characters are sanitized.
- **Metadata files**: `original-name.ext.JSON` sidecar, plus original `.xmp` files copied alongside.
- **Incremental updates**: new files are added to the right date folder; existing files are checked and refreshed if changed; deletions on the source are **never** propagated (archive-only, non-destructive).
- **Temporary files**: minimal use, stored in the system temp dir or `IMMICHGO_TEMPDIR`, auto-cleaned on exit.

### 11.12 API Compatibility Monitoring

The project runs **automated daily monitoring** of the Immich API spec via GitHub Actions, opening issues automatically when upstream API changes are detected. You can also run `./scripts/check-immich-api.sh` locally from a source checkout to check manually.

---

## 12. Practical Examples & Recipes

### 12.1 Local Photo Upload

```bash
# Upload an entire photo collection
immich-go upload from-folder \
  --server=http://localhost:2283 --api-key=your-api-key \
  /home/user/Pictures

# Create albums that mirror your folder structure, stacking RAW+JPEG
immich-go upload from-folder \
  --server=http://localhost:2283 --api-key=your-api-key \
  --folder-as-album=FOLDER --manage-raw-jpeg=StackCoverRaw \
  /home/user/Pictures/Organized

# Tag everything with custom tags plus an automatic session tag
immich-go upload from-folder \
  --server=http://localhost:2283 --api-key=your-api-key \
  --tag="Import/2024" --tag="Source/LocalFiles" --session-tag \
  /home/user/Pictures

# Upload directly from a zipped photo archive
immich-go upload from-folder \
  --server=http://localhost:2283 --api-key=your-api-key \
  /path/to/photo-archive.zip
```

### 12.2 Google Photos Migration

```bash
# Import every part of a split takeout, with burst + RAW/JPEG handling
immich-go upload from-google-photos \
  --server=http://localhost:2283 --api-key=your-api-key \
  --manage-raw-jpeg=StackCoverRaw --manage-burst=Stack \
  /downloads/takeout-*.zip

# Skip partner photos and anything already trashed
immich-go upload from-google-photos \
  --server=http://localhost:2283 --api-key=your-api-key \
  --include-partner=false --include-trashed=false \
  /downloads/takeout-*.zip

# Import just one album
immich-go upload from-google-photos \
  --server=http://localhost:2283 --api-key=your-api-key \
  --from-album-name="Vacation 2023" \
  /downloads/takeout-*.zip

# Tuned for a very large takeout (100k+ photos)
immich-go upload from-google-photos \
  --server=http://localhost:2283 --api-key=your-api-key \
  --concurrent-tasks=4 --client-timeout=60m \
  --pause-immich-jobs=true --on-errors=continue --session-tag \
  /downloads/takeout-*.zip
```

### 12.3 iCloud Import

```bash
immich-go upload from-icloud \
  --server=http://localhost:2283 --api-key=your-api-key \
  --manage-heic-jpeg=StackCoverJPG \
  /path/to/icloud-export

# ...plus Memories as albums
immich-go upload from-icloud \
  --server=http://localhost:2283 --api-key=your-api-key \
  --memories --manage-heic-jpeg=StackCoverJPG \
  /path/to/icloud-export
```

### 12.4 Server Backup (Archive)

```bash
# Full backup
immich-go archive from-immich \
  --server=http://localhost:2283 --api-key=your-api-key \
  --write-to-folder=/backup/immich-complete

# Last 30 days only
immich-go archive from-immich \
  --server=http://localhost:2283 --api-key=your-api-key \
  --from-date-range=$(date -d '30 days ago' '+%Y-%m-%d'),$(date '+%Y-%m-%d') \
  --write-to-folder=/backup/immich-recent

# Specific albums
immich-go archive from-immich \
  --server=http://localhost:2283 --api-key=your-api-key \
  --from-album="Family Photos" --from-album="Travel" \
  --write-to-folder=/backup/immich-albums

# One archive folder per year
for year in 2020 2021 2022 2023 2024; do
  immich-go archive from-immich \
    --server=http://localhost:2283 --api-key=your-api-key \
    --from-date-range=$year \
    --write-to-folder=/backup/immich-$year
done
```

### 12.5 Server-to-Server Migration

```bash
# Full transfer
immich-go upload from-immich \
  --from-server=http://old-server:2283 --from-api-key=old-api-key \
  --server=http://new-server:2283 --api-key=new-api-key \
  --concurrent-tasks=4

# One year only
immich-go upload from-immich \
  --from-server=http://old-server:2283 --from-api-key=old-api-key \
  --from-date-range=2023-01-01,2023-12-31 \
  --server=http://new-server:2283 --api-key=new-api-key

# Specific albums only
immich-go upload from-immich \
  --from-server=http://old-server:2283 --from-api-key=old-api-key \
  --from-album="Family" --from-album="Work" \
  --server=http://new-server:2283 --api-key=new-api-key
```

### 12.6 Photo Organization on an Existing Library

```bash
# Stack bursts, RAW+JPEG, and HEIC+JPEG in one pass
immich-go stack \
  --server=http://localhost:2283 --api-key=your-api-key \
  --manage-burst=Stack --manage-raw-jpeg=StackCoverRaw --manage-heic-jpeg=StackCoverJPG

# Preview first
immich-go stack \
  --server=http://localhost:2283 --api-key=your-api-key \
  --manage-burst=Stack --manage-raw-jpeg=StackCoverRaw --dry-run

# Reorganize a messy folder tree into a clean date-based archive
immich-go archive from-folder \
  --write-to-folder=/organized-photos --manage-raw-jpeg=StackCoverRaw \
  /messy/photo/folders
```

### 12.7 Selective Sync / Filtering

```bash
# Just one year
immich-go upload from-folder \
  --server=http://localhost:2283 --api-key=your-api-key \
  --date-range=2023 \
  /home/user/Pictures

# Only videos
immich-go upload from-folder \
  --server=http://localhost:2283 --api-key=your-api-key \
  --include-type=VIDEO \
  /home/user/Movies

# Only certain image formats
immich-go upload from-folder \
  --server=http://localhost:2283 --api-key=your-api-key \
  --include-extensions=.jpg,.png,.heic \
  /home/user/Pictures

# Skip large videos and screenshots
immich-go upload from-folder \
  --server=http://localhost:2283 --api-key=your-api-key \
  --exclude-extensions=.mov,.mp4 \
  --ban-file="*screenshot*" --ban-file="*Screen Shot*" \
  /home/user/Pictures
```

### 12.8 Performance Tuning Examples

```bash
# Fast network + powerful server
immich-go upload from-folder \
  --server=http://localhost:2283 --api-key=your-api-key \
  --concurrent-tasks=16 --client-timeout=30m --pause-immich-jobs=true \
  /large/photo/collection

# Slow/unstable connection
immich-go upload from-folder \
  --server=http://localhost:2283 --api-key=your-api-key \
  --concurrent-tasks=1 --client-timeout=120m --on-errors=continue \
  /photos

# Background, unattended run with logging
nohup immich-go upload from-folder \
  --server=http://localhost:2283 --api-key=your-api-key \
  --log-file=/tmp/upload.log --no-ui \
  /photos > /dev/null 2>&1 &
```

### 12.9 Debugging Examples

```bash
# Maximum verbosity, no real changes
immich-go --log-level=DEBUG --api-trace \
  upload from-folder --dry-run \
  --server=http://localhost:2283 --api-key=your-api-key \
  /test-photos

# Quick connectivity check
immich-go --log-level=DEBUG \
  archive from-immich \
  --server=http://localhost:2283 --api-key=your-api-key \
  --from-date-range=2024-01-01,2024-01-01 \
  --write-to-folder=/tmp/test --dry-run

# Large video files need a much bigger timeout and lower concurrency
immich-go upload from-folder \
  --server=http://localhost:2283 --api-key=your-api-key \
  --include-type=VIDEO --client-timeout=180m --concurrent-tasks=2 \
  /large-videos
```

---

## 13. Best Practices

### 13.1 Google Photos Takeout — Getting a Good Takeout

**Recommended settings when requesting the takeout from Google**:
- Format: **ZIP** (easier to process than TGZ)
- File size: choose the **maximum (50 GB)** to minimize the number of split parts
- Content: include **all** photos, videos, and metadata
- Make sure **every** part fully downloads before importing

**Common pitfalls**:
- Incomplete downloads — double-check every `takeout-001.zip`, `takeout-002.zip`, … is present (`ls -la takeout-*.zip`)
- Don't mix ZIP and TGZ formats within the same import
- Partial takeouts happen — if a lot of expected files are missing, request a fresh takeout

### 13.2 Import Strategy by Collection Size

| Size | Recommended flags |
|---|---|
| **100k+ photos** | `--concurrent-tasks=4 --client-timeout=60m --pause-immich-jobs=true --on-errors=continue --session-tag` (prioritize reliability) |
| **10k–100k photos** | `--concurrent-tasks=8 --manage-raw-jpeg=StackCoverRaw --manage-burst=Stack` (balanced) |
| **< 10k photos** | `--concurrent-tasks=12 --manage-raw-jpeg=StackCoverRaw --manage-burst=Stack --manage-heic-jpeg=StackCoverJPG` (fast, full processing) |

### 13.3 Troubleshooting Import Gaps

If many files seem to be missing after an import:
1. Verify takeout completeness (`ls -la takeout-*.zip`).
2. Force-import unmatched files: `--include-unmatched`.
3. If data genuinely looks incomplete, request a new takeout covering the missing period.

**Resuming an interrupted import** is safe by design — Immich-Go detects and skips already-uploaded files. Use `--session-tag` so you can track exactly what was imported and when, and check your log file to see where a previous run stopped.

### 13.4 Performance Tuning by Environment

| Environment | Recommended settings |
|---|---|
| Gigabit LAN, fast & stable | `--concurrent-tasks=16 --client-timeout=30m --pause-immich-jobs=true` |
| Regular internet, variable speed | `--concurrent-tasks=4-8 --client-timeout=60m --on-errors=continue` |
| Slow / unstable network | `--concurrent-tasks=1-2 --client-timeout=120m --on-errors=continue` |
| Powerful server (high CPU/RAM) | `--concurrent-tasks=12-20 --pause-immich-jobs=false --client-timeout=30m` |
| Limited server resources | `--concurrent-tasks=2-4 --pause-immich-jobs=true --client-timeout=60m` |
| NAS / low-power server | `--concurrent-tasks=1-2 --pause-immich-jobs=true --client-timeout=180m` |

**Storage considerations**: fast SSD storage can absorb higher concurrency (8–16); slow HDDs should reduce concurrency (2–4) and process in smaller batches; network storage should account for latency in your timeout and be tested with small batches first.

### 13.5 Organization Strategy

**Folder-based albums** — best for already-organized collections:
```bash
immich-go upload from-folder --folder-as-album=FOLDER --album-path-joiner=" - " --server=... --api-key=... /organized/photos/
```

**Date-based + tags** — best for large, mixed-source collections:
```bash
immich-go upload from-folder --tag="Source/Import2024" --tag="Camera/Canon5D" --session-tag --server=... --api-key=... /photos/
```

**Hybrid**:
```bash
immich-go upload from-folder --folder-as-album=PATH --folder-as-tags=true --tag="Import/$(date +%Y-%m)" --server=... --api-key=... /photos/
```

**RAW+JPEG workflow choice**:

| Goal | Setting |
|---|---|
| Keep both, ample storage | `--manage-raw-jpeg=NoStack` |
| Primarily edit RAW | `--manage-raw-jpeg=StackCoverRaw` |
| Primarily view JPEG, RAW as backup | `--manage-raw-jpeg=StackCoverJPG` |
| Storage-constrained, pick one | `--manage-raw-jpeg=KeepRaw` or `KeepJPG` |

**Burst workflow choice**:

| Use case | Setting |
|---|---|
| Creative photography (keep everything, less clutter) | `--manage-burst=Stack` |
| Casual photography (save storage) | `--manage-burst=StackKeepJPEG` |
| Professional (need every single shot easily selectable) | `--manage-burst=NoStack` |

**Tagging strategies** — use hierarchical tags liberally:
```bash
--tag="Location/Europe/France/Paris"
--tag="Events/2024/Wedding/Ceremony"
--tag="Equipment/Camera/Canon/5D-Mark-IV"
```
Combine multiple dimensions:
```bash
--tag="Location/Paris" --tag="Event/Wedding" --tag="People/Family" --tag="Year/2024"
```
And always tag your source/import batch for traceability:
```bash
--tag="Source/GooglePhotos" --tag="Import/$(date +%Y-%m-%d)" --session-tag
```

### 13.6 Backup & Recovery Strategy

Follow the classic **3-2-1 rule**: 3 copies total, on 2 different media, with 1 offsite.

```bash
# Local backup copy
immich-go archive from-immich --server=http://localhost:2283 --api-key=your-api-key --write-to-folder=/local-backup/immich

# Sync that copy offsite
rsync -av /local-backup/immich/ user@remote-server:/backups/immich/
```

Daily incremental + monthly full backup pattern:
```bash
#!/bin/bash
YESTERDAY=$(date -d '1 day ago' '+%Y-%m-%d')
TODAY=$(date '+%Y-%m-%d')
immich-go archive from-immich \
  --server=http://localhost:2283 --api-key=your-api-key \
  --from-date-range="$YESTERDAY,$TODAY" \
  --write-to-folder="/backup/incremental/$TODAY"
```

**Test before you trust it**: dry-run a small subset first, and periodically verify you can actually re-import from your backup folder (`upload from-folder` pointed at a backup date-folder).

### 13.7 Security & Privacy

**API key management**:
- Use **separate keys** for different purposes (upload vs. backup vs. admin).
- Grant only the **minimal permissions** each key actually needs.
- **Rotate keys** periodically.
- Never hardcode keys in scripts — read from a permission-restricted file or environment variable:

```bash
API_KEY=$(cat ~/.config/immich-go/api-key)
chmod 600 ~/.config/immich-go/api-key
# or
export IMMICH_API_KEY="your-key"
immich-go upload from-folder --api-key="$IMMICH_API_KEY" ...
```

**Network security**:
- Always use **HTTPS** in production.
- Only use `--skip-verify-ssl` for self-signed certs in a dev/test environment — never in production.
- Prefer VPN access or firewall rules restricting who can reach your Immich server; a properly-terminated reverse proxy is a good middle ground.

### 13.8 Monitoring & Error Recovery

**Logging by scenario**:

| Scenario | Flags |
|---|---|
| Dev/testing | `--log-level=DEBUG --log-file=/tmp/immich-go-debug.log --api-trace` |
| Production runs | `--log-level=INFO --log-file=/var/log/immich-go/upload-$(date +%Y%m%d).log` |
| Unattended/automated | `--log-level=WARN --log-file=/var/log/immich-go/automated.log --no-ui` |

**Health checks before/during a big job**: `df -h` on your storage and temp directories, `watch df -h` during the run, and general system monitors (`htop`, `iotop`, `nethogs`) on the server side.

**On failure**: `--on-errors=continue` plus a log file lets the job keep going and lets you review failures afterward (`grep "ERROR" logfile`). Because duplicate detection is built in, you can almost always just **re-run the exact same command** after a network interruption — Immich-Go will skip everything already uploaded.

### 13.9 Migration Planning Checklist

**Requirements**
- [ ] Immich server configured and reachable
- [ ] API key created with all necessary permissions
- [ ] Sufficient storage (budget ~1.5x source size)
- [ ] Network capacity/time budgeted
- [ ] Source data backed up independently

**Testing**
- [ ] Small-subset test run (`--dry-run`, then a real small batch)
- [ ] Verify metadata (dates, GPS, albums) survives the transfer
- [ ] Test your backup/restore procedure end-to-end
- [ ] Validate performance under expected load

**Execution phases**
1. **Test migration** — `--dry-run` against a tiny folder.
2. **Pilot migration** — a real subset, tagged (`--tag="Migration/Pilot"`).
3. **Full migration** — the complete run, with logging and session tags.

**Post-migration**
- Compare source vs. destination asset counts.
- Spot-check a random sample for quality.
- Confirm dates/locations/albums came through correctly.
- Archive the original source data (e.g. `tar -czf` the takeout ZIPs) before deleting anything, and clean up temp files.

---

## 14. Automation Scripts

### 14.1 Bash — Nightly Backup

```bash
#!/bin/bash
# backup-immich.sh
set -e

IMMICH_SERVER="http://localhost:2283"
API_KEY="your-api-key"
BACKUP_DIR="/backup/immich"
DATE=$(date '+%Y-%m-%d')

echo "Starting Immich backup: $DATE"
mkdir -p "$BACKUP_DIR/$DATE"

immich-go archive from-immich \
  --server="$IMMICH_SERVER" \
  --api-key="$API_KEY" \
  --from-date-range="$(date -d '7 days ago' '+%Y-%m-%d'),$(date '+%Y-%m-%d')" \
  --write-to-folder="$BACKUP_DIR/$DATE" \
  --log-file="$BACKUP_DIR/$DATE/backup.log"

echo "Backup completed: $BACKUP_DIR/$DATE"
```

### 14.2 PowerShell — Windows Backup

```powershell
# backup-immich.ps1
$ImmichServer = "http://localhost:2283"
$ApiKey = "your-api-key"
$BackupDir = "D:\Backup\Immich"
$Date = Get-Date -Format "yyyy-MM-dd"

Write-Host "Starting Immich backup: $Date"
New-Item -ItemType Directory -Path "$BackupDir\$Date" -Force

& immich-go archive from-immich `
  --server="$ImmichServer" `
  --api-key="$ApiKey" `
  --from-date-range="$(Get-Date (Get-Date).AddDays(-7) -Format 'yyyy-MM-dd'),$(Get-Date -Format 'yyyy-MM-dd')" `
  --write-to-folder="$BackupDir\$Date" `
  --log-file="$BackupDir\$Date\backup.log"

Write-Host "Backup completed: $BackupDir\$Date"
```

### 14.3 Cron Entries

```cron
# Daily backup at 2 AM
0 2 * * * /home/user/scripts/backup-immich.sh

# Weekly full backup on Sundays at 3 AM
0 3 * * 0 immich-go archive from-immich --server=http://localhost:2283 --api-key=your-key --write-to-folder=/backup/weekly/$(date +\%Y-\%m-\%d)
```

---

## 15. Troubleshooting

### 15.1 Installation Issues

| Problem | Fix |
|---|---|
| `Permission denied` (Linux/macOS) | `chmod +x immich-go` |
| `Command not found` | Ensure it's on `PATH`, or use a full path |
| SSL certificate errors | `--skip-verify-ssl` (dev/test only) |

### 15.2 Upload Issues

| Problem | Fix |
|---|---|
| Upload stalls or errors partway through | Reduce `--concurrent-tasks`, raise `--client-timeout`, set `--on-errors=continue`, then simply re-run the same command — duplicates are auto-skipped |
| Files silently missing after a Google Takeout import | Verify all takeout parts downloaded (`ls -la takeout-*.zip`); re-run with `--include-unmatched`; request a new takeout if data is genuinely incomplete |
| Need to see exactly what's happening | Add `--log-level=DEBUG --api-trace`, and use `--dry-run` first |
| Server seems overloaded during upload | Ensure `--pause-immich-jobs=true`; lower `--concurrent-tasks` |

### 15.3 Stack Issues

| Problem | Fix |
|---|---|
| Nothing gets stacked | Check filenames match a supported device pattern; verify timestamps; use `--api-trace`; try `--dry-run --log-level=DEBUG` |
| Too much / wrong stacking | The 900ms time-based fallback may be too aggressive; rely on filename-pattern detection where possible |
| Slow on large libraries | Increase `--client-timeout`; split work by date range |

### 15.4 General Diagnostic Workflow

1. Reproduce with `--dry-run` first — no risk of side effects.
2. Add `--log-level=DEBUG --api-trace` and a `--log-file` to capture full detail.
3. Test server connectivity in isolation with a tiny, narrow date range:
   ```bash
   immich-go --log-level=DEBUG archive from-immich \
     --server=http://localhost:2283 --api-key=your-api-key \
     --from-date-range=2024-01-01,2024-01-01 \
     --write-to-folder=/tmp/test --dry-run
   ```
4. Re-run for real once the dry run looks correct — Immich-Go's duplicate detection means re-running is always safe.
5. If you suspect an upstream API mismatch, check the project's [releases page](https://github.com/simulot/immich-go/releases) for compatibility notes, since the tool actively monitors Immich's API for breaking changes.

---

## 16. Quick-Reference Cheat Sheet

```bash
# ── INSTALL ─────────────────────────────────────────────────────
immich-go --version

# ── UPLOAD ──────────────────────────────────────────────────────
immich-go upload from-folder        --server=SERVER --api-key=KEY /path/to/photos
immich-go upload from-google-photos --server=SERVER --api-key=KEY /path/to/takeout-*.zip
immich-go upload from-icloud        --server=SERVER --api-key=KEY /path/to/icloud-export
immich-go upload from-picasa        --server=SERVER --api-key=KEY /path/to/picasa
immich-go upload from-immich \
  --from-server=OLD --from-api-key=OLD_KEY \
  --server=NEW --api-key=NEW_KEY

# ── ARCHIVE (EXPORT) ────────────────────────────────────────────
immich-go archive from-immich       --server=SERVER --api-key=KEY --write-to-folder=/backup
immich-go archive from-folder       --write-to-folder=/organized /messy/photos
immich-go archive from-google-photos --write-to-folder=/organized /takeout-*.zip

# ── STACK (ORGANIZE EXISTING ASSETS) ────────────────────────────
immich-go stack --server=SERVER --api-key=KEY --manage-burst=Stack
immich-go stack --server=SERVER --api-key=KEY --manage-raw-jpeg=StackCoverRaw
immich-go stack --server=SERVER --api-key=KEY --manage-heic-jpeg=StackCoverJPG
immich-go stack --server=SERVER --api-key=KEY --manage-epson-fastfoto=true

# ── SAFETY / TESTING ─────────────────────────────────────────────
--dry-run                 # simulate, no changes
--log-level=DEBUG         # verbose logging
--api-trace                # log every API call
--no-ui                    # disable interactive UI (for cron/scripts)

# ── COMMON FLAGS ─────────────────────────────────────────────────
-s, --server            Immich server URL
-k, --api-key           API key
--concurrent-tasks=N     Parallel task count (1-20, default = CPU cores)
--client-timeout=DUR     Per-call timeout (e.g. 20m, 60m, 180m)
--on-errors=MODE         stop | continue | <max error count>
--pause-immich-jobs      Pause server background jobs during operation
--overwrite              Replace existing server assets
--session-tag            Tag assets with the upload timestamp
--tag="Path/SubPath"     Add a hierarchical custom tag (repeatable)
--date-range=YYYY[-MM[-DD]] or "start,end"   Filter by date
--include-type=IMAGE|VIDEO
--include-extensions=.jpg,.png
--exclude-extensions=.mov,.mp4
--ban-file="pattern"     Exclude files by pattern (repeatable)
--folder-as-album=FOLDER|PATH|NONE
--manage-burst=NoStack|Stack|StackKeepRaw|StackKeepJPEG
--manage-raw-jpeg=NoStack|KeepRaw|KeepJPG|StackCoverRaw|StackCoverJPG
--manage-heic-jpeg=NoStack|KeepHeic|KeepJPG|StackCoverHeic|StackCoverJPG
```

---

## Appendix: Further Reading

- Project repository: [github.com/simulot/immich-go](https://github.com/simulot/immich-go)
- Releases & changelogs: [github.com/simulot/immich-go/releases](https://github.com/simulot/immich-go/releases)
- Issues / bug reports: [github.com/simulot/immich-go/issues](https://github.com/simulot/immich-go/issues)
- Feature requests / discussion: [github.com/simulot/immich-go/discussions](https://github.com/simulot/immich-go/discussions)

*This guide was compiled from the project's official `/docs` folder (installation.md, configuration.md, environment.md, examples.md, best-practices.md, technical.md, and commands/{README,upload,archive,stack}.md) plus the top-level README, current as of the `v0.31.0` documentation snapshot. Always cross-check flag defaults against `immich-go <command> --help` for the exact binary version you have installed, since options do evolve between releases.*
