# Release notes

**Upgrading from a version earlier than 26.822.1: run `force_reindex` on every watched
folder after installing.** A folder indexed by an older engine keeps answering from the old
cut until you do. From 26.822.1 and later no reindex is needed.

**Check your config against the one in the kit.** Keys get added and renamed between
versions. A key the engine does not recognise is dropped without a word, so a setting that
was renamed simply stops having an effect. Diff your `config.yaml` against the one shipped
at the top of the kit, beside `run.sh`, and carry over what is new.

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
