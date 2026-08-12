# Keeping a corpus

An engine answers about what it was told to watch. This page is the other half of that: deciding
what belongs in the index, adding and removing it, following the long jobs that do the work, and
retiring material that should stop surfacing without deleting anything.

None of it is daily work. All of it is what stands behind an answer that came back thin.


## What is in the index

```python
mcp__<engine>__list_folders()                 # what this engine actually watches
mcp__<engine>__index_folder(path="/path/to/folder", generate_embeddings=True)
mcp__<engine>__get_indexing_progress(path="/path/to/folder")
mcp__<engine>__update_folder(path="/path/to/folder", ignore_patterns=["**/fixtures/**"])
mcp__<engine>__remove_folder(path="/path/to/folder")
mcp__<engine>__get_embedding_errors(limit=50)
```

**`list_folders` is the answer to "is this indexed", and it is worth asking before concluding
something does not exist.** When the material you need is in no engine at all, name the source you
would want added — deciding to index it belongs to whoever runs the corpus, and a precise name
makes that decision easy.

**Its rows carry more than paths, and each field answers a question you would otherwise guess at:**

| Field | What it tells you |
|---|---|
| `active` | a watch can be listed and switched off. An inactive folder answers nothing, and the row looks entirely normal |
| `files_indexed` · `last_update` | how much is actually in there and when it was last touched. Zero files, or a date months old, is a diagnosis rather than a detail |
| `ignore_patterns` | what was deliberately excluded **for this folder** — the single most common reason a file sits in a watched folder and never appears. It is one layer of several, and it is the only one you set here; see below |
| `recursive` | whether the watch descends into subdirectories or holds only the top level. A false here explains a subtree that was never indexed and never reported missing |
| `odoo_aware` | whether this folder is parsed with framework-specific extraction, which decides what the call graph can see in it |
| `episodes` | whether documents here are remembered as events — see below. Off unless somebody said otherwise |
| `description` | free text about why this folder is watched, left by whoever added it. Useful, and no fresher than the day it was written |
| `nested_under` · `has_nested` | whether this folder sits inside another watch, or contains its own |
| `groups` | **not in these rows** — group tags are set on the folder with `update_folder(path, groups=[…])` and read back with `list_groups`. They are a search-time label rather than a property of the index, and what they are for is in [search](search.md) § Narrowing |

### What is excluded, and by which layer

A file is turned away by more than one mechanism, and only the last of them is per-folder: the
engine's built-in list, the machine's `indexing.exclude_patterns`, a set of binary extensions and
file names refused before anything is read, and finally the folder's own `ignore_patterns`.

```python
mcp__<engine>__list_folders()      # the per-folder layer
# GET /api/v1/files/ignore-patterns — all layers, each one named and explained
```

**Ask before you write.** Roughly two thirds of the patterns written by hand into folder configs
on a working machine were already covered by a layer above — `*.pyc` fifteen times, `__pycache__/`
fifteen, `.venv/` eleven. Nobody was careless: until the endpoint answered with every layer, the
only way to find out was to read the engine's source. `index_folder` and `update_folder` now name
any submitted pattern that was already covered, and drop none of them.

**The built-in list is deliberately basic.** It covers what nearly every tree has and carries
nothing for Xcode, Java, .NET or your framework's cache directory. When you add a folder from a
stack the engine has never heard of, look at what its build writes and name it yourself — a
monorepo with an iOS app in it contributed 40,565 nodes of `DerivedData` to somebody's index
before anyone noticed.

**Layers only add up**: nothing set globally can be cancelled for one folder.

### Whether a folder grows memory

Indexing a folder and remembering what happens in it are two different decisions, and `episodes`
is where the second one is made:

```python
mcp__<engine>__index_folder(path="/path/to/vault", episodes=True)     # from the start
mcp__<engine>__update_folder(path="/path/to/vault", episodes=True)    # or later
```

**The flag decides one thing only: whether a document counts as an event.** Indexing and search
are unaffected either way — an unmarked folder is watched, chunked, embedded and searchable
exactly as a marked one is; its documents simply do not become episodes. What episodes are, and
what a document needs in its frontmatter to become one, is in [memory](memory.md).

**The default is no, and it is set on the root of a watch.** A file belongs to the watched folder
whose path is its longest prefix, so marking the root covers the tree below it, and a nested watch
overrides its parent for its own subtree. A document nobody claims is not remembered: memory grows
only where someone said it should.

