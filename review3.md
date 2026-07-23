Yes — I went through `review2.md` against the current `app.py`, `core/*` bundle, CLI documentation, and tests.

My honest assessment is:

> **Phase 1 is largely in place.**
> **Phase 2 is mostly in place, but not fully complete.**
> There are still enough contract-level gaps that I would **not** mark Phase 2 as “done” without a short closure pass.

The project is in much better shape than before. The architecture is sound, secret handling is strong, and the GUI now generates far more correct commands than earlier. But the remaining problems are exactly the dangerous kind for a CLI wrapper:

- a few UI controls still do not map cleanly to the CLI contract
- some path handling is still inconsistent
- schema/allowlist enforcement is not fully closed-loop
- tests still contain duplicate names and some weak assumptions
- process tracking is better, but not equally robust on all platforms

Below is the critic-style review and a new plan that stays relevant to the current scope.

---

# 1. Phase 1 review: “Correctness first”

## Phase 1 intent from `review2.md`
Phase 1 was supposed to fix:

1. archive flag `--write-to` vs `--write-to-folder`
2. `archive from-immich` source-server/auth model
3. surface `plan.errors`
4. wire or remove non-functional Google Photos controls
5. fix stack flag allowlist/builder mismatches
6. fix `running_process` boolean bug
7. make stale-lock detection real

---

## 1.1 Archive destination flag — **Done**
### Evidence
Current code now uses:

- `TAB_ALLOWED_FLAGS` for archive tabs includes `write-to-folder`
- `command_builder.py` emits `--write-to-folder=...`
- tests expect `--write-to-folder=...`

### Verdict
This critical issue is resolved.

---

## 1.2 `archive from-immich` source model — **Mostly done**
### Evidence
Current code now:

- uses `--from-server=...` for `archive-immich`
- uses `IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_*` environment variables
- no longer emits a normal `--server` for archive-from-immich
- UI now describes the server as a **source** rather than a target in the archive tab

### Verdict
This is now directionally correct and much safer than before.

### Remaining caveat
The contract is still not fully proven end-to-end inside the repo unless the fixtures/live binary tests are run. The code looks right, but I would still want an integration-level check that the exact env var names are accepted by the real binary.

---

## 1.3 Surface `plan.errors` — **Partially done**
### Evidence
`app.py` now checks `plan.errors`:

- in `show_confirm_dialog()`
- in `run_command()`

That is a real improvement.

### What is still missing
`update_status()` still does **not** consider `plan.errors`.

That means the UI can show:

- “Server: Ready”
- Run enabled

and only after clicking Run does the user see:

- “Command Build Errors”

That is much better than silent failure, but it is still not good enough for a polished wrapper.

### Verdict
**Partial.**
Errors are no longer completely silent, but they are still not surfaced early enough.

---

## 1.4 Google Photos controls — **Mostly done, but one visible mismatch remains**
### Evidence
The GP tab now exposes many controls, and the builder now emits many of them:

- `include-type`
- `include-unmatched`
- `include-partner`
- `include-archived`
- `include-trashed`
- `sync-albums`
- `from-album-name`
- `partner-shared-album`
- `takeout-tag`
- `people-tag`

This is a major improvement.

### Remaining problem
The GP UI still has:

- `Put all into Album` → stored as `into-album`

But `TAB_ALLOWED_FLAGS["upload-gp"]` does **not** include `into-album`.

That means:

- if the user leaves it blank, nothing happens
- if the user fills it in, the builder creates a `plan.errors` entry

So this control is still not properly reconciled with the CLI contract.

### Verdict
**Mostly done, but not fully closed.**
This is exactly the kind of false affordance Phase 1 was supposed to eliminate.

---

## 1.5 Stack flag allowlist/builder mismatches — **Mostly done**
### Evidence
Stack now supports:

- `api-trace`
- `time-zone`
- `manage-epson-fastfoto`

and the builder emits them.

### Remaining concern
The CLI guide you provided does **not** clearly document `date-range` for `stack`.

Yet current code allows and emits:

- `--date-range` for stack

This may be valid in the real binary, but based on the supplied CLI doc alone, it is not clearly supported.

### Verdict
**Mostly done, but needs contract verification.**
If the live binary supports it, keep it. If not, remove it.

---

## 1.6 `running_process` boolean bug — **Done**
### Evidence
Current logic is now sane:

```python
is_running = (
    active_lock is not None and is_lock_active(active_lock)
) or (getattr(self, "running_process", False) is True)
```

This is much better than the old `is not None` bug.

### Verdict
Resolved.

---

