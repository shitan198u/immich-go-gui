Yes — this cleanup is **mostly correct**, and it fixes two real maintenance/correctness annoyances from the earlier opt-in advanced-flags work.

But I would **not** call the whole advanced-flags area fully closed yet, because this diff does not address one important secret-handling gap introduced by the opt-in advanced rows.

---

# Short verdict

## What this diff gets right

### 1. Deriving `ADVANCED_KEYS` from `ADVANCED_FLAGS` is correct
This is a good cleanup.

Before:

```python
ADVANCED_KEYS = {
    "upload-folder": { ... },
    "upload-gp": { ... },
    ...
}
```

After:

```python
ADVANCED_KEYS = {
    tab: {def_.key for def_ in defs}
    for tab, defs in ADVANCED_FLAGS.items()
}
```

This removes a duplicated source of truth.

That matters because earlier there was drift risk:

- `ADVANCED_FLAGS` defined the actual advanced rows
- `ADVANCED_KEYS` manually listed which keys were “advanced”
- the two could disagree

Now they cannot drift apart.

This also has a nice hidden benefit:

- the old hardcoded `ADVANCED_KEYS["upload-gp"]` still contained `"into-album"`
- the generated advanced registry for `upload-gp` does **not** contain `into-album`
- so this cleanup also removes that stale entry automatically

That is a good thing.

---

### 2. Fixing `from-admin-api-key` flag name is correct
This change is also correct:

```python
AdvancedFlagDef(
    key="from-admin-api-key",
    flag="from-admin-api-key",
    ...
)
```

Previously it was:

```python
flag="admin-api-key"
```

That was misleading because the CLI flag for `upload from-immich` is:

```bash
--from-admin-api-key
```

Even though this flag is currently secret-env-only and not emitted in `argv`, correcting the flag name is still right because:

- the UI checkbox label now makes sense
- the definition now matches the real CLI flag
- future allowlist/validation work will be cleaner

So this is a good fix.

---

### 3. Removing `manage-raw-jpeg` from `_raw_tab_state("upload-gp")` is correct
This is also correct.

For `upload-gp`, `manage-raw-jpeg` is now part of the advanced registry, not the simple/raw state.

So removing this:

```python
"manage-raw-jpeg": get_combo("manage-raw-jpeg", "NoStack"),
```

from `_raw_tab_state("upload-gp")` is the right move.

It prevents duplicate/conflicting state handling.

---

### 4. The diff script change is fine
Excluding generated/large documentation bundles from the diff output is reasonable:

```python
exclude_paths = [
    ":!command_binary_bugs_fix.txt",
    ":!command_binary_bugs.md",
    ":!phase2_review_changes.txt",
]
```

That is not a functional app change, just tooling cleanup.

---

# What is still not fully correct

## Critical remaining issue: advanced secret values can still be persisted in plaintext

This is the biggest problem still present.

The advanced row for `from-admin-api-key` is a secret field:

```python
AdvancedFlagDef(
    key="from-admin-api-key",
    flag="from-admin-api-key",
    label="Source admin API key",
    kind="text",
    secret_env="IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_ADMIN_API_KEY",
)
```

And the UI correctly makes it a password-style field.

But the persistence logic currently saves **all advanced row state**, including values.

In `collect_form_state()` you currently do something like:

```python
for tab_key, rows in getattr(self, "adv_rows", {}).items():
    tab_adv = {}
    for k, row in rows.items():
        tab_adv[k] = row.state()
```

And `row.state()` returns:

```python
{
    "enabled": ...,
    "value": ...,
}
```

That means if a user enters a source admin API key in the advanced row, it can be written into:

```toml
form_state.advanced.upload-immich.from-admin-api-key.value
```

in the profile config file.

That is not acceptable for a secret.

---

## Why this matters

You already correctly avoid putting normal API keys into `form_state`.

For simple fields, you exclude:

```python
secret_keys = {
    "api_key",
    "from-api-key",
    "admin_api_key",
    "from-admin-api-key",
    "target-server",
}
```

But that exclusion only applies to the old `self.inputs` fields.

It does **not** apply to advanced rows.

So the advanced secret field bypasses the secret-exclusion logic.

---

## Recommended fix

Do not persist secret values from advanced rows.

You have two good options.

---

### Option A — simplest and safest: persist only `enabled`, not secret value

When collecting advanced state, blank out values for secret rows.

Example:

```python
from core.advanced_flags import ADVANCED_FLAGS

ADVANCED_SECRET_KEYS = {
    tab: {def_.key for def_ in defs if def_.secret_env}
    for tab, defs in ADVANCED_FLAGS.items()
}
```

Then in `collect_form_state()`:

```python
adv_state = {}
for tab_key, rows in getattr(self, "adv_rows", {}).items():
    tab_adv = {}
    secret_keys = ADVANCED_SECRET_KEYS.get(tab_key, set())

    for k, row in rows.items():
        state = row.state()

        if k in secret_keys:
            # Do not persist secret values
            state = {
                "enabled": state.get("enabled", False),
                "value": "",
            }

        tab_adv[k] = state

    if tab_adv:
        adv_state[tab_key] = tab_adv
```

This means:

- the app remembers that the row was enabled
- but it does not remember the secret value
- after restart, the user must re-enter the secret

That is a reasonable security tradeoff.

---

### Option B — better UX but more work: store advanced secrets in `SecretStore`

If you want to persist advanced secrets securely, store them in the OS keyring via `SecretStore`, not in `config.toml`.

For example:

- key name: `advanced:upload-immich:from-admin-api-key`
- save using `SecretStore.set_secret(...)`
- load separately during `load_configuration()`

This is better UX, but more implementation work.

For now, I would use **Option A**.

---