Changing the flag applies from the next indexing pass. Episodes already recorded stay — turning it
off stops new ones rather than retracting old ones.

**Do not mark the folder the engine writes its own memory into.** Episodes are persisted as files
there, and a marked folder reads those files as documents — so each episode produces a second
episode about the same event, and that one is a document too. Nothing announces it: recall keeps
answering, and the twins look like ordinary results until someone counts. Six months of one team's
notes accumulated 536 duplicates this way, 263 of them in a single month. The same caution applies
to any folder holding material generated by the engine rather than written by a person.

### Long jobs run in the background, and you have to collect them

Indexing a folder does not finish inside the call. It returns an **`operation_id`**, and the work
continues on the engine:

```python
op = mcp__<engine>__index_folder(path="/path/to/folder", generate_embeddings=True)
mcp__<engine>__get_operation(operation_id=op["operation_id"])   # status · phase · progress · result
mcp__<engine>__list_operations()                                # everything in flight right now
mcp__<engine>__cancel_operation(operation_id=…)                 # stops at the next safe boundary
```

**A call that returned is not a job that finished.** Treating the return value as completion is how
a search gets run against a half-built index and comes back thin — which looks exactly like "there
is little about this here". `get_operation` carries the final result in its detail once the status
says completed; `cancel_operation` stops cleanly and keeps whatever was already done.

### Paths are the engine's, not yours

The engine may run on another machine or inside a container, and it reports paths as **it** sees
them. When a path from a hit does not resolve on your disk, `fetch_file(path=…)` pulls the file
from the engine rather than leaving you to work out the mapping. And every call that takes a
folder wants the path exactly as `list_folders` reports it — not the one you would type.

## Retiring material that should stop surfacing

Archived plans, superseded designs and deprecated docs keep answering queries long after they
stopped being true. `forget_document` hides one from search **without touching the file on disk**.

```python
mcp__<engine>__forget_document(path="/path/to/archive/old_plan.md",
                               reason="superseded by the 2026 rewrite; kept for history")
```

The file node is marked, and the mark cascades to every chunk of it; search excludes them by
default. You can still open the file directly, and the audit trail can find it again.

| Someone says | What it means |
|---|---|
| "why does this old doc keep coming up" | stale — hide it |
| "this is out of date" / "deprecated" / "we removed that" | same |
| "we archived that plan, it should not surface" | same |
| results keep coming from an `*_archive/` path | worth proposing proactively |

**Related calls:** `forget_folder(folder, reason)` hides a whole subtree in one go and is
sibling-safe; `restore_document` and `restore_folder` undo either; `list_forgotten_documents`
shows the audit trail with the reason and the time, and matches substrings of path and title only —
it is not a semantic search.

**Write the reason for the person who finds it in a year** — same discipline, and the same
worked examples, as for correcting a memory: [memory](memory.md) § Write the reason.

**Two edge cases worth knowing.** Editing a forgotten file regenerates its chunks: existing ones keep
the mark, new ones do not, so re-run the call after a substantial edit. And do not forget a
document you have not read — "looks old" and "is superseded" are different claims, and only one
of them survives someone asking why the answer disappeared.

## Bringing material onto the engine

Indexing needs the material to be on the machine the engine runs on, which is not always the
machine you are on. For source you do not have yet, the engine can fetch and track it itself:

```python
mcp__<engine>__git_clone(url="https://…/project", branch="main", depth=1)   # shallow by default
mcp__<engine>__git_pull(path="/path/on/the/engine")                          # fast-forward only
mcp__<engine>__git_fetch(path="/path/on/the/engine")
mcp__<engine>__git_status(path="/path/on/the/engine")                        # branch, ahead/behind
mcp__<engine>__workspace_browse(path="/path")                                # what is on the node
mcp__<engine>__list_workspace_folders()                                      # watched folders, git-aware
```

**A clone is not an index.** Fetching a repository puts files on the node; the engine only answers
about them after `index_folder`. The reverse trap costs more: a watched clone that nobody pulls
answers confidently from the state it had when it arrived — the index is fresh, the source is
stale, and nothing in the answer says so. `git_status` is what tells you which.

## When the index and the disk disagree

An index can fall out of step with the files it was built from, and the symptoms read as engine
faults: a hit pointing at a line that has moved, material plainly indexed that never matches by
meaning. What to read in each case, and which operations change state rather than report on it,
is in [admin](admin.md) — it is not repeated here.
