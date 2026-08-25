# Archive Workflows

Archive tabs export media **from** a source **to** a local folder. They do not upload to Immich (except Archive from Immich, which reads from a remote Immich server).

| Tab | immich-go command | Server required? |
|-----|-------------------|------------------|
| Folder | `archive from-folder` | No (serverless) |
| Google Photos | `archive from-google-photos` | No (serverless) |
| iCloud | `archive from-icloud` | No (serverless) |
| Picasa | `archive from-picasa` | No (serverless) |
| Immich | `archive from-immich` | Yes (source server only) |

## Serverless vs Server-Required

### Serverless archive tabs

These four tabs operate entirely on local files or exports. They **never** send `--server`, `--api-key`, or `--client-timeout` flags:

- Archive from Folder
- Archive from Google Photos
- Archive from iCloud
- Archive from Picasa

You do not need Immich server credentials configured to run them. The primary output destination is a **local write folder**.

### Archive from Immich

This tab connects to your **Immich server** configured on the **Configuration tab** to download/export assets to a local directory.

## Common Fields

| Field | Description |
|-------|-------------|
| **Source path** | Takeout folder, iCloud export, or local directory |
| **Write to folder** | Destination directory for archived files |
| **Dry run** | Preview without writing files |
| **Date range** | Limit by capture date |
| **Include / exclude extensions** | File type filters |

## Archive from Folder

**Command:** `immich-go archive from-folder <path> --write-to-folder <dest>`

Copy or organize local media into an archive directory structure.

**Notable options:** `recursive`, `folder-as-album`, `folder-as-tags`, `date-from-name`, `into-album`

## Archive from Google Photos

**Command:** `immich-go archive from-google-photos <takeout-path> --write-to-folder <dest>`

Extract media from a Google Takeout export to a local folder.

**Notable options:** `sync-albums`, `include-archived`, `include-partner`, `takeout-tag`, `people-tag`

## Archive from iCloud

**Command:** `immich-go archive from-icloud <path> --write-to-folder <dest>`

Archive from an iCloud Photos export.

**Notable options:** `memories`, `folder-as-album`, `recursive`

## Archive from Picasa

**Command:** `immich-go archive from-picasa <path> --write-to-folder <dest>`

Archive from Picasa-compatible exports.

**Notable options:** `album-picasa`, `folder-as-album`

## Archive from Immich

**Command:** `immich-go archive from-immich --write-to-folder <dest>`

Download assets from a remote Immich server to a local folder.

**Credentials:** Configured on the **Configuration tab** (Server URL and API Key).

**Notable options:** `from-albums`, `from-tags`, `from-people`, `from-date-range`, `from-favorite`, `from-archived`, `from-trash`

## Running an Archive

1. Select the archive sub-tab matching your source type.
2. Set source and destination paths (or configure options for Archive from Immich).
3. Review the command preview — serverless tabs will not show server/API flags.
4. Click **Run**.

Serverless tabs skip the Immich pre-flight connection check.

## Further Reading

- [Choose Your Workflow](choose-your-workflow.md) — When to archive vs upload
- [Upload Workflows](upload-workflows.md) — Upload counterpart for each source
- [CLI Command Mapping](../reference/cli-command-mapping.md)
- [Advanced Flags](advanced-flags.md)
