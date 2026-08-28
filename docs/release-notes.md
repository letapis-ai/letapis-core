# Release notes

**Upgrading from a version earlier than 26.822.1: run `force_reindex` on every watched
folder after installing.** A folder indexed by an older engine keeps answering from the old
cut until you do. From 26.822.1 and later no reindex is needed.

**Check your config against the one in the kit.** Keys get added and renamed between
versions. A key the engine does not recognise is dropped without a word, so a setting that
was renamed simply stops having an effect. Diff your `config.yaml` against the one shipped
at the top of the kit, beside `run.sh`, and carry over what is new.

## 26.828.1

### Work on a branch in a copy of the tree

A copy of a repository can now be indexed without appearing in anyone else's answers. Register
it as a watched folder with `hidden: true` and `supersedes: "<the watched trunk>"`; name it in
`reveal` on each call and you get your copy, while the trunk it stands in for drops out of that
one answer. Everybody else keeps getting the trunk.

The full procedure — registering, asking, catching up, retiring the copy — is in the skill room
`skills/letapis/references/worktree.md`.

### Cleanup judges a file by the folder that owns it

`cleanup_orphaned_files` used to judge a file by the first watched folder whose path was a
prefix of its own. Where watched folders nest, the inner folder's rules never applied, and its
files were swept by the outer folder's rules instead. The owning folder is now the one that
decides, and both `index_folder` and `update_folder` judge the pair of marks the same way.

### Narrowing the cleanup to one folder now works

`cleanup_orphaned_files` declares a `path`. The parameter did not reach the handler, so a call
that narrowed the sweep to one folder swept the whole store — successfully, and without saying
so. If you have been avoiding the tool for that reason, it now does what it offers.

The same defect is closed on `get_indexing_progress.scope_id`, which asked about a research
scope and answered about everything.

### The visibility note answers one question per key

`visibility.hidden_folders` carried two different meanings depending on whether `reveal` was
used. It now means one thing — hidden folders kept out of this answer — and the trunk your copy
stood in for is reported separately as `superseded_by_reveal`, present only when a substitution
happened.

### Refusals that used to be silence

`supersedes` naming a tree nobody watches, or naming it from a folder whose watch is stopped, is
refused by name (`supersedes_unwatched`, `supersedes_from_inactive`) instead of being accepted
with a substitution that does nothing.

`ena_correct_fact` now declares `context`, which its handler always read. `get_knowledge_graph`
no longer offers `depth`: nothing read it, and a multi-hop walk is not implemented.

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
