# Keeping episodic memory healthy

Memory accumulates and nobody sweeps it. Every document you save with the right frontmatter, in a
folder marked as a source of episodes, becomes one — and so does everything you record
deliberately. Over months that grows into a corpus with orphans, empty stubs and claims that were
true once. This page is about auditing that corpus: what the scan looks at, and what each of its
verdicts is actually worth.

**The scan only ever reads.** It proposes; deleting and correcting stay separate, deliberate
steps that someone takes on purpose.

## When to run it

- Someone asks in so many words: "check the memory", "what has piled up", "audit the episodes".
- The corpus has grown past a couple of thousand episodes. There is no magic number — the point
  is that hand-knowledge of what is in there stops being reliable somewhere around that size.
- Right after a large batch of file renames or a folder reorganisation **that the engine did not
  watch happen** — one done while it was stopped, or outside the watched tree. Episodes remember
  where they came from; a move seen live is reconciled by itself, and one made behind the engine's
  back leaves the old address behind.

## How to run it

```python
mcp__<engine>__ena_hygiene_scan()                          # the standard pass
mcp__<engine>__ena_hygiene_scan(with_graph=True)           # also flags episodes with no causal links; slower
mcp__<engine>__ena_hygiene_scan(stale_factor=2, cap=100)   # widen or narrow what counts
```

`<engine>` is the server name from your own configuration — see [SKILL.md](../SKILL.md)
§ Addressing an engine. **Run this against the engine that holds your episodes**, which with
several registered is a choice, not a formality.

The engine runs the scan against its own store and hands back the report, so this works the same
whether it sits on this machine or elsewhere. Nothing is needed locally.

The report has two halves: a `summary` — how many episodes were scanned, the count per flag, and
coverage — and `candidates`, the shortlist per flag.

## Which corpus you are auditing

**Any engine with a marked folder of markdown accumulates episodes**, including one you set up
purely for someone else's documentation — mark a folder there and it grows a memory made of
*their* frontmatter. Why that happens and what it costs is in [memory](memory.md); what it means
here is that the audit is two jobs.

On the engine holding your work the flags below mean what they say. On a reference-only engine
expect most of what surfaces to be generated noise, and the remedy is the folder flag — clearing
`episodes` stops the source, which beats `episode: false` file by file in documents you do not
control.

`summary.scanned` tells you which of the two you are looking at.


## What each flag is worth

The scan sorts candidates; it does not judge them. The right action differs per flag, and several
are routinely misread as "delete this".

Three of the flags are about the file an episode came from, and they are kept apart because they
need opposite things done to them:

| Flag | What it means | What it is usually worth |
|---|---|---|
| `stale_pointer` | the file is alive, the episode points at where it used to be | the pointer is repairable, and the row says how. Never a forget: the content is intact |
| `no_carrier` | the episode has no file recorded at all | repairable too — a file can be written from the episode's own content |
| `orphan` | a file is recorded and it is nowhere on disk | **no automatic cure.** A person decides: give the record a file of its own, or forget it if the document was removed deliberately. Repairing does not bring the lost document back |
| `low_signal` | the body is empty or nearly so | a forget, when it is genuinely scaffolding or a stray note |
| `stale` | older than `stale_factor` × its kind's half-life — the multiplier is a parameter of the scan, not a constant | **not** a forget. Old is not wrong; a durable decision stays true for years. Read it and ask whether it still holds |
| `no_provenance` | the episode does not say where it came from | a labelling gap. Worth backfilling, never worth deleting over |
| `isolated` | no causal links to anything else | informational, rarely actionable |

**Rows about the carrier bring their own remedy with them**, so for those three the table above
is a summary rather than something to memorise:

```
id             episode-…
source_file    /vault/…/decision.md
address_field  source_path           # which field the address came from
resolves_to    /vault/…/decision.md  # for a moved file, where it actually is
repair         {automatic: …, how: "…"}
```

`repair.automatic` is the one to read first: `true` means the engine can mend it and `how` names
the move, `false` means the decision is yours.

The other flags — `low_signal`, `stale`, `no_provenance`, `isolated` — carry no `repair` field,
because what to do about them is a judgement rather than a move: read the episode and decide.

**Two things the scan cannot do at all,** and it is honest about not doing them: it does not spot
contradictions, and it does not spot near-duplicates. Both need someone to read the shortlist and
notice "these two say opposite things" or "this same fact is here three times". That is the part
where the audit earns its keep, and it is not automated.

## Rules that exist because they were paid for

**Propose, then act one at a time.** The forget call takes a single target and acts immediately.
Batch-forgetting by pattern has clobbered unrelated episodes in practice — a query that looks
precise pulls in a valuable neighbour ranked slightly higher. Surface the list, get an explicit
go, act singly.

**Report what was *not* scanned.** Contradictions and duplicates are outside the scan; a report
that stays quiet about them reads as full coverage and is not.

## Acting on the result

These are downstream of the audit, and none of them are part of it:

- `mcp__<engine>__ena_forget_fact(query, reason)` — soft-delete one fact. It stays in the audit trail.
- `mcp__<engine>__ena_correct_fact(old_query, new_text, reason)` — supersede a fact that has
  changed, keeping the link between the old claim and the new one.
- `mcp__<engine>__forget_folder` — soft-delete everything under a folder, for the case where a
  whole retired directory has left a cluster of orphans behind.

Their detail lives in [memory](memory.md).

## Mending what the scan found: `letapis doctor`

The scan reads. Mending is a separate command of the engine itself, run from a terminal:

```bash
letapis doctor --dry-run      # report only, writes nothing
letapis doctor --apply        # mend what has a mend
```

**It is a command rather than a tool an agent can call, and that is deliberate.** Repairing a
memory is a rare, deliberate act with a person behind it, not something to reach for between two
other things.

### What it mends, and what it only names

| | |
|---|---|
| a record with no date | the date is taken from its own file |
| a pointer to a file that moved | the pointer is repointed; no content is copied |
| a record with no file at all | a file is written from the record's own content |
| a forgetting that never reached the file | it is written there, so a rebuild keeps it |
| an empty record | **named only.** Whether a record with nothing in it is worth keeping is your call |
| a record marked because its file left the disk | **counted only.** The mark is correct until the file returns, and it lifts itself when it does |

The dry run prints the same table with counts and ends with how many records `--apply` would
mend. Run it first; there is no reason not to.

### Where it looks for the config

Three places, in this order, and the first that answers wins:

1. `LETAPIS_CONFIG_FILE`, if set — **authoritative**: named but missing is a refusal, not a
   reason to look further;
2. `./config.yaml` in the working directory;
3. `~/.config/letapis/config.yaml` — the fixed place, so the command works from any directory.

Nothing found in all three is a refusal that names what it checked. There are no silent
defaults: an engine that quietly started on an empty config would look like one that works
badly rather than one that was not told where to look.

The third place is the one worth setting up once. With a config there, `letapis doctor` runs
from wherever you happen to be standing.

### On Linux, where the engine runs in a container

The command lives with the engine, so it is called inside the container from outside it:

```bash
docker exec <container> letapis doctor --dry-run
```

The config path above is the container's, not the host's.
