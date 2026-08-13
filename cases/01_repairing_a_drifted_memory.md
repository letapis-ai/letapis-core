# Case 01 — Repairing a memory that had drifted

A working corpus of **5 504 episodes**, months old, several people and several agents writing
into it. It answered questions and looked healthy.

## The audit said 2 orphans. There were 753 records to mend.

An episode records where it came from, and that address had come to live in two fields — an older
one and a newer one. The scan read only the newer. Everything written before that field existed
was not misjudged: it was **not looked at**.

A report can be honest about what it examined and silent about what it skipped. Silence reads as
absence. Read the `coverage` line before the counts — [what each flag is worth][flags].

## What was there

| | |
|---|---|
| pointer to a file that had moved | 159 |
| record with no file of its own | 19 |
| record with no date | 568 |
| forgetting that never reached the file | 5 |
| **file recorded, nowhere on disk** | **2** |
| empty record | 46 |

Those 2 are the only ones with **no automatic cure**: the document is gone, and writing a fresh
file from the record's content would produce something plausible that is not it.

Widen the scan without telling these apart, and the report jumps from 2 to 159 — with 157 of them
having their files intact one directory over.

## The repair

```bash
letapis doctor --dry-run    # writes nothing
letapis doctor --apply
```

Run from anywhere once the config sits in its fixed place — [where the doctor looks for it][cfg].

**753 records in one pass.**

| | before | after |
|---|---|---|
| pointer to a moved file | 159 | **0** |
| record with no file | 19 | **5** |
| record with no date | 568 | **0** |
| forgetting not in the file | 5 | **0** |
| empty record | 46 | 46 — *named only* |
| marked because its file left | 4 | 4 — *counted only* |

Dates came from each record's own file. Pointers were repointed — no content copied, no record
forked. Forgettings were written into the files, so a rebuild keeps them forgotten.

## What it left alone

- **46 empty records** — whether an empty record is worth keeping is a judgement about your work.
- **5 with no file** — writing one is not obviously right, so the command stops rather than guesses.
- **4 marked by the watcher** — the mark is correct until the file returns, and then it lifts itself.

A repair tool that skips things is working. What it skips is where a person is cheaper than a
mistake.

## Take-aways

- **Run the dry run.** Writes nothing, costs seconds.
- **Read `coverage` before the counts.** A number is as wide as the examination behind it.
- **Distinguish before repairing.** Three states of a missing file need three different answers.
- **Do it on a quiet afternoon.** The same work mid-restore, with 568 undated records, is a very
  different day.

## Where this is documented

- [Keeping episodic memory healthy][hygiene] — running the scan, what each flag is worth, and
  [`letapis doctor`][doctor]: what it mends, what it only names, [where it reads its config][cfg].
- [Episodic memory][memory] — how an episode gets its date, and how a document withdraws the
  record it produced.

[hygiene]: ../skills/letapis/references/hygiene.md
[flags]: ../skills/letapis/references/hygiene.md#what-each-flag-is-worth
[doctor]: ../skills/letapis/references/hygiene.md#mending-what-the-scan-found-letapis-doctor
[cfg]: ../skills/letapis/references/hygiene.md#where-it-looks-for-the-config
[memory]: ../skills/letapis/references/memory.md
