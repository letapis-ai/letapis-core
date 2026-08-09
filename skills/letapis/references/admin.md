# When the engine misbehaves

Search comes back thin, a file you know is indexed will not surface, memory answers nothing. This
page is the diagnosis you can do from inside a session — what to read, what each reading means,
and where the line is between checking and changing.


## Read before concluding

Every one of these only reads. Run them freely; they cost a call and settle questions that
otherwise turn into guesses.

| Symptom | What to read | What it tells you |
|---|---|---|
| a query returns nothing at all | `list_folders` | whether the material is watched by **this** engine — the most common cause by far. Read `active` too: a switched-off watch looks entirely normal in the list and answers nothing |
| indexing "finished" but results are thin | `get_operation(operation_id)` | it did not finish. The call returns an id and the work continues; status and phase say where it is |
| something is clearly indexed but never matches by meaning | `get_embedding_stats` | how much of the corpus actually carries vectors. A gap here is exactly this symptom |
| a file sits in a watched folder and never appears | `list_folders` → its `ignore_patterns` | far and away the usual cause, and it is deliberate: whole subtrees are commonly excluded. Check this **before** suspecting the engine |
| specific files never appear and are not ignored | `get_embedding_errors` | which files failed to embed, and why — usually a pattern worth excluding rather than a bug |
| chunks of a file look duplicated or missing | `stale_check` | files violating the chunk-numbering invariant. `refresh=True` re-scans and is itself a background job — collect it by id |
| the corpus references folders you no longer have | `list_orphaned_folders` | indexed data left behind after a watch was dropped |
| the call graph is empty for a whole folder | `list_folders` → its `odoo_aware` | extraction mode decides what becomes a call edge; the wrong mode for the material yields no structure at all |
| a saved finding points at nothing | `verify_findings()` | findings whose source anchor no longer resolves; a scope id narrows it, omitting one checks them all |
| something is running and you do not know what | `list_operations` | everything in flight, with kind and progress |

**Read the operation, not the call.** Long jobs — indexing, deep indexing, a refreshing scan —
return an id immediately and do their work afterwards. A session that treats the return as
completion will search a half-built index and conclude the material is not there.

## When it is memory that misbehaves

Episodes have their own failure modes, and they do not look like search failures.

**An empty recall is walked cause by cause in [memory](memory.md) § When recall comes back empty** —
five of them, ordered by likelihood. That list is not repeated here. What belongs on this page is
the repair side of it:

| Symptom | What to do | Why |
|---|---|---|
| episodes exist but nothing is found by meaning | `sync_episodes(path, force=True)` | they need embeddings; older ones may have none, and a sync that ran while the embedding service was down produces exactly this |
| recall answers with material that is not yours | `ena_hygiene_scan`, then read `summary.scanned` | the count settles whether this engine holds your memory or someone else's frontmatter |
| the same fact keeps coming back twice | `ena_find_conflicts(episode_id)` | duplicates accumulate quietly, and the hygiene scan does not detect them |
| something you know was recorded is gone | `ena_list_forgotten(query=…)` | forgotten episodes are hidden from recall, not destroyed; `replaced_by` says whether something superseded it |

**A re-sync is cheap and safe; forgetting is neither.** Regenerating embeddings only rebuilds what
is derived. Removing episodes is a decision about the record, and it belongs with whoever owns it.

## Changing things

Four operations change state, and three of them destroy data that has to be rebuilt:

| Operation | What it does | Cost of being wrong |
|---|---|---|
| `cancel_operation` | stops a running job at its next safe boundary | none — work already done is kept |
| `cleanup_orphaned_files` | drops records whose files are gone from disk | recoverable by reindexing, slow |
| `force_reindex` | deletes everything indexed for a folder and rebuilds it | the folder is unsearchable until it finishes, which on a large corpus is not quick |
| `remove_folder` | removes a folder's data and stops watching it | the index is gone; the files on disk are untouched |

**None of these is a diagnostic step.** They are what you do *after* a diagnosis, with the
agreement of whoever owns the corpus — a reindex started to see whether it helps is a reindex
started without knowing what was wrong. If the answer to "why is this happening" is not yet in
hand, the table above is where to keep looking.

**Reindexing is not the cure for a bad query.** By far the most common reason a search disappoints
is the question, not the index: the wrong engine, a register the material does not use, a filter
narrower than intended. Exhaust [search](search.md) before touching the corpus — it is faster and
it is reversible.

## Two failures that look like engine faults and are not

**A watched clone that nobody pulls.** The engine answers from the state the files had when they
arrived. Everything looks healthy — the index is current *for those files* — while the source has
moved on. Nothing in the answer says so; `git_status` on the folder does. See [corpus](corpus.md).

**An engine answering from the wrong corpus.** With more than one engine registered, a query sent
to the wrong one returns a confident answer built from unrelated material. That is not a fault to
diagnose, it is an address to check — [SKILL.md](../SKILL.md) § Addressing an engine.