## 1.7 Stale-lock detection — **Substantially done, but not equally strong everywhere**
### Evidence
`process_tracker.py` now has:

- PID checking
- terminal PID checking
- heartbeat file checking
- grace-period logic
- cross-platform process liveness checks

`terminal_launcher.py` also writes PID/heartbeat on POSIX.

### Verdict
This is now real, not theoretical.

### Remaining weakness
Windows is still weaker than POSIX:

- the Windows `.bat` flow deletes the lock on exit
- but it does not have the same heartbeat discipline as POSIX
- if the terminal/process tree behaves oddly, lock state can still become ambiguous

So this is **good enough for now**, but not bulletproof.

---

# 2. Phase 2 review: “CLI contract hardening”

## Phase 2 intent from `review2.md`
Phase 2 was supposed to:

1. rebuild `TAB_ALLOWED_FLAGS` from captured CLI help
2. add missing flags where appropriate:
   - concurrent tasks
   - stack time-zone / epson / api-trace
   - GP album/partner/trash/archived/sync controls
3. verify env-var secret contract or replace it with temporary config generation
4. normalize all paths to absolute before execution

---

## 2.1 Rebuild allowlists from captured CLI help — **Partially done**
### What exists now
You now have:

- `cli_help.py`
- `cli_contract.py`
- fixture loading
- compatibility checking
- tests comparing allowed flags to fixtures

This is a very good direction.

### What is still not true
`TAB_ALLOWED_FLAGS` is still a **hand-maintained registry**.

It is now checked against fixtures, but it is not automatically generated from them.

That means the system can detect drift, but it does not prevent the allowlist from being authored incorrectly in the first place.

### Verdict
**Partial.**
You have contract checking.
You do not yet have contract-driven generation.

---

## 2.2 Add missing flags where appropriate — **Mostly done**
### Evidence
The schema and builder now include many previously missing flags:

- `concurrent-tasks`
- stack `time-zone`
- stack `manage-epson-fastfoto`
- stack `api-trace`
- GP album/partner/trash/archived/sync controls

This is a major improvement.

### Remaining issues
There are still a few mismatches or uncertain areas:

#### A. GP `into-album`
Still exposed in UI, but not allowed by schema.

#### B. Stack `date-range`
Allowed in code, but not clearly documented in the supplied CLI guide.

#### C. `from-date-range` normalization
For `upload-immich` and `archive-immich`, `from-date-range` is emitted raw, without the same cleaning used for normal `date-range`.

That means spaces may survive:

- `2023-01-01, 2023-12-31`

Other date-range fields are cleaned; this one is not.

### Verdict
**Mostly done, but not fully rigorous.**

---

## 2.3 Verify env-var secret contract or replace with temp config — **Mostly done in design, not fully proven**
### What is good
The current approach is now much more defensible because:

- the CLI documentation says every flag has an equivalent `IMMICH_GO_*` env var
- the app uses `IMMICH_GO_*` variables consistently
- POSIX terminal launching now forwards all `IMMICH_GO_*` variables, not just a hardcoded subset

That closes one of the earlier serious risks.

### What is still missing
There is still no strong **end-to-end proof** in the codebase that:

- the real binary accepts every env var name you generate
- especially for `archive-immich` source credentials
- especially for admin keys

The current tests prove that your Python code puts the right values into `plan.env`.
They do not prove that `immich-go` itself honors those exact variables.

### Verdict
**Mostly acceptable now, but still needs verification against the real binary or a stub contract test.**

---

## 2.4 Normalize all paths to absolute before execution — **Not fully done**
This is the biggest remaining Phase 2 gap.

### What is done
Source paths are generally processed through `collect_paths()`, which:

- expands user home
- absolutizes paths
- expands globs

That is good.

### What is not done
#### A. Destination paths are not absolutized
`write-to-folder` is emitted as typed.

If the user enters a relative destination, the external terminal may run from a different working directory, especially because your launcher intentionally isolates execution.

That is a latent bug.

#### B. Glob behavior is inconsistent
Validation uses `expand_source_paths()` with recursive globbing.
Command building uses `collect_paths()` with non-recursive globbing.

That means validation and execution can disagree.

### Verdict
**Partial.**
This is one of the clearest unfinished parts of Phase 2.

---

# 3. Overall scorecard

## Phase 1
| Item | Status |
|---|---|
| Archive destination flag | Done |
| Archive-from-immich source model | Mostly done |
| Surface `plan.errors` | Partial |
| GP controls wired | Mostly done |
| Stack flag mismatches | Mostly done |
| `running_process` boolean bug | Done |
| Stale-lock detection | Mostly done |

