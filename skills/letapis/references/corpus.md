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

**Its rows carry more than paths, and four fields answer questions you would otherwise guess at:**

| Field | What it tells you |
|---|---|
| `active` | a watch can be listed and switched off. An inactive folder answers nothing, and the row looks entirely normal |
| `files_indexed` · `last_update` | how much is actually in there and when it was last touched. Zero files, or a date months old, is a diagnosis rather than a detail |
| `ignore_patterns` | what was deliberately excluded — the single most common reason a file sits in a watched folder and never appears |
| `odoo_aware` | whether this folder is parsed with framework-specific extraction, which decides what the call graph can see in it |
| `nested_under` · `has_nested` | whether this folder sits inside another watch, or contains its own |

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
