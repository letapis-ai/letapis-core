# Release notes

**If you are upgrading from a version earlier than 26.822.1, reindex every watched folder
after installing this one.** 26.822.1 changed how text is cut, and a file indexed by an older
engine carries no record of which cut produced it. The engine reads that silence as "leave it
alone", not as "re-cut everything", so nothing happens on its own: the folder keeps answering
from the old cut until you run `force_reindex` on it. Upgrading from 26.822.1 or 26.823.1 needs
no reindex — this version does not touch the cutter.

**Check your config against the one this version ships.** Keys are added and renamed between
versions, and a config that has fallen behind will not tell you so. The engine reads a key it
does not recognise and drops it — deliberately, so that upgrading is never met by a refusal over
a line that merely stopped meaning anything — and the price of that kindness is silence: a
setting renamed since your version, or one added after it, simply has no effect, and nothing
says a word. No command checks this for you (`letapis doctor` repairs memory records, not
configuration). Diff your own `config.yaml` against the `config.yaml` shipped at the top of the
kit, beside `run.sh` and `RUN.txt`, and carry over whatever is new.

## What changed

- **`deep_index` reports the work this run did, not the size of the scope.** Running it a
  second time over an untouched corpus used to answer "Indexed 3 files" — the files it skipped
  were added to the ones it cut, and the difference lived only in the log. Every counter is now
  about this run alone, and the fates partition what was walked: `files_indexed` (cut for the
  first time), `files_reindexed` (changed since the last pass, cut again), `files_healed`
  (see below), `files_skipped`, `files_refused`, `files_empty` and `files_errored` add up to
  the files walked, each file counted once. `chunks_created` and `edges_created` likewise describe one world: a resume used
  to count chunks over the whole scope and edges only for the run, so "340 chunks, 0 edges"
  read as broken chaining when nothing was broken. The scope's own totals are what
  `get_research_structure` answers about.

- **A rerun mends a scope, not only adds to it.** Until now a file was judged by its content
  hash alone, and three things followed from that. A chunk the embedder never answered for
  stayed empty for ever, because the file on disk had not changed. A file deleted from disk
  lived on in the scope with nothing to remove it. And a re-cut that failed halfway lost the
  file, because the old chunks were dropped before the new ones existed. Now a file whose
  chunks are missing vectors is embedded **in place** — no re-cut, chunk ids preserved; a file
  that has gone from disk under the path this call scans loses its chunks from the scope; and a
  re-cut writes before it removes, so an interruption leaves the file as it was. Three new
  numbers say what happened — `files_healed`, `files_removed`, `chunks_without_vector` — each
  named in the answer's sentence only when it actually occurred. Removal is deliberately scoped
  to the path you are scanning: `deep_index` is legitimately called on a single file or a
  subfolder, and a difference computed over the whole scope would empty it.

- **One scope is walked by one run at a time, and the refusal says so.** A call naming a scope
  that another run is walking right now is refused with `scope_busy` and the id of the run
  holding it, and nothing is indexed. Before, such a call went in as a guest: it wrote chunks
  while being unable to say anything about itself. The scope's totals are written by the run
  that owns it and by nobody else, and a run that loses its scope mid-walk stops rather than
  writing into someone else's. A scope whose owner has genuinely died is still claimable — the
  rule keeps out live writers, not stuck ones.

- **A scope says whether its run is alive.** Each row of `list_research_graphs` carries
  `status` — `indexing` while a run is walking it, `completed` when one finished, `failed` with
  the reason when one died — plus `heartbeat`, the last sign of life, and `stale`. A run killed
  outright writes no status at all, since nothing survives to write one; `stale: true` means the
  row still claims to be indexing while nothing has moved for fifteen minutes, and it is to be
  read as dead rather than as working. A long file no longer counts against that: the heartbeat
  keeps moving while a single file is being embedded, so a slow run is not mistaken for a dead
  one.

- **An empty structure tree says why it is empty.** An empty tree used to be readable three
  ways — nothing built one, the parse failed, or the document really is flat — and nothing in
  the tree told them apart. `get_research_structure` now answers in `empty_because`:
  `not_built` (cut by the basic `deep_index`, which builds no structure), `none_found`
  (structure was parsed and the document is flat), or `unknown` (the scope predates this mark,
  where saying so is honest and guessing is not). Sections whose parent chapter is missing come
  back under `unparented_sections` instead of being dropped, so every section the statistics
  count appears somewhere in the answer. Emptiness is now judged by the same numbers the answer
  publishes: a scope holding one section and no chapters used to be called empty while its own
  `section_count` said otherwise.

- **`index_folder` on a folder you already took now does what it says.** Two problems, one
  visible and one silent. The silent one: settings named on a second call — new `file_patterns`,
  say — were never written, because the "already watching" exit came before the write; the
  answer listed them as changed all the same. They are now saved before that exit, under the
  same lock `update_folder` uses, and the answer says from when they apply and what to do about
  files indexed under the old ones. If a long pass is running, the call is refused rather than
  writing settings underneath it. The visible one: during a folder's very first pass the answer
  claimed "Indexing started in background" and handed back the operation id of a pass this call
  had not begun. The answer now says outright whether **this** call started a pass or found one
  already running, and covers both busy states — watched, and still in its first pass — rather
  than only the first. A call that names no settings remains the ordinary way to pick up a
  running pass, and is not an error.
