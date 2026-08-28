# Working in a copy of a tree

You want to work on a branch without your teammates, or your own other sessions, running into
half-finished code in their answers. A copy of the repository gives you that isolation. The engine
can index the copy like any other folder, so search and the call graph still see what you are
doing.

Those two things used to be in tension. They are reconciled by visibility rather than versioning:
the index stays flat, two states of the same code live as two watched folders, and which one
answers is decided per call.

## The shape of it

A copy is registered as an ordinary watched folder. It is walked, parsed and embedded exactly like
its neighbour. One mark makes it different: it is hidden, so it answers nobody who did not ask for
it by name. When you name it in `reveal`, that same act drops the trunk from your answer, so two
states of one file never arrive together.

None of this is remembered between calls. A call that does not name the copy gets the trunk. That
is the default, and it is what everyone else keeps getting.

## Registering the copy

```
index_folder(path="<copy>",
             file_patterns=["*.py", "*.md"],
             hidden=true,
             supersedes="<the watched trunk>")
```

The call hands back an `operation_id` and the pass runs in the background. `get_operation` says
when it has finished.

`supersedes` takes the path of a *watched* tree, not the tree your copy was made from. Those are
the same only when the clone you branched off is the one being indexed, and several clones of one
repository on a machine is an ordinary setup with usually one of them watched. Name an unwatched
path and the call is refused by name: `supersedes_unwatched`, nothing written, and the message
tells you to index that tree or name the one that is watched. Read the path out of `list_folders`
rather than typing the one you are standing in, and the refusal will not come up at all.

`supersedes` also closes exactly one path: the one you named. If the same tree is watched a second
time, by a folder nested inside it for instance, that second record is untouched and its files
arrive alongside your copy. Look at how many watches cover your trunk before you rely on the
substitution.

Both marks sit on the watch root and cover the tree below it. A watched folder nested inside
answers for itself.

## Checking the marks landed

```
list_folders(folder="<copy>")
```

Name a folder and you get its whole record. Leave it out and you get a short listing that marks
which folders are hidden and what each of them supersedes. A mark the folder never declared is
missing from the record entirely, so an absent key is not a measured `false`.

The call is worth making. Indexing runs in the background, and a copy registered without `hidden`
starts answering everyone straight away, mixing your unfinished work into their results.
`update_folder(path="<copy>", hidden=true)` fixes the folder. It cannot recall the answers already
given.

## Asking while you work

```
search(query="…", reveal=["<copy>"])
blast_radius(symbol="…", reveal=["<copy>"], folder="<copy>")
```

Omit `reveal` and you get the trunk. Not an error, not an empty result: a plausible answer about
the older state of your code. This is how the arrangement fails, and the results themselves will
not tell you — but the answer will, if you look at the right field. `visibility.revealed` is
empty when you named nothing, and `visibility.hidden_folders` then lists your copy among the
folders kept out. That is the whole check, and it costs one glance.

`reveal` admits the copy. It does not narrow the answer down to it. `blast_radius` has its own
`folder` for that, and without it you get callers from the whole corpus in one list, other
repositories included. Plausible again, and about something other than your tree.

Every call names the copy for itself. Revealing is not remembered and is not shared.

Under `visibility` the answer says what it did, and each key answers one question:
`applied` — whether anything was kept out at all; `revealed` — what you asked for;
`hidden_folders` — hidden folders kept out of this answer; `superseded_by_reveal` — the trunk
your copy stood in for, present only when a substitution actually happened.

The last two are apart because you act on them differently. A folder in `hidden_folders` is
opened by naming it in `reveal`. A tree in `superseded_by_reveal` was never closed to you: it
left because this very call asked for its copy instead, and it comes back the moment you stop
revealing.

## Catching up with the trunk

Merge the trunk into the copy the way you normally would. The watcher picks the changed files up
on its own, the folder needs no re-registering, and the merge disturbs neither mark.

## Retiring the copy

```
remove_folder(path="<copy>")
```

One call does it. Everything the filesystem produced goes: files, their chunks, the structures
parsed out of them. Records whose text lives in the record itself stay, because a dead source is
not a dead carrier, so episodes and findings are counted and left alone. Files on disk are not
touched. The call has no way back; when you want something reversible, `forget_folder` hides
rather than deletes.

Then remove the working tree. Two things catch people out. Removal refuses while modified or
untracked files are still there, and in a copy anyone has worked in they nearly always are,
starting with its virtual environment; forcing it takes the directory down with everything unsaved
inside. And the branch outlives the working tree. Deleting one does not delete the other.

## What the copy does not buy you

It isolates the tree, not the work. Narrow tests for your own change run inside it, but the checks
that catch damage to a neighbouring mechanism live in the common suite, and those you have not
run. The full run on the branch is still owed before anything merges.

## What it costs

Measured on a trial corpus of roughly six thousand nodes per tree.

| Item | Cost |
|---|---|
| the copy on disk | 8.3 MB, since it shares the repository's object store |
| its environment after the first run | 330 MB, 9.1 s |
| indexing the trunk | 20.8 s |
| indexing a copy | about 24.2 s, some 16 % more, with both running at once |
| nodes | three trees, three times the nodes; identical trees are not deduplicated |

A live copy earns its pass. Without one the engine would not see the change you made the copy for.
The expensive part is the environment, not the tree.

## Refusals you will meet

| Refusal | What it means |
|---|---|
| `supersedes` refused by name | only a hidden folder may declare one, never itself, never a relative path, and never a tree nobody watches |
| `supersedes_from_inactive` | watching this copy is stopped, so nothing reveals it and nothing can be substituted. Start watching it again — `index_folder` on the folder reactivates it — and set the pair then |
| settings refused while a pass is running | a long pass is reading this folder's settings; stop it, change them, start again |
| `unknown_settings` | a name this surface does not read. Nothing was written, and the answer lists what it does read |
| empty `results` with a `hint` | the answer outgrew the limit and was spilled to a file. Read it with `fetch_file` rather than reading the emptiness as "nothing found" |
