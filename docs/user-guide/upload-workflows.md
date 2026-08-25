# Upload Workflows

Upload tabs send media **to** your Immich server. All five upload workflows require a configured server URL and API key.

| Tab | immich-go command | Source |
|-----|-------------------|--------|
| Folder | `upload from-folder` | Local directory on disk |
| Google Photos | `upload from-google-photos` | Google Takeout export |
| iCloud | `upload from-icloud` | iCloud export / library |
| Picasa | `upload from-picasa` | Picasa / Google Photos legacy export |
| Immich | `upload from-immich` | Another Immich server (migration) |

See [CLI Command Mapping](../reference/cli-command-mapping.md) for the full mapping.

## Common Fields (All Upload Tabs)

These appear in Simple mode on most upload tabs:

| Field | Description |
|-------|-------------|
| **Source path** | Folder or file containing media to upload. Supports drag-and-drop. |
| **Dry run** | Preview what would happen without uploading |
| **Date range** | Limit uploads to files within a date window |
| **Include / exclude extensions** | Filter by file type (e.g. `.jpg`, `.mp4`) |
| **Include type** | Filter by media type (image, video, etc.) |

Global connection settings from the Config tab (server URL, API key, skip SSL, timeout) apply across all upload tabs. Other runtime flags (such as `concurrent-tasks` and `on-errors`) can be enabled and configured per tab via **Advanced Flags**.

## Upload from Folder

**Command:** `immich-go upload from-folder <path>`

Upload photos and videos from a local directory tree.

**Typical use:** Bulk import from an external drive, NAS export, or organized photo library.

**Notable options (advanced):**

- `recursive` — Include subdirectories
- `folder-as-album` / `folder-as-tags` — Map directory structure to Immich albums or tags
- `date-from-name` — Parse dates from filenames
- `manage-burst`, `manage-raw-jpeg`, `manage-heic-jpeg` — Burst and RAW/HEIC pairing

## Upload from Google Photos

**Command:** `immich-go upload from-google-photos <takeout-path>`

Import from a [Google Takeout](https://takeout.google.com/) archive.

**Typical use:** Migrating from Google Photos after exporting your library.

**Notable options (advanced):**

- `include-archived`, `include-trashed`, `include-partner` — Include non-default album content
- `sync-albums` — Sync album structure to Immich
- `takeout-tag` — Tag imported items
- `from-album-name`, `partner-shared-album` — Filter by album

## Upload from iCloud

**Command:** `immich-go upload from-icloud <path>`

Import from an iCloud Photos export or compatible folder layout.

**Notable options (advanced):**

- `memories` — Handle iCloud Memories
- `folder-as-album`, `into-album` — Album mapping
- Same folder/recursive/date filters as folder upload

## Upload from Picasa

**Command:** `immich-go upload from-picasa <path>`

Import from Picasa Web Albums exports or legacy Google Photos Picasa-compatible layouts.

**Notable options (advanced):**

- `album-picasa` — Target specific Picasa albums
- Folder and extension filters similar to folder upload

## Upload from Immich

**Command:** `immich-go upload from-immich`

Copy assets from **another Immich server** to your configured destination server. Requires credentials for both source and destination.

**Additional fields:**

| Field | Description |
|-------|-------------|
| **From server URL** | Source Immich instance |
| **From API key** | Source instance API key (keyring-stored) |
| **From admin API key** | Optional source admin key |

**Notable options (advanced):**

- `from-albums`, `from-tags`, `from-people` — Filter source assets
- `from-date-range`, `from-favorite`, `from-archived` — Further source filters
- `from-partners` — Include partner-shared assets

## Running an Upload

1. Configure server and API key on the Config tab (use **Test Connection**).
2. Optionally set an **Admin API key** if you want background Immich jobs paused during the upload.
3. Select the appropriate upload sub-tab.
4. Set the source path (drag-and-drop supported).
5. Adjust filters and options as needed — prefer **Dry run** on first attempt.
6. Review the masked command preview.
7. Click **Run** — a terminal window opens running immich-go.

The GUI performs a pre-flight server connection check before launch.

### Large library tips

- Start with a date range or a single folder before the full Takeout
- Use a dedicated [profile](profiles.md) when testing against a staging Immich instance
- Watch the terminal for immich-go progress; close it only when finished so the GUI lock clears
- See [Choose Your Workflow](choose-your-workflow.md) for migration recipes

## Further Reading

- [Choose Your Workflow](choose-your-workflow.md) — Decision tree and recipes
- [Advanced Flags](advanced-flags.md) — Full flag reference per tab
- [Security & Privacy](security-and-privacy.md) — How secrets are passed
- [Environment Variables](../reference/environment-variables.md)
- [immich-go upstream docs](https://github.com/simulot/immich-go/) — CLI behavior details
