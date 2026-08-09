# Rolling the engine back

The engine updates itself — `letapis update` downloads, checks and installs, the same way it does
on a Linux server where no panel exists. **The panel's Update button is a way of asking it to**,
and everything about that button, including what its refusals mean and how a failed update
recovers on its own, is written up in the panel's
[updating.md](https://github.com/letapis-ai/letapis-panel/blob/main/docs/updating.md). This page is the engine's own command line.

**Going back deliberately** — as opposed to recovering from a failed update — is an operation of
the engine itself:

```bash
letapis update --list-versions        # what is in the two slots
letapis update --rollback             # go back to the other slot
letapis update --rollback 0.1.11      # the same, refusing unless that is what is there
```

**There is one step back, not a history.** The engine keeps two slots, so going back means
pointing the entry link at the other one. The version after `--rollback` is not a choice from a
list — it is what you *expect* to find in the other slot, and the engine refuses rather than
switch to something else. Restart the row from the panel afterwards; the engine never restarts
itself.

**Installing an engine for the first time is not something the button does.** It updates an
engine that is already there — there has to be one to ask. First installation is
[install.md](install.md) on this page's own repository.
