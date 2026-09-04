# Release notes

**Upgrading from a version earlier than 26.822.1: run `force_reindex` on every watched
folder after installing.** A folder indexed by an older engine keeps answering from the old
cut until you do. From 26.822.1 and later no reindex is needed.

**Check your config against the one in the kit.** Keys get added and renamed between
versions. A key the engine does not recognise is dropped without a word, so a setting that
was renamed simply stops having an effect. Diff your `config.yaml` against the one shipped
at the top of the kit, beside `run.sh`, and carry over what is new.

## 26.904.1

### A zero from the call map says what it did not read

`blast_radius` used to answer an unknown name and a name it could not read the same way: an empty
`callers` list. Those are different facts, and the answer now separates them.

    "callers": [], "caller_count": 0,
    "unread": [{"extension": ".abap", "files": 757, "with_the_name": 1}],
    "hint": "NOT READ: 757 `.abap` files here have no extractor, and 1 of them
             carry this name, so the zero above speaks only for what was read."

`unread` names an extension the engine has no reader for, how many such files sit in the scanned
folders, and how many of them carry the name you asked about. A non-zero `with_the_name` means the
empty `callers` above is about what was read, not about your codebase.

`unparsed` is the neighbouring case: files that were opened and whose reader gave up. A zero beside
an empty `unparsed` and an empty `unread` is a zero about the whole folder.

### A name met inside a string is a mention, not a call

A framework often reaches code by writing its name as text — a command name, a registry key, an
event. The call graph cannot see that by construction, and until now the answer swallowed it.

Those places come back in `mentions`, with `mention_count` for the total before the list is capped:

    "mentions": [{"file": "src/app/commands.ts", "line": 42, "kind": "string"}],
    "mention_count": 3

A mention is never promoted to a call. What a string *means* is the caller's business; this field
says only that the name is written there.

### A class reached through a registry is an edge, not a silence

Some code is never called by name — it is put into a registry under a string key, and whoever wants
it names the key. `registrations` answers from both ends: give it the symbol and you learn the key
it is registered under; give it the key and you learn what answers to it.

    "registrations": [{"key": "product.template", "symbol": "ProductTemplate",
                       "via": "_name", "file": "models/product.py", "line": 18}]

`named_at` is the other half — the places in markup that write that key, with `named_at_count` for
the total. Zero callers beside a registration reads "reached the other way", not "unused".

### What the reader skipped on purpose says so

A reader that deliberately ignores part of a file — a docstring, a comment block — now declares it
in `skipped_on_purpose` instead of leaving the omission invisible. What is missing from an answer
and why is part of the answer.

### The engine answers in English

Diagnostics, hints and refusal messages come back in English throughout.

## 26.831.1

### A PDF with bookmarks now gives you its table of contents

Ask a research scope for its structure and you get the chapters and sections the document carries
in its own bookmarks, with the nesting you can rebuild from them.

    get_research_structure(scope_id="…")

A book-sized tree does not fit in one answer: the engine writes it to a file on its own disk and
hands you the path. Follow it.

Sections come back in one list per chapter, each with `level`, `order` and `file_path`. A
section's parent is the nearest preceding entry of a smaller level. Order runs per document, so
in a scope holding two files `order` 5 can be followed by `order` 0 — that is the second document
starting.

**Only PDF bookmarks are read.** A `.docx`, an `.epub`, a markdown file never carried an outline,
and no re-indexing gives them one. Figures and tables are not built for anyone.

### An empty structure tree tells you which of four things happened

`empty_because` separates four facts:

| Value | What it means |
|---|---|
| `none_found` | bookmarks were read and there are none: a scan, or a PDF published without them |
| `read_failed` | the bookmarks are there and reading them failed: whether this document has a structure is unknown. `message` names the files and the error, and the scope is worth re-indexing |
| `not_built` | no file here carries an outline at all — wrong format for a tree |
| `unknown` | the scope was indexed before any of this existed |

### Your scope was indexed by an older version

`structure_needs_reindex` tells you when the tree holds nodes this engine did not write.
Re-indexing does not clear them — delete the scope and index it again.

### An answer that did not fit names the parameters of the tool you called

When a reply is too large, the engine hands back its size and an address instead of the body. That
refusal now also lists what the tool you called actually accepts, read from its own schema:

    … This tool takes: kind, active.

Narrow with those. They differ per tool — `list_operations` takes `kind` and `active`, memory
recall takes `query`, `limit`, a date window and more — so the names in the refusal are the ones
that will work on the call you just made.

A path that belongs to no tool — the file channel, a panel route — lists none.

## 26.830.2

**A pass** is the engine reading a folder and bringing the index up to date with it. One runs
when a watched file changes, one runs on a timer every five minutes, and you can start one
yourself with `index_folder`. A pass only ever *adds and refreshes*; taking entries out is a
separate job — see the section on removing files.

**Calls** are written as `name(argument=…)`. That is the tool name your client shows, and each
one has an HTTP address given next to it the first time it appears.

---

### Read first: one change can alter what your corpus holds