## Phase 2
| Item | Status |
|---|---|
| Help-fixture contract checking | Partial |
| Missing flags added | Mostly done |
| Env-var secret contract | Mostly done, not fully proven |
| Absolute path normalization | Partial |

---

# 4. Critic summary: what is still not good enough

If I’m still being a critic, these are the real remaining problems.

---

## Critical remaining issue 1: The UI can still present controls that are not contract-safe
The biggest example is:

- GP tab: `Put all into Album` → `into-album`

This control is visible, but the schema rejects it.

That means the GUI still has at least one control that can create a command-build error instead of either:

- working correctly, or
- being removed/disabled

That violates the “no false affordances” principle.

---

## Critical remaining issue 2: `plan.errors` are still not visible early enough
You now block execution with `plan.errors`, which is good.

But the status area can still say the form is ready.

That creates this UX:

1. user fills form
2. UI says ready
3. user clicks Run
4. only then sees a schema error

That is acceptable as a safety net.
It is not acceptable as the primary error surface.

---

## Critical remaining issue 3: Path handling is still not fully deterministic
For a GUI wrapper, this matters a lot.

Right now:

- source paths are largely normalized
- destination paths are not
- validation and command building use different glob behavior

That means the app can still behave differently depending on:

- current working directory
- whether the path is relative
- whether the pattern is globbed recursively or not

For a tool that launches commands in an external terminal, this is a real correctness risk.

---

## Critical remaining issue 4: The CLI contract is checked, but not fully authoritative
The fixture/compatibility system is good.

But:

- `TAB_ALLOWED_FLAGS` is still manually maintained
- the fixtures are not visible in the provided bundle
- duplicate tests still exist
- some flags remain uncertain (`stack --date-range`, GP `into-album`)

So the system is much better than before, but it is not yet a single source of truth.

---

## Critical remaining issue 5: Tests are better, but still not fully trustworthy
The test suite is now much more meaningful.

However, `test_app.py` still contains duplicated test function names, for example:

- `test_golden_upload_folder`
- `test_golden_upload_gp`
- `test_golden_stack`
- `test_golden_archive_folder`
- `test_golden_archive_immich`
- `test_golden_upload_immich`

In Python, later definitions silently override earlier ones.

That means some tests you think exist may not actually run.

This is a real quality problem.

---

# 5. What I would conclude about “Phase 2 complete?”

## My verdict
**Phase 1: effectively complete enough to move on.**
**Phase 2: not fully complete.**

I would describe Phase 2 as:

> **80% done, but the last 20% is exactly the part that prevents silent wrong behavior.**

So the right next step is not a big new feature phase.

It is a short **Phase 2 closure / contract hardening** pass, followed by the real Phase 3 safety work.

---

# 6. Recommended new plan

I would not jump straight into broad Phase 3 work without first closing the remaining Phase 2 holes.

So the best plan is:

- **Phase 2.5: Contract Closure**
- **Phase 3: Runtime Safety & Release Hardening**

That keeps the plan relevant to the current scope and avoids feature bloat.

---

# Phase 2.5 — Contract Closure

## Goal
Make sure that:

1. every visible UI control either works or is removed
2. every emitted flag is allowed and fixture-verified
3. every filesystem path emitted by the GUI is deterministic
4. command-build errors are visible before Run is clicked
5. tests are unique, trustworthy, and aligned with the real CLI

This should be a small, high-priority milestone.

---

## Task 2.5.1 — Audit every UI field against schema and builder
### What to do
Create a one-time audit that compares:

- `self.inputs[tab][key]`
- `_collect_tab_state()`
- `TAB_ALLOWED_FLAGS[tab]`
- actual emission in `build_plan_from_state()`

### Known immediate fixes
- GP `into-album`
  - if CLI supports it: add to allowlist and tests
  - if CLI does not support it: remove from GP UI and state
- Stack `date-range`
  - verify against live binary/help fixture
  - keep only if truly supported

### Acceptance criteria
- no exposed field can produce a hidden or surprising `plan.errors`
- every non-empty control either:
  - changes the generated command, or
  - is explicitly informational only

---

## Task 2.5.2 — Make path handling deterministic
### What to do
Introduce one shared path normalization policy.

### Minimum required changes
#### A. Absolutize destination paths
For:

- `archive-folder` → `write-to-folder`

Do:

- expand user
- convert to absolute path
- preserve the value as a directory path

#### B. Unify source expansion
Use the same logic for:

- validation
- command building

Right now:

- validation uses recursive glob expansion
- builder uses non-recursive glob expansion

Pick one contract and apply it everywhere.