# Other remaining concerns

## 1. Verify that no dead GP simple controls remain

This diff itself is clean, but it makes me re-check one thing:

For `upload-gp`, the simple/raw state is now only:

```python
{
    "path": ...,
    "manage-burst": ...,
    "manage-heic-jpeg": ...,
}
```

That is fine **if** the GP simple UI no longer contains controls for:

- `include-partner`
- `sync-albums`
- `include-archived`

If those checkboxes are still visible in Simple mode but are no longer collected anywhere, then they are dead controls.

That would be a false affordance.

So you should verify one of the following:

### Either:
- those GP checkboxes were removed from the simple card

### Or:
- they are still collected and emitted somehow

If they are visible but ignored, remove them.

This is not caused by this cleanup commit, but this commit makes the state boundary clearer, so it is worth checking now.

---

## 2. `TAB_ALLOWED_FLAGS` still does not include `from-admin-api-key`

This is not necessarily a bug right now, because:

- `from-admin-api-key` is secret-env-only
- `apply_advanced_flags_to_plan()` puts it into `plan.env`
- it does not go through the normal `flag_allowed_for_tab()` argv check

So functionally it can still work.

But there is a small contract cleanliness issue:

- the real CLI help includes `--from-admin-api-key`
- your compatibility fixture may include it
- your `TAB_ALLOWED_FLAGS["upload-immich"]` does not include it

That may show up as an “unknown upstream flag” in compatibility reporting.

You have two reasonable choices:

### Choice A — leave it out
Keep `TAB_ALLOWED_FLAGS` strictly for flags you emit in argv.

Since `from-admin-api-key` is env-only, leaving it out is defensible.

### Choice B — add it for compatibility cleanliness
Add it to:

```python
TAB_ALLOWED_FLAGS["upload-immich"]
```

even though you do not emit it in argv.

That would make help-fixture comparison cleaner.

I would probably choose **B** if your compatibility report is meant to compare against full CLI help output.

But this is not urgent.

---

## 3. No tests were added for these cleanup changes

This cleanup is small, but it is still worth adding a couple of regression tests.

At minimum, I would add:

### Test A — `ADVANCED_KEYS` is derived from `ADVANCED_FLAGS`
```python
def test_advanced_keys_derived_from_advanced_flags():
    from app import ImmichGoGUI
    from core.advanced_flags import ADVANCED_FLAGS

    expected = {
        tab: {def_.key for def_ in defs}
        for tab, defs in ADVANCED_FLAGS.items()
    }

    assert ImmichGoGUI.ADVANCED_KEYS == expected
```

---

### Test B — GP `into-album` is not an advanced key
```python
def test_upload_gp_does_not_include_into_album_advanced_key():
    from app import ImmichGoGUI

    assert "into-album" not in ImmichGoGUI.ADVANCED_KEYS.get("upload-gp", set())
```

---

### Test C — `from-admin-api-key` advanced secret goes to env, not argv
```python
def test_from_admin_api_key_advanced_secret_env(gui):
    gui.toggle_advanced(True)
    gui.stacked_widget.setCurrentIndex(1)
    gui.upload_tabs.setCurrentIndex(2)

    gui.inputs["config"]["server"].setText("http://new:2283")
    gui.inputs["config"]["api_key"].setText("new-key")
    gui.inputs["upload-immich"]["from-server"].setText("http://old:2283")
    gui.inputs["upload-immich"]["from-api-key"].setText("old-key")

    gui.adv_rows["upload-immich"]["from-admin-api-key"].set_state({
        "enabled": True,
        "value": "old-admin-secret",
    })

    plan = gui.build_plan(False)

    assert "--from-admin-api-key" not in " ".join(plan.argv)
    assert "old-admin-secret" not in " ".join(plan.argv)
    assert plan.env.get("IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_ADMIN_API_KEY") == "old-admin-secret"
```

---

### Test D — advanced secret value should not be persisted
This test will fail until you add the persistence fix:

```python
def test_advanced_secret_value_not_persisted(gui):
    gui.toggle_advanced(True)

    gui.adv_rows["upload-immich"]["from-admin-api-key"].set_state({
        "enabled": True,
        "value": "super-secret-admin-key",
    })

    state = gui.collect_form_state()

    saved = state["advanced"]["upload-immich"]["from-admin-api-key"]
    assert saved["enabled"] is True
    assert saved["value"] == ""
```

---

# Final assessment of this diff

## Is this cleanup correct?
### Yes, mostly.

The changes in this diff are good and safe:

- `ADVANCED_KEYS` is now derived from the real registry
- stale manual maintenance is removed
- `from-admin-api-key` flag name is corrected
- GP `manage-raw-jpeg` is correctly treated as advanced-only
- diff tooling cleanup is fine

---

## Is the advanced-flags feature fully closed now?
### Not yet.

The biggest remaining issue is:

> **Advanced secret fields can still be persisted in plaintext via `form_state`.**

That should be fixed before release.

---

# Recommended next patch

If you want the smallest correct follow-up, do this:

1. Add `ADVANCED_SECRET_KEYS`
2. In `collect_form_state()`, blank out secret advanced values
3. Add tests for:
   - derived `ADVANCED_KEYS`
   - `from-admin-api-key` env-only behavior
   - secret advanced value not persisted
4. Verify GP simple controls are not dead UI
5. Optionally add `from-admin-api-key` to `TAB_ALLOWED_FLAGS["upload-immich"]` for compatibility cleanliness

---

# Bottom line

This cleanup commit is a **good and correct incremental fix**.

But I would still keep the advanced-flags work marked as **not fully complete** until the advanced secret persistence issue is fixed.

If you want, I can give you the **exact follow-up patch** for the secret persistence fix only.