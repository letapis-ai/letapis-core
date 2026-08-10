# Episodic memory

What was decided, what happened, and why the current shape of things is the shape it is. Ordinary
search answers about the corpus as it stands now; memory answers about how it got there.

The tools on this page share the prefix `ena_` — **ENA, the engine's Episodic Narrative
Architecture**: the part that stores events as episodes with their provenance and their links to
each other, rather than as documents.


**Which engine holds your memory is a question of fact, not of intent** — and the intuitive answer
is wrong often enough to be worth checking. Episodes grow from folders somebody marked as a source
of them, and inside such a folder creation is inclusive: any indexed markdown with non-empty
frontmatter produces one. Mark a folder of someone else's documentation and that engine
accumulates episodes from *their* frontmatter, about *their* documents — and a few of yours may
have been written there by hand.

The failure this causes is the nasty kind. Ask the wrong engine and you do not get silence: you
get a confident answer, drawn from a corpus that has nothing to do with your work — and on an
engine indexing a large body of someone else's documentation, generated episodes can outnumber
anything of yours by orders of magnitude.

**A recall will not show you that.** It returns a handful because that is the default limit, and a
handful of noise reads like a little noise. The measure of how much is there is `summary.scanned`
from a hygiene scan, run against that engine — one call, and it settles whether this corpus holds
your memory or someone else's frontmatter.

Before trusting a recall, know which engine answered.

## Recalling

```python
mcp__<engine>__ena_get_context(query="what we worked on yesterday")
```

**One call is usually the whole answer.** Reading files or searching code after a recall tends to
return the present, and the question was about the past — they answer different things.

### Windows, and how to tell whether one was applied

Episodes can be long. A bare `limit` over a large corpus returns a wall of text, and on a big
enough answer the client spills it to a file where you end up reading blind. A date window is the
natural remedy, and any temporal word in the request — yesterday, last week, back in March — is
one waiting to be written down.

```python
mcp__<engine>__ena_get_context(query="work", date_from="2026-01-04", date_to="2026-01-10")
mcp__<engine>__ena_get_context(query="work", session_id="…")   # one working session instead
```

**Check that it narrowed rather than assuming it did.** A date filter can only bite on episodes
that carry a date, and an episode gets one from its own frontmatter — an explicit `date`, then a
completion date, then a start date, and file modification time as a last resort. Episodes written
directly rather than derived from a document often carry none of those, and a window over a corpus
like that filters nothing while looking as though it did.

**The tell is already in the answer you have: `t_valid`.** Null on every row means nothing in that
result was datable, so nothing could have been filtered by date — and the dates you read in the
text are the episodes' own content, not evidence the window held. This costs nothing.

**When you want it beyond doubt, one extra call settles it:** ask the same question with a window
that cannot possibly match, two days years ago. A different, smaller result means the filter
works; the same result means it does not.

### Check memory before acting on a plan

A task list says "build X"; memory may say X was reconsidered. Later decisions override earlier
plans, and the plan does not know it.

The order that saves the work is: **recall first, then read the plan, then implement.** The cost
of skipping it is building the thing that was deliberately dropped — and the plan will look
perfectly convincing while you do it.

## When memory and reality disagree

**Reality wins, and recording that is worth the minute it takes.** A stale memory left in place is
not neutral: it gets recalled confidently and reads exactly like a true one.

```python
mcp__<engine>__ena_correct_fact(
    old_query = "phrasing that will match the stale episode",
    new_text  = "the current truth, as a full sentence",
    reason    = "why — evidence, not 'updated'",
)
```

It soft-deletes the old episode, creates the new one, and links them, so the next session inherits
what you learned instead of the claim you had to argue with.

### What should trigger it

- **Someone corrects you outright** — "we do it differently now", "that stopped being true".
- **Code contradicts memory.** This is the strongest signal: memory says A, the file you just read
  says B. Code wins.