#### A `.gitignore` in a watched folder no longer affects indexing

**Your corpus will grow.** Everything a `.gitignore` was keeping out becomes eligible on the
next pass — for many folders that is `data/`, `dist/`, fixtures, generated files. If any of it
should stay out, move those patterns into the folder's own rules **before** the next pass runs,
not after: once entries are in, taking them out is a second job.

    update_folder(path="…/your-folder", ignore_patterns=["build/", "fixtures/"])
    POST /api/v1/files/update

`ignore_patterns` replaces the folder's list — it does not append to it. Read the current one
first if the folder already has rules.

A `!` line that used to let something back in has the same meaning written among the folder's
rules. Write it there and it keeps working.

    folder_rules(path="…/your-folder")
    GET /api/v1/files/folder-rules?path=…/your-folder

That answer names every rule dropping files in this folder and which layer carries it, so you
can see what your folder is left with before anything runs.

---

### What decides whether a file is indexed

Three lists of patterns, glued into one in this order, and **the last line that matches wins** —
so a rule written lower overrules the same rule written higher:

    1. the engine's built-in list
    2. your config
    3. the folder's own rules      ← lowest, so a `!` here overrules the two above

Two more things drop files and are **not** part of that list, so no `!` reaches them: the VCS
directories (`.git/`, `.svn/`, `.hg/`), which sit below the folder, and the sets matching by file
extension, by file name, or by a substring that marks a secret. `ignore_patterns()`
(`GET /api/v1/files/ignore-patterns`) lists every layer and says which of them a folder may
overrule.

#### One folder needs the file type your config excludes everywhere

Write the cancellation among that folder's own rules, prefixed with `!`:

    update_folder(path="…/vendor-docs", ignore_patterns=["!*.md"])

That folder keeps them; every other folder still drops them. There is no separate field for
this and no list of allowed values to pick from — a `!` line is an ordinary rule that happens to
sit lower than what it overrules.

A rule carried by more than one layer is only cancellable when every one of them is. `.DS_Store`
is carried by three, so a `!` on it does nothing.

#### A file is on disk and search does not find it

    folder_rules(path="…/addons_oca")

Next to each dropping rule the answer names the layers it came from. That is which one caught
your file.

#### You added an exclusion and the files are still in the index

A pass will not remove them. Entries already in the index stay until you sweep them out:

    cleanup_orphaned_files()
    POST /api/v1/files/cleanup

It drops index entries nothing currently backs — a file gone from disk, or a file excluded by
that folder's current rules. Your files on disk are never touched.

---

### Everything else

#### A file is in the index but searching it returns nothing

The next ordinary pass over its folder reads the file again and fills it in, with no reindex by
hand.

#### You want to tell a folder how to read its files and do not know the names

Name one you know is not there, and the refusal tells you what is:

    update_folder(path="…/your-folder", parser="no-such-name")
    → error: unknown_parser, with known_parsers and known_lenses in the answer

Parsers cut files into chunks; lenses read the links between them. A name may be registered as
one, the other, or both. Nothing is written when the name is unknown, so the folder keeps the
setting it had.

What your engine has depends on the build it was made from, so the refusal is the list.

#### You ask what the engine is busy with and get thousands of lines back

    list_operations(active=true)
    GET /api/v1/operations?active=true

`active` narrows the answer to work that is queued or running. Without it you get every
operation the engine remembers; when that does not fit in one answer, the engine writes it to a
file on its own disk and hands you the path.

The summary of a finished operation is in `result`. If your code reads it from `detail.result`,
move to `result`: it is there for every ending except `ERROR`, which carries `error` and nothing
else. A run someone stopped still hands you the summary it had by then.

#### One pass over your Odoo folders will be slow after this upgrade

Files in a folder you named `odoo-xml` are read again once, on the first ordinary pass after you
install. Nothing to do on your side. Folders named anything else are untouched.

#### Files that failed to get embeddings take a long time to retry

The retry pass asks for everything waiting at once instead of one file at a time, so it spends
its time on the work rather than on round-trips to the embedding service.

#### A pass over a large folder takes longer than the work in it

The search for records whose file is gone runs on its own schedule, so an ordinary pass reads
only what it removes.

## 26.828.3

### A folder names how its files are read

A watched folder can name a lens, and both halves of the engine answer to that name: the one
that reads links and the one that cuts files into chunks. Set it with `update_folder`:

    update_folder(path="…/magento2/app/code", parser="magento")

The engine refuses a name it does not know and tells you what it has. Parsers and lenses are
listed separately, because a name can be known to one side and not the other. `magento` is the
name for a Magento tree; `odoo-xml` and `xml` were already there.

### Magento's wiring is part of the call map

Under the `magento` lens, `blast_radius` reads the wiring the framework declares in markup.
A `preference` in `di.xml` binds an interface to a class, and the map follows it. A plugin
class named `afterSave` resolves to the `save` it wraps. No file spells that link out; the name
is the only place it is written.

### Templates are code

A `.phtml` template answers as a `.php` file does. A method called from inside `<?php … ?>`
comes back as a caller, with the template's path and line. A name written in the surrounding
HTML is not a call and is not reported.

