# Release notes

**If you are upgrading from a version earlier than 26.822.1, reindex every watched folder
after installing this one.** 26.822.1 changed how text is cut, and a file indexed by an older
engine carries no record of which cut produced it. The engine reads that silence as "leave it
alone", not as "re-cut everything", so nothing happens on its own: the folder keeps answering
from the old cut until you run `force_reindex` on it. Upgrading from 26.822.1 itself needs no
reindex — this version does not touch the cutter.

## What changed

- **`folder` on `blast_radius` now narrows below the root of a watched folder.** Naming a
  subdirectory used to select the watch that contained it and then answer from all of it, so
  asking about one module returned callers from every module in the tree. The answer is now
  limited to files under the path you named; naming the watch root behaves as before. The
  parameter's description said "path prefix" all along — the behaviour has caught up with it.

- **A `scope`d answer says which callers are not on that model.** `scope` filters definitions
  and cannot filter callers: a call site is found by name, and a name does not say which type
  it was called on. That limit is unchanged. What is new is that the answer no longer hides it.
  Each caller carries `scope_relation` — `in_scope` (same model), `defines_its_own` (another
  model that defines this name itself), or `undetermined` (a test class, a helper, or a model
  with no definition — the answer cannot tell). A mixed list raises a hint. Nothing is dropped:
  a filter would have judged the undecidable ones by deleting them.

- **`index_folder` names both ways of narrowing a folder, not one.** Its description advised
  `ignore_patterns` and said nothing about `file_patterns`, which was declared a few lines
  below. Both are now described, with what each matches against: a whitelist is checked against
  the file **name**, not its path (`*.py` works, `src/*.py` matches nothing), and whatever it
  turns away is counted and returned as `pattern_misses`.

- **`deep_index` says what it does not build.** A research scope holds chunks and the chain
  between them — no chapter, section, figure or table nodes — so `get_research_structure` on
  it returns an empty tree however well the document is organised. The description now says
  so; before, the empty tree read as a property of the document.

## Known limits of this version

- Only the text layer of a document is indexed. Whatever a page says in pictures — an icon
  standing for a key, a label on a diagram, a value on a drawing, a scan with no recognition
  layer — is not in the corpus. The tell is a hole inside a passage that came back, not an
  empty answer.
- A service header longer than the chunk budget still yields a chunk without content.
- PDF and Word files are cut by length alone.