- **A newer document contradicts an older episode** — "using X" against "migrated to Y".
- **Memory contradicts itself** — two episodes of comparable confidence saying opposite things.
  Keep the newer, correct the older.

### What not to correct

- **Opinions.** "We prefer this style" is not falsified by someone momentarily disagreeing.
- **Historical facts.** "That work started in March" is fixed in time and stays as written.
- **Similar but different.** Two episodes about different modules are not in conflict — check what
  each is about before deciding one is wrong.
- **Weak matches.** A returned similarity below ~0.75 means the tool found something loosely
  related, not the episode you meant. Review before trusting it.

### Write the reason for the person who reads it in a year

It becomes part of a permanent audit trail. "updated", "wrong" and "fix" tell that person nothing.

| Instead of | Write |
|---|---|
| `"updated"` | `"the migration completed in March; the old backend is gone"` |
| `"wrong"` | `"verified by reading the storage backend — no code path for it exists"` |
| `"fix"` | `"design reversed after performance testing, see the follow-up doc"` |
| `"user said so"` | `"confirmed in session and matches the current code"` |

The test: could they understand **why** without re-investigating?

### Confirm it landed

After a correction returns `status="corrected"`, re-run the original query. The old episode should
be gone from the result and the new one should come back first. The call returns both ids if you
need to reference the change later.

`status="no_match"` means nothing crossed the similarity threshold: lower it, or use a more
generic `old_query` — or accept that the fact simply was not in memory and no correction is needed.

## Forgetting without replacing

Correction always creates a replacement. When something is no longer relevant and there is
**nothing to put in its place**, forget it instead.

```
correct_fact:  find old → create new → soft-delete old → link them
forget_fact:   find old → soft-delete old. Nothing else.
```

```python
mcp__<engine>__ena_forget_fact(
    query  = "the approach, the module, the purpose",
    reason = "rolled back entirely — the design changed, there is no replacement",
)
```

Reach for it when an engagement ended, an approach was reverted with nothing taking its place, or
something was recorded by mistake. A second call on the same episode returns `no_match` rather
than doing damage, and the original reason is preserved rather than overwritten.

**Act one at a time.** The call takes a single target and acts immediately; a query that looks
precise can pull in a valuable neighbour ranked slightly higher. Surface the candidate, get a go,
then act.

## The audit trail

Forgotten episodes are hidden from recall but not destroyed, and `ena_list_forgotten` is the only
way to see them.

> **Do not confuse it with `list_forgotten_documents`.** The names are nearly identical and the
> behaviour is opposite: this one searches forgotten **episodes** by meaning; that one lists
> retired **documents** and matches substrings of path and title only. Reaching for the wrong one
> returns an empty result that reads like "nothing was forgotten".

```python
mcp__<engine>__ena_list_forgotten(query="storage backend")   # semantic search through forgotten only
mcp__<engine>__ena_list_forgotten(limit=20)                  # most recently forgotten first
```

Each entry carries what it was, when it was forgotten and why, when it was originally recorded,
and — the useful field — **`replaced_by`**:

| `replaced_by` | What it means |
|---|---|
| `null` | forgotten outright; nothing took its place |
| `{id, event, …}` | superseded, and `id` is the episode that replaced it |

That is what answers "what did we used to think" and "why did this change" in one call: the
forgotten claim, the reason, and the thing that replaced it.

There is no undo through the tools. If something was forgotten by mistake, list the recent ones,
identify it, and record the truth again deliberately.

## Recording an episode

```python
added = mcp__<engine>__ena_add_episode(
    event      = "what happened, in a sentence or several",
    kind       = "decision",
    provenance = "where this came from — verified in code, stated by a person, inferred",
)
```

**Record the provenance when you write the episode.** An audit later flags episodes that do not
say where they came from, and that gap cannot be filled from memory once the session is over —
whoever finds it has only the claim, with no way to weigh it. The call also takes `significance`
and `confidence` when you have grounds to set them, and `context` for structured extras.

Then, before you trust it as new, check whether it already exists:

```python
conflicts = mcp__<engine>__ena_find_conflicts(
    episode_id = added["episode"]["id"],
    threshold  = 0.85,
)
# non-empty → is this a refinement of that episode, or a replacement? Decide, do not add both.
```

### Episodes also appear on their own

Indexed markdown creates them automatically from frontmatter — but only where a folder was marked
as a source of episodes. **Two gates, and both must be open:** the folder carries `episodes=True`
(see [corpus](corpus.md) § Whether a folder grows memory, where the default is off), and the file
has non-empty frontmatter. Inside a marked folder the second gate is inclusive: **any markdown file
with non-empty frontmatter produces an episode** — a general one if nothing more specific matched.

| Frontmatter | Episode kind |
|---|---|
| `type: decision` | decision |
| `type: status` | milestone |
| `status: completed` | milestone |
| `status: active` | milestone |
| `importance: high` | insight |

**To opt one document out of a marked folder, put `episode: false` in its frontmatter.** This
matters more than it looks: the flag lives in the *file* and is re-read on every index, so it
survives a full rebuild —
whereas forgetting an episode only marks the stored copy and is undone the next time the file is
indexed. For a document that should permanently stop generating recall, do both: forget what
exists, and set the flag so it is not recreated.

### Frontmatter that makes recall work

```yaml
---
status: active
type: stage
project: <the work this belongs to>   # groups episodes; without it recall cannot cluster them
started_date: 2026-01-21              # lets date-range queries find work in progress
---
```

On completion, `status: completed` plus a `completed_date` — the engine fills that one in if it is
missing.

**Which date the filter uses**, in order: an explicit `date`, then `completed_date`, then
`started_date`, and file modification time only as a last resort. Recording a start date is what
makes active work findable by date rather than only after it finishes — and an episode carrying
none of these cannot be reached by a date window at all, which is the usual reason a window
appears to do nothing.

### Keep episodes short

An episode is a record of what happened and what follows from it, not a report of the work. The
detail already lives in the documents it points to. A few lines is right; when it will not fit,
that is usually two episodes rather than one long one.

Oversized episodes hurt twice — as noise in memory, and as a wall of text on recall.

## Following the thread

Episodes within the same project link chronologically, and you can walk that line in either
direction from any point:

```python
mcp__<engine>__ena_walk_timeline(episode_id="episode-xxx", direction="backward", k=5)   # or "forward"
```

`ena_get_context(include_causal=true)` returns a bounded skeleton of the same links alongside each
recalled episode.

## When recall comes back empty

**"No confirmed memories found" while the documents clearly exist** has six causes worth walking
in this order — the first two are the cheapest to check and the easiest to overlook:

1. **You asked an engine that holds no episodes.** With several registered this is the most common
   cause by far, and the emptiest-looking one: the answer is correct for the corpus you asked, and
   says nothing about what another engine knows.
2. **The folder was never marked as a source of episodes.** The documents are indexed and
   searchable, and none of them was ever remembered — the default is off. `list_folders` reports
   the flag per watch; [corpus](corpus.md) § Whether a folder grows memory is how it gets set.
3. **The episodes have no embeddings** — they cannot be found by meaning without them. Re-sync
   with `sync_episodes(path, force=True)`, and check the embedding service was actually up while
   it ran.
4. **The sync path was wrong.** It must be a path the engine watches — take it from
   `list_folders`, not from wherever the files feel like they live.
5. **The frontmatter does not trigger.** `type` must be one of the values in the table above, and
   `project` must be present for grouping.
6. **The query does not match the content.** Episodes are found by meaning like everything else;
   broaden it, or name the project.

**`sync_episodes` counts scanned files and created episodes separately, and the pair tells you
which of these you have.** Zero files means the path is not in the index at all — check
`list_folders` and use the exact folder it reports. Files scanned but nothing created means the
gate closed further in: an unmarked folder skips every file it reads, and so does frontmatter that
does not trigger.
