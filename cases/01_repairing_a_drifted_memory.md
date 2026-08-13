# Case 01 — Repairing a memory that had drifted

A working corpus of 5 504 episodes, months old, several people and several agents writing into
it. It answered questions and looked healthy.

## The audit said 2 orphans. There were 753 records to mend.

An episode records where it came from, and that address had come to live in two fields: an older
one and a newer one. The scan read only the newer. Everything written before that field existed
was not misjudged, it was never looked at.

A report can be honest about what it examined and quiet about what it skipped, and quiet reads as
nothing there. Read the `coverage` line before the counts, and [what each flag is worth][flags].

## What was there

| | |
|---|---|
| pointer to a file that had moved | 159 |
| record with no file of its own | 19 |
| record with no date | 568 |
| forgetting that never reached the file | 5 |
| file recorded, nowhere on disk | 2 |
| empty record | 46 |

Those 2 are the only ones with no automatic cure. The document is gone, and writing a fresh file
out of what the record holds would produce something plausible that is not it.

Widen the scan without telling these apart and the report jumps from 2 to 159, while 157 of those
files sit intact one directory over.

## The repair

```bash
letapis doctor --dry-run    # writes nothing
letapis doctor --apply
```

It runs from anywhere once the config sits in its fixed place. See
[where the doctor looks for it][cfg].

753 records in one pass:

| | before | after |
|---|---|---|
| pointer to a moved file | 159 | 0 |
| record with no file | 19 | 5 |
| record with no date | 568 | 0 |
| forgetting not in the file | 5 | 0 |
| empty record | 46 | 46, named only |
| marked because its file left | 4 | 4, counted only |

Dates came from each record's own file. Pointers were repointed, with no content copied and no
record forked. Forgettings were written into the files, so a rebuild keeps them forgotten.

## What it left alone

Whether an empty record is worth keeping is a judgement about your own work, so the 46 were named
and left. Five records still have no file, because writing one there is not obviously right and
the command stops instead of guessing. Four are marked because their file left the disk; that
mark is correct until the file comes back, and then it lifts itself.

Skipping is part of the job. What gets skipped is where a person is cheaper than a mistake.

## Take-aways

Run the dry run first. It writes nothing and costs seconds.

Read `coverage` before you read the counts. A number is only as wide as the examination behind it.

Tell the states apart before repairing anything. Three different reasons a file can be missing
need three different answers, and merged into one flag they bury the two records that need you.

Do this on a quiet afternoon. The same work in the middle of a restore, with 568 undated records,
is a different day entirely.

## Where this is documented

- [Keeping episodic memory healthy][hygiene]: running the scan, what each flag is worth, and
  [`letapis doctor`][doctor] with what it mends, what it only names, and
  [where it reads its config][cfg].
- [Episodic memory][memory]: how an episode gets its date, and how a document withdraws the
  record it produced.

[hygiene]: ../skills/letapis/references/hygiene.md
[flags]: ../skills/letapis/references/hygiene.md#what-each-flag-is-worth
[doctor]: ../skills/letapis/references/hygiene.md#mending-what-the-scan-found-letapis-doctor
[cfg]: ../skills/letapis/references/hygiene.md#where-it-looks-for-the-config
[memory]: ../skills/letapis/references/memory.md