### Recommended contract
- expand `~`
- convert relative paths to absolute
- expand globs consistently
- warn if a non-glob path does not exist
- warn if a glob matches nothing

### Acceptance criteria
- relative source paths become absolute in `plan.argv`
- relative destination paths become absolute in `plan.argv`
- validation warnings and actual command construction agree

---

## Task 2.5.3 — Surface `plan.errors` in status, not only in dialogs
### What to do
Add a lightweight plan-error check to the UI state.

You do not need to rebuild the full plan on every keystroke if that is too expensive.

Instead:

- debounce plan construction for text fields
- or run plan-error checks on focus-out / editing finished
- or maintain a cached plan and refresh it on relevant changes

### Minimum UX requirement
If `plan.errors` exists:

- status card should show an error state
- Run and Dry Run should be disabled
- the first error should be visible without opening a dialog

### Acceptance criteria
- filling GP `into-album` (if still unsupported) immediately disables Run
- status shows the reason
- no user has to click Run to discover a schema violation

---

## Task 2.5.4 — Make fixtures the contract authority
### What to do
Strengthen the fixture system so it is not optional.

### Minimum requirements
- fixtures must exist for the tested version
- missing fixtures must fail tests loudly
- compatibility report must distinguish:
  - fixture compatibility
  - live binary compatibility
  - missing fixture data

### Stronger improvement
Generate or export the allowed-flag registry from fixtures instead of maintaining it entirely by hand.

For example:

- capture help fixtures
- parse flags
- write `cli_flags.json`
- load `TAB_ALLOWED_FLAGS` from that generated artifact

That would make the CLI help the real source of truth.

### Acceptance criteria
- deleting a fixture causes a visible failure
- adding a new upstream flag shows up as “unknown flag” in compatibility checking
- manual schema drift is much harder to introduce accidentally

---

## Task 2.5.5 — Verify the env-var secret contract
### What to do
Do not rely only on Python-side assertions.

Add one of the following:

#### Option A: stub binary contract test
Create a fake `immich-go` executable/script that prints:

- received environment variables
- received argv

Then test that:

- required `IMMICH_GO_*` variables are present
- secrets are not present in argv

#### Option B: live binary smoke test
Run real `--help` / dry-run style checks against a known version and verify that the environment variable names are accepted.

### Priority variables to verify
- `IMMICH_GO_UPLOAD_API_KEY`
- `IMMICH_GO_UPLOAD_FROM_IMMICH_FROM_API_KEY`
- `IMMICH_GO_ARCHIVE_FROM_IMMICH_FROM_API_KEY`
- admin key equivalents

### Acceptance criteria
- the secret strategy is proven by more than just internal Python tests
- archive-immich and upload-immich credential passing is verified

---

## Task 2.5.6 — Fix test hygiene
### What to do
Rename duplicated test functions and add a lint/check for duplicate test names.

### Immediate duplicates to fix
- `test_golden_upload_folder`
- `test_golden_upload_gp`
- `test_golden_upload_immich`
- `test_golden_archive_folder`
- `test_golden_archive_immich`
- `test_golden_stack`

### Add missing tests
For every visible widget:

- changing it changes the generated command, or
- it is intentionally informational only

Especially add tests for:

- GP archived/partner/sync/trashed/unmatched toggles
- GP media type
- GP album filters
- stack time-zone
- stack epson
- archive destination absolutization
- relative source path absolutization

### Acceptance criteria
- no duplicate test names
- every exposed functional control has a test proving its effect

---

# Phase 3 — Runtime Safety & Release Hardening

Once Phase 2.5 is closed, Phase 3 becomes the right next milestone.

This phase is not about new source types or new pages.
It is about making the existing app safe, predictable, and release-worthy.

---

## Task 3.1 — Centralize binary update flow
### Current problem
`BinaryManager` already contains a lot of update logic, but `app.py` still has a parallel update/extraction flow.

That duplication is risky.

### What to do
Move the full update workflow into one controller/backend service:

- version comparison
- asset discovery
- download
- extraction
- verification
- selection
- rollback / no-change-on-failure

### Minimum safety requirements
- no downgrade prompting
- no corrupted install on cancellation
- no replacement unless extracted binary verifies
- explicit success/failure result object
- temp-file based replacement
- version output verification after extraction

### Nice-to-have but strongly recommended
- checksum verification if upstream publishes checksums
- release notes display improvements
- clearer “already up to date” handling

### Acceptance criteria
- canceling a download does not damage the current binary
- failed extraction does not replace the current binary
- update result is unambiguous to the caller

---

