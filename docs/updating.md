# Updating, rolling back, uninstalling

**Two programs update themselves; the panel supervises one of them.** The panel replaces its own
`.app` from its own channel. The engine replaces its own installed copy — on a Mac that is the
whole `letapis.app` directory, not a single file — downloading, checking and installing it
exactly as it does on a Linux server where no panel exists. The panel's part is to ask
it to, and then to restart it, which is the one thing a running program cannot do for itself.

The panel therefore knows **one** address, its own, and **it is inside the program**. A released
panel carries the address it updates from; there is no file to edit, nothing to point elsewhere,
and nothing on your disk that decides where your panel looks. Moving the channel is done by
publishing a new build, which is the only way that reaches everybody.

That is deliberate, and the reason is worth one sentence: an address kept in a config file is
written once and never rewritten, so it would outlive every later decision: a panel installed
today would still be asking yesterday's address years from now, and nobody could change it.

**The engine does not carry an address either.** It asks the licence service where its channel
is and what that channel holds, so there is nothing on your disk, and nothing in its environment,
that points it anywhere. Neither program can be aimed at a different channel by editing something
on this machine. That is the whole design, not a limitation of it.

> **Building the panel yourself?** A build made from source carries no address, and says so
> instead of guessing: the Update button reports *Panel update channel is not configured*. Give
> it one by writing `~/.config/letapis-app/update.yaml` — the panel reads that file only when it
> was built without a channel of its own:
>
> ```yaml
> panel_manifest_url: https://github.com/letapis-ai/letapis-panel/releases/latest/download/latest.json
> ```
>
> The whole manifest URL goes in, not a base to build one from — different hosts spell that
> address differently.

## Updating

What changed in the version you are moving to is in
[release-notes.md](release-notes.md). Read it before updating, in case it asks
something of you.

One button, **Update**, in the panel's toolbar. It asks both — the engine's channel through the
engine, its own directly — and installs what is stale: the engine first, then the panel.

While it runs, the service controls are locked and the panel says why. One owner at a time: a
Start pressed underneath the update would be a second hand on the same service.

**The panel** replaces itself and relaunches. Nothing to do.

**The engine** is replaced in two steps, and you are told between them:

1. The engine downloads the new build, verifies it, and installs it **beside** the one that is
   running — **while it keeps serving.** It keeps two slots and always writes into the free one,
   then points its entry link at the new slot. The running process is untouched: it goes on
   serving from the slot it started in until it stops. Nothing is interrupted in this step, and
   it is the long one (tens of megabytes; minutes on a slow link, with no progress bar — the
   engine does not report one).
2. The panel says *Engine updated — restarting it now*, restarts the engine's card, and waits
   for the new build to answer. This is the only moment the engine is down.

Between the two you may briefly see the engine row read `26.811.1 (installed 26.811.2)` — the running
version and the one on disk, differing. That is not a fault; it is the state the two steps
create, said out loud.

**The check is honest about what it could not do.** Under the engine row you will see *update:
not checked* until something asks, and *update: could not check* if the channel was unreachable.
"Up to date" is only ever printed for an answer actually received.

## When an engine update fails

**Whatever went wrong, you are reading the engine's own words.** The panel does not translate
them: it is the engine that knows whether the channel was unreachable, the licence expired or a
checksum failed, and a second account of the same event would only be a worse one.

Failures separate into the two steps above:

| What you read | What actually happened |
|---|---|
| `letapis update: manifest fetch failed: …` | the engine could not reach its channel. Nothing was downloaded, nothing changed |
| `letapis update: sha256 mismatch …` | what arrived was not what the channel promised. Refused before anything was replaced |
| a block beginning `letapis cannot start:` | the engine refused for licence or configuration reasons. Nothing was replaced |
| `could not run the engine at …` | the engine could not be started to do the work at all — a different thing from an update that failed. Nothing was attempted |
| `the engine on disk is X — NOT restarted: … holds :3131` | the files are updated, but the port is held by something that is not ours, so nothing was signalled. Start the row when you want it |
| `core updated to X` | done, and the new engine is serving |

**If the new build will not come up, it is rolled back for you.** There is no rollback button,
and that is not an omission: the panel stops what it started, asks the engine to restore the
previous version (`letapis update --rollback`), starts it again, and confirms *it* answers
before saying anything:

| What you read | What actually happened |
|---|---|
| `the new engine did not come up — rolled back to X, which is serving again` | you are back where you started |
| `the new engine did not come up AND the restored X did not come back` | both failed. Start the row by hand and read its log |
| `the new engine did not come up, AND the rollback to X was refused: …` | the engine would not restore it; its reason is quoted |

**Going back deliberately** — as opposed to recovering from a failed update — is an operation of
the engine itself:

```bash
letapis update --list-versions        # what is in the two slots
letapis update --rollback             # go back to the other slot
letapis update --rollback 26.811.1      # the same, refusing unless that is what is there
```

**There is one step back, not a history.** The engine keeps two slots, so going back means
pointing the entry link at the other one. The version after `--rollback` is not a choice from a
list — it is what you *expect* to find in the other slot, and the engine refuses rather than
switch to something else. Restart the row from the panel afterwards; the engine never restarts
itself.

**Installing an engine for the first time is not something the button does.** It updates an
engine that is already there — there has to be one to ask. First installation is
[ONBOARDING.md § 6](../ONBOARDING.md#6-the-engine).

## Updating the panel by hand

You do not have to use the button. The panel is an ordinary macOS app: download a newer `.dmg`
from [Releases](https://github.com/letapis-ai/letapis-panel/releases), quit the panel from its menu-bar menu, and replace the app in
`/Applications`.

Your configuration is untouched by this — it lives in `~/.config/letapis-app/`, not inside the
app.

## Uninstalling

Nothing is installed outside your home directory and `/Applications`, and nothing runs as a
system service. Removing it is removing files, in this order:

```bash
# 1. Quit the panel from its menu-bar menu, and stop what it was supervising.
docker stop letapis-qdrant

# 2. The app.
rm -rf /Applications/letapis-app-rs.app

# 3. The panel's configuration — service cards, launch scripts, update channels.
rm -rf ~/.config/letapis-app

# 4. The engine and its configuration.
rm -rf ~/.local/letapis-core ~/.config/letapis

# 5. The models, if you want the disk back.
rm -f ~/models/harrier-oss-v1-0.6b-Q8_0.gguf ~/models/Qwen3-Reranker-0.6B.Q8_0.gguf
```

**The index is separate, and outlives all of the above.** It lives in a Docker volume:

```bash
docker rm letapis-qdrant                       # the container — harmless, rebuilt on demand
docker volume rm letapis_qdrant_storage        # the index itself — NOT recoverable
```

Remove the volume only when you mean to lose everything the engine indexed. Re-indexing a large
corpus is measured in hours.

**Reinstalling** is this page's opposite read backwards, with one shortcut: if you kept
`~/.config/letapis-app/` and the Docker volume, a fresh panel picks up your existing cards and
your existing index, and the stack comes up where it left off. If you are moving to a new
machine, the new one has to be logged in on its own — see [licence.md](licence.md). Do not carry
the engine's data directory across: both machines would work until the licence string is renewed,
and then one of them stops, unpredictably.