Templates are also cut by their own markup now, so a search hit lands on a whole insert, not
half of one.

### Magento's XML is cut by its declarations

A chunk of `di.xml`, `events.xml`, `webapi.xml` or a layout file is a declaration with its own
name — `preference`, `type`, `virtualType`, `plugin`, `event`, `observer`, `route`, `block`,
`container`, `referenceContainer` and the rest. A search result says which declaration it came
from instead of showing an unnamed piece of markup.

Layout nests a block inside a block, and the name follows the nesting the whole way down:
`content.category.products.category.product.list`. A declaration deep in a layout file carries
its own name rather than riding inside its ancestor.

Chunks already in the index keep the shape they were cut into. Files this release reads
differently get re-cut on the next pass over their folder; the rest are skipped. Restarting the
engine after an install normally starts that pass.

If a folder you named `magento` still comes back as unnamed markup, run `force_reindex` on it.

## 26.828.2

### The call map reads PHP

`blast_radius` answers on PHP. A `.php` file yields definitions and calls the way a Python one
does: functions, methods, and the four type declarations (class, interface, trait, enum). A
declaration with no body is a definition too, so a call by name reaches the interface that
states the contract as well as the class that implements it.

The map reads a bare call, a namespaced call, `$this->x()`, `Klass::y()`, `$x?->y()` and
`new Klass()`. It leaves out a callee with no static name: `$fn()`, `$obj->{$method}()`,
`$obj->{CONSTANT}()`. Those names are decided while the code runs, and taking the written one
would claim a call to a method that need not exist.

PHP symbols keep their own namespace, so a `save` in PHP does not collide with a `save` in
Python, TypeScript, C, Swift or Rust.

The map covers `.php`. A `.phtml` template yields no definitions or calls.

## 26.828.1

### Work on a branch in a copy of the tree

A copy of a repository is indexed without appearing in anyone else's answers. Register it as a
watched folder with `hidden: true` and `supersedes: "<the watched trunk>"`, then name it in
`reveal` on each call: you get your copy, and the trunk it stands in for drops out of that one
answer. Everybody else gets the trunk.

The whole procedure is in `skills/letapis/references/worktree.md`: registering the copy, asking
while you work, catching up with the trunk, retiring it.

### The folder that owns a file decides its fate

`cleanup_orphaned_files` judges a file by the watched folder that owns it, which is the
innermost one whose path covers it. Where folders nest, the inner rules govern the inner files.
`index_folder` and `update_folder` judge the marks by the same rule.

### Cleanup narrows to the folder you name

Pass `path` to `cleanup_orphaned_files` and the sweep covers that folder alone. Ask
`get_indexing_progress` about a research scope with `scope_id` and the answer is about that
scope.

### One question per key in the visibility note

`visibility.hidden_folders` names the hidden folders kept out of this answer.
`superseded_by_reveal` names the trunk your copy stood in for, and appears only when a
substitution happened. You act on them differently: a hidden folder opens when you name it in
`reveal`, while a superseded trunk returns as soon as you stop revealing.

### Refusals with a name

`supersedes` is accepted when it names a watched tree and comes from a folder whose watch is
running. Otherwise the call is refused by name, `supersedes_unwatched` or `supersedes_from_inactive`,
and nothing is written.

`ena_correct_fact` takes `context`, the same free-form payload `ena_add_episode` takes.

## Recall takes a projects filter

`ena_get_context` accepts `projects`. Pass one or several values and you get records from
those projects only. The store does the narrowing, so you get everything that matches, not
the part that surfaced first.

The reply also says how many records carry no project at all — those no filter can reach.

`max_depth` and `min_similarity` are now declared in the tool schema.

## Date windows are applied by the store

`date_from` and `date_to` are a condition on the `t_valid` index. A window returns what it
holds, whatever else is in the corpus and whatever limit you asked for.

Records without a date are returned and counted separately: a window cannot check them, and
dropping them would empty the very questions that ask what was decided.

## search says when a filter does not apply

`types=['episode']` together with `groups` no longer answers zero. Group tags resolve to
watched folders and episodes carry none, so the reply says the filter does not apply here and
names what narrows episodes instead.

## Points no longer carry a copy of their own vector

Points written by this release keep their vector in one place. Copies written by earlier
versions stay where they are — that is your data, and removing it is your call.

`letapis doctor` knows the condition:

    letapis doctor --dry-run --only payload_carries_the_vector

It prints how many points carry a copy and writes nothing. Swap `--dry-run` for `--apply` to
remove them.

The cure takes out one payload key. Vectors are not recomputed, indexes are unchanged, search
results are the same before and after, and nothing is reindexed. It works in batches and stops
if the counts stop adding up. Interrupting is safe: whatever is left is still there next run.

Both halves read the whole collection — the key is not indexed, and indexing it would keep in
memory the thing you are removing. On 50 000 points the dry run takes under half a second and
the cure about ten.

If you do nothing, nothing breaks. The copies keep taking up memory, and they stop growing.