## Task 3.2 — Make secret migration/copy/rename loss-proof
### Current problem
Some secret operations still rely too much on “try, then proceed”.

### What to do
For:

- QSettings migration
- profile rename
- profile duplication
- secret provider fallback

Require:

- write
- read-back verification
- only then delete old secret

### Acceptance criteria
- simulated keyring failure cannot cause secret loss
- rename/duplicate either fully succeeds or leaves old secrets intact
- failures are surfaced to the user

---

## Task 3.3 — Harden run lifecycle and lock recovery
### Current problem
Lock tracking is much better, but Windows is still weaker than POSIX.

### What to do
Improve cross-platform consistency.

### Minimum improvements
- Windows wrapper should have a more explicit cleanup/heartbeat strategy
- stale locks should be recoverable without manual file deletion
- “Reset Run State” should always restore a sane UI
- running state should be visible even if the user switches tabs

### Stronger improvement
Add a global running indicator outside the footer, for example:

- status card row
- header badge
- always-visible warning strip

### Acceptance criteria
- killing the terminal does not permanently lock the GUI
- stale locks are cleaned or resettable
- running state is visible from every relevant page

---

## Task 3.4 — Debounce expensive validation
### Current problem
Some validation can become expensive while typing, especially path/glob fields and manual binary path.

### What to do
Debounce:

- source path fields
- destination path fields
- manual binary path
- other heavy validators

Run expensive checks:

- after editing finished, or
- after a short timer

### Acceptance criteria
- typing a long path does not cause UI lag
- glob expansion does not run on every keystroke
- manual binary path does not trigger excessive subprocess calls

---

## Task 3.5 — Improve warning UX
### Current problem
Many important warnings only appear in the confirmation dialog.

That is better than nothing, but still late.

### What to do
Add inline warnings near the relevant fields for:

- skip SSL
- overwrite
- destructive RAW/JPEG modes
- destructive burst modes
- destination inside source path
- untested binary version

### Acceptance criteria
- users see dangerous choices before they click Run
- warnings are visible in the form itself, not only in a popup

---

## Task 3.6 — Make compatibility reporting fully trustworthy
### Current problem
The compatibility dialog is much better now, but it still needs to be impossible to misread.

### What to do
Make the dialog explicitly show:

- fixture compatibility
- live binary compatibility
- missing fixtures
- unknown upstream flags
- tested version vs detected binary version

### Acceptance criteria
- missing fixtures cannot be interpreted as “compatible”
- live binary drift is clearly separated from fixture drift
- user can understand exactly what is verified and what is not

---

# 7. Suggested milestone order

If I were planning this as the next concrete roadmap, I would do this:

## Milestone A — Phase 2.5 Closure
1. Remove/fix GP `into-album`
2. Verify stack `date-range`
3. Absolutize all emitted paths
4. Unify glob expansion behavior
5. Surface `plan.errors` in status
6. Fix duplicate tests
7. Add widget-to-command tests
8. Strengthen fixture enforcement

## Milestone B — Phase 3 Safety
1. Centralize binary update flow
2. Make secret operations loss-proof
3. Harden Windows lock lifecycle
4. Debounce validation
5. Add inline warnings
6. Polish compatibility reporting

---

# 8. Definition of Done for the next milestone

I would not call the next milestone complete unless all of these are true:

## Command correctness
- No visible control can silently fail to affect the command
- No emitted flag is outside the allowlist
- No emitted filesystem path is relative
- No schema violation is discovered only after clicking Run

## CLI contract
- Fixtures exist and are mandatory
- Missing fixtures fail loudly
- Unknown upstream flags are reported
- Env-var secret passing is verified beyond Python-side assertions

## Tests
- No duplicate test names
- Every exposed functional control has a test
- Golden tests reflect the real CLI contract, not current assumptions

## Runtime safety
- Stale locks can be detected and recovered
- Binary updates cannot corrupt the existing install
- Secret migration/rename cannot lose data

---

# 9. Bottom line

## Are we done through Phase 2?
### Short answer:
**Not quite.**

### More precise answer:
- **Phase 1:** yes, effectively done
- **Phase 2:** mostly done, but with a few real contract gaps

The most important remaining Phase 2 issues are:

1. GP `into-album` mismatch
2. `plan.errors` not surfaced early enough
3. destination paths not absolutized
4. glob/validation inconsistency
5. fixture/contract system not yet fully authoritative
6. duplicate tests still present

Once those are closed, Phase 3 becomes the right next step.

---

If you want, I can turn this into either:

1. a **GitHub issue list** with titles, labels, and acceptance criteria, or  
2. a **patch plan** with exact file-by-file changes for Phase 2.5 only