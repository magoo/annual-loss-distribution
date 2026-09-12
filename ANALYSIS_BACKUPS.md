# Analysis backups and recovery

The **Your analyses** controls manage independent annual-loss analyses in this
browser profile. **New**, **Rename**, and **Duplicate** organize analyses; **Delete**
asks for confirmation. Reopening selects the last-used analysis. Deleting the last
analysis starts a fresh **Analysis 1**.

## What is saved

Typing is saved immediately on each input event, before a timer, a Python worker
response, or a calculation. Press Enter or leave a numeric field to apply it.
Incomplete strings such as `-` and `1e` remain drafts. Inactive drafts are retained
without blocking valid active inputs. Invalid active estimates prevent calculation.

A saved analysis contains all three distributions' direct estimates, both expert
panels, the shared scenario list, their stable row IDs and allocation counters,
hidden parameters, active and remembered workflow modes, seed, and chart settings.
Changing methods or modes does not reset those values. Application defaults are
used only for a new analysis or a newly added row; loading does not rebuild saved
inputs from today's defaults.

Annual-loss results are held only in memory for the current analysis activation.
**Calculate / Recalculate annual loss** runs the model explicitly. Editing retains
the last calculated snapshot; opening, switching, duplicating, importing, or
recovering an analysis clears the annual-loss results. Previews remain bounded by
the existing model validation and workload checks. Recalculate to regenerate
results from saved inputs and the same seed in the same numerical runtime.

## Portable JSON files

**Download analysis** creates a `.analysis.json` file. **Back up all analyses**
creates `annual-loss-analyses.json`, including readable unsaved work from the current
session. **Import backup** accepts either format and creates new analyses; it never
overwrites existing analyses. Duplicate names receive numeric suffixes.

Individual documents use `format: "security-annual-loss-analysis"`, `version: 1`,
and `model_version: 1`. Library files use `format: "security-annual-loss-library"`,
`version: 1`, and an `analyses` array. Individual documents contain:

- `id`, `name`, `created_at`, and `updated_at` (UTC timestamps with milliseconds).
- `seed`, `view`, and `workflow`, including the remembered independent modes.
- `frequency` and `cost`, each containing its selected `distribution`, all `direct`
  parameter sets, and `panel` rows plus `next_id`.
- `scenarios`, containing ordered rows and `next_id`.
- `drafts`, mapping stable field paths to unfinished strings.

The browser seed is a non-negative integer through 9,007,199,254,740,991, ensuring
exact JSON/JavaScript round trips. An unfinished or out-of-range seed remains a
saved raw draft. The core Python simulation API retains its existing seed contract.

Exports have sorted object keys, two-space indentation, UTF-8 text, and a final
newline. Meaningful row ordering is preserved. Exporting does not update timestamps.
Results, simulation arrays, locks, and recovery checkpoints are excluded.

Imports validate the complete file before adding any analyses and reject files
above 10 MiB, unknown versions, extra or missing schema fields, duplicate or invalid
IDs, invalid modes, nonfinite numbers, and invalid field types. Structurally valid
unfinished drafts and invalid model ranges are accepted for correction. Imported
text is displayed as text and never executed. Budget files from
`security-org-planning` are a different format and cannot be imported.

A future format/model change must explicitly support the old version or provide a
tested migration that keeps the original until the migrated copy is saved. Unknown
versions and unreadable records remain available for original-file download.

## Browser journal and durable copy

localStorage keys use `security-org-planning-annual-loss:analyses:v1:` followed by
`analysis:<id>`, `checkpoint:<id>`, or `active`. The active pointer is a convenience,
not a library index: records are enumerated directly. Corrupt records do not hide
valid ones, and orphan checkpoints remain discoverable. These keys and the
`security-org-planning-annual-loss-analyses` IndexedDB database are isolated from
the budget app, even when both apps share a GitHub Pages origin.

Each edit writes a complete local recovery record immediately, then queues an
IndexedDB transaction with strict durability. The indicator shows **Saved** only
after the latest durable transaction completes. **Saving** means the latest edit
may still be lost in a crash. Failure in either store shows **Not saved** and keeps
current work downloadable and available across analysis switches in that session.
No records are evicted to make room. A newer durable record can restore a missing
or older readable local record. Corrupt and unsupported originals are preserved.

A checkpoint is captured before the first edit to a previously saved analysis in
a page session. Switching away and back does not replace it. **Recover previous
session** creates a separate analysis from that checkpoint. New analyses have no
previous-session checkpoint until they are reopened and edited in a later session.
Deleting an analysis removes its current record and checkpoint; durable tombstones
are committed first so a crash cannot resurrect the deletion.

An exclusive Web Lock permits one tab to edit an analysis. A second tab can view
it, duplicate it, or choose **Retry saving / Edit here** after ownership becomes
available. Switching waits for queued durable writes before releasing the lock.
Startup recovery also respects live writers' locks. Conflicting unsaved edits are
preserved as a separate copy rather than overwriting another tab's changes.

## Recovery limits and privacy

Browser storage belongs to an origin and browser profile. Local Marimo and Pages
origins have separate libraries, as do different ports, devices, and profiles. Use
JSON backups to move analyses between them. Storage is not encrypted by this app
or synchronized to a backend. Clearing site data, private-browsing cleanup, browser
storage policies, or profile/device/disk loss can remove it. Runtime resources must
still be available to open the application; this is not an offline installation.

If storage or cross-tab coordination is unavailable, work stays in an explicitly
unsaved session. Download it before closing. **Retry saving / Edit here** retries
storage and ownership. Whole-library exports contain readable analyses; use
**Download original** separately for unreadable records.

Backups can contain sensitive company estimates, expert names, and unfinished
notes. Keep them in private storage outside the source repository, or in its ignored
`analysis-backups/` or `private/` directory. Standard backup filenames are ignored;
arbitrary user-chosen filenames elsewhere are not automatically protected. The app
does not connect to Git or upload backups.
