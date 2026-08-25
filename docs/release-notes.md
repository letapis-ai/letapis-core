# Release notes

**Upgrading from a version earlier than 26.822.1: run `force_reindex` on every watched
folder after installing.** A folder indexed by an older engine keeps answering from the old
cut until you do. From 26.822.1 and later no reindex is needed.

**Check your config against the one in the kit.** Keys get added and renamed between
versions. A key the engine does not recognise is dropped without a word, so a setting that
was renamed simply stops having an effect. Diff your `config.yaml` against the one shipped
at the top of the kit, beside `run.sh`, and carry over what is new.

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
