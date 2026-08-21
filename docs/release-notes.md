# Release notes

**Reindex every watched folder after installing this version.** Text is cut differently and
chunks now carry marks the previous engine never wrote. What is already stored stays searchable,
but it answers from the older cut until it is read again: run `force_reindex` on each folder.

## What changed

- **The similarity floor for the vector branch is one constant for every query.** It used to be
  chosen from the length of the question, which filtered short queries hardest, the case where
  the meaning half matters most. A request may still name its own floor for that one call, and a
  value below the constant returns candidates the constant would have cut.
- **Answers are trimmed by the shape of the reranker's score curve, not by the limit alone.**
  Where the scores fall off a cliff, what lies below it is dropped; where they are flat, nothing
  is. This is on by default and a request can turn it off with `autocut`.
- **Every score in a result carries the name of its own scale** — `rerank_score` from the
  cross-encoder, `similarity` a raw cosine, `relevance` the full-text measure, `rrf_score` a
  function of position in the merge; the verbose form carries `avg_similarity` beside them, for a
  hit averaged over several chunks. They are not comparable with one another, and a field that is
  absent means not measured rather than measured zero.
- **A search parameter overrides only itself.** Naming one no longer takes the rest out of the
  engine's configuration.
- **`search` can return where a hit sits in its file** — the enclosing section, the path of
  sections down to it, and its siblings — with `structural_context`.
- **A folder chooses which parser reads its files.** `parser` on `index_folder` and
  `update_folder` names one; an unregistered name is refused before anything is written, and the
  refusal lists what this engine has registered.
- **`recursive` and `debounce_ms` can be changed on a folder that already exists.** Until now
  they could only be chosen when the folder was added, and changing them meant removing the
  folder and losing its index. `odoo_aware` can now be set at registration rather than in a
  second call.
- **No chunk is larger than the embedder's window.** Text is bounded to it before it is
  embedded, and a chunk that is not is refused rather than stored. An oversized chunk used to be
  embedded whole and truncated by the model, which produced a plausible vector for a text the
  model had only partly read. Markdown is cut by the configured `embeddings.chunk_size`.
- **Files are read as UTF-8 explicitly**, so the engine starts and indexes the same way whatever
  the machine's locale.
- **Four tools are new, and the set is 49 where it was 45.** `ignore_patterns` lists every
  exclusion in force, across all the layers that contribute one; `list_files_by_handler` says
  which handler parsed which files; `restore_from_files` rebuilds memory records from the files
  behind them; `memory_repair_carriers` fills in what a record is missing, and reports without
  changing anything unless it is asked to apply.
- **Four tools that already existed take new parameters:** `autocut` and `structural_context` on
  `search`; `parser` and `odoo_aware` on `index_folder`; `parser`, `recursive` and `debounce_ms`
  on `update_folder`; `full` and `folder` on `list_folders`. The last two are there because
  `list_folders` now answers short by default — path, files indexed, whether the watch is active,
  and the marks the folder declares — with `full` for every field and `folder` for one record.
- **The engine says what it could not do, instead of leaving a gap to be inferred.** `/health`
  names the state of each dependency and breaks down what is missing from the index; a file that
  was skipped or failed says which file and why; a vector that was not produced has a named
  reason; a run that was cancelled or failed no longer reads as a healthy one; and a watch whose
  loop has died is no longer reported as running.
- **An answer too large to return is written to a file on the engine's machine.** The reply
  carries its size and address instead of the content, and `fetch_file` brings it over. The file
  does not outlive its collection.
- **Memory is rebuilt from its files if its database is lost**, and recall says when a date
  window could not filter rather than quietly returning everything. A file that has disappeared
  marks its record instead of destroying it.
- **Tools that delete irreversibly declare it as a protocol field** rather than as a sentence in
  their description, so a client can act on it without reading prose. Tool and parameter
  descriptions were rewritten against the code they describe.

A large part of this release is not visible from the outside and changes nothing in how the
engine behaves.

## Configuration

In the engine's own settings, four keys are gone. An engine that meets them ignores them and
keeps its own defaults, so a configuration carrying them still starts, but the thresholds they
used to set no longer exist:

```yaml
search:
  adaptive_short_threshold:    # gone
  adaptive_medium_threshold:   # gone
  adaptive_long_threshold:     # gone
  adaptive_scope_threshold:    # gone
```

What replaces them, and what is new beside them. `response` is a new section: its three keys have
to be written under a `response:` heading of their own. Every key below has a default, and none of
them has to be set:

| Key | Default | What it decides |
|---|---|---|
| `search.vector_floor` | `0.25` | the one similarity floor, replacing the four above |
| `search.autocut_enabled` | `true` | whether the score curve trims the tail |
| `search.autocut_jump_ratio` | `0.2` | how steep a fall counts as the cliff |
| `search.autocut_min_keep` | `1` | how many results survive however steep it is |
| `search.branch_candidates_per_result` | `2` | candidates each branch fetches per result asked for |
| `reranker.max_doc_tokens` | `2048` | the token budget a document is trimmed to for scoring |
| `response.max_chars` | `25000` | above this an answer is written to a file instead of returned |
| `response.spill_dir` | engine's own | where those files are written |
| `response.spill_ttl_seconds` | `300` | how long one waits to be collected |
| `indexing.watch_liveness_interval_s` | `60.0` | how often a watch is checked for being alive |

A misspelled key is ignored and the engine keeps its own default, so a typo looks exactly like an
applied setting. The engine names what it ignored when it starts.
