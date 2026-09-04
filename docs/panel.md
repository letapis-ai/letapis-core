# Reading the panel

One row per service, a lamp on the left, buttons on the right, and — when there is something
worth saying — a line or two of small text under the name. This page is what all of it means.

## The lamp

| Colour | State | Says |
|---|---|---|
| green | **healthy** | the service answered its health check |
| red | **unhealthy** | it was asked and did not answer |
| grey | **unknown** | it has not been asked yet, or the answer cannot be trusted (see below) |

Grey before the first check has run is normal — it lasts a second or two after the panel opens.

Grey that *stays* means something more specific: the service answered, but **the process
answering is not the one this row manages**. The panel refuses to paint that green, because a
green lamp on somebody else's process is the most expensive lie a supervisor can tell — you
would restart, update or debug the wrong thing. When this happens, the note under the row names
the occupant.

Hovering the lamp shows the reason in a tooltip.

## The lines under a service name

Most rows show only their name. The extra lines appear when the panel has something to warn you
about, or when the row is an engine.

### Ownership

| Note | What happened | What to do |
|---|---|---|
| *held by the other engine* | another card in your stack listens on this port | stop that card first; two services cannot share a port |
| *held by another process (pid N)* | something outside this stack has the port | find out what it is (`lsof -nP -iTCP:<port> -sTCP:LISTEN`) and stop it yourself — the panel will not kill a process it did not start |
| *N listeners (…) — ambiguous* | more than one process is listening | the panel will not guess which is the service; the pids are listed so you can sort it out by hand |
| *identity by name (add owner_exe_roots)* | this card recognises its process only by name, which a stray copy also matches | add `owner_exe_roots` to the card — see [services.md](services.md) |

In the middle three cases the row's Stop and Restart buttons are gone. That is deliberate:
those buttons act on *this card's* process, and the panel has just told you the process on the
port is not it.

**Not every row is checked this way, and it is worth knowing which.** The check needs the card to
say where its program is installed, which the engine's and Qdrant's cards do. The embedder and
the reranker run `llama-server` out of your `PATH`, so their rows go green for whoever holds
12436 or 8086 — and a card that runs a container is outside the check by construction, because
the port is held by the runtime rather than by the program inside it
([services.md](services.md)).

On a row that is not checked, a green lamp means *something answers at that address*. If a
service refuses to start while its row stays green, read its log: the start script says what
went wrong, and `Address already in use` is what a port taken by someone else looks like.

### Version, on the engine row

| Shows | Means |
|---|---|
| `26.811.1` | the running engine reports this version |
| `26.811.1 (installed 26.811.2)` | a newer engine is on disk but the old one is still serving — restart the row to pick it up |
| `version unknown` | it is serving, but it is too old to report a version. The panel will not fill the gap with a number read off the disk |
| `checking…` | the install directory has not been read yet |
| `not installed` | there is no engine binary at the install path |
| `install unreadable` | there is a binary, and it would not answer |

### The update channel

| Shows | Means |
|---|---|
| *update: not checked* | nobody has asked the channel yet |
| *up to date · \<time\>* | asked, and the answer was no new version |
| *update: 26.811.2 available · \<time\>* | asked, and there is one |
| *update: could not check* | the channel could not be reached — see [updating.md](updating.md) |

"Up to date" is only ever shown for an answer actually received. An unreachable channel says so.

## The buttons

Buttons appear on a row only when they can do something, and reveal themselves as you move over
the row.

| Button | Does | Absent when |
|---|---|---|
| ▶ **Start** | runs the card's start command | the service is healthy, or has no start command |
| ■ **Stop** | stops this card's process | the card has no stop strategy, or — on a checked row — the port is held by someone else |
| ↻ **Restart** | stop, pause, start | the card cannot do both halves |
| **Logs** | opens the service's log | the card declares no log |
| ✎ **Edit config** | opens the file the card points at | the card points at no file |

A Start that would collide with a port already in use is refused before it is attempted, and the
message names the occupant.

**On a row that is not checked, Stop means "kill what is listening on that port".** It has no way
to tell your service from a stranger that took the port, so it stops whichever it finds. Which
rows those are, and why: the note under [When everything is red](#when-everything-is-red).

## Row notes during an action

| Note | Means |
|---|---|
| *Working… Ns* | the action is in flight; the counter is elapsed time, not a promise |
| *Not confirmed* | the action was sent, and the result did not prove out in the time allowed. **Not** the same as failed — a Stop that worked leaves a red lamp, and a Stop that never confirmed leaves a green one |

## The toolbar

| Control | Does |
|---|---|
| **Autostart** | arms two things at once: the panel relaunches at login, and it starts the whole stack when it launches |
| ✎ | opens the configuration folder |
| ↻ | re-reads the configuration from disk and refreshes health — this is what to press after editing a card |
| **Update** | checks both channels and installs what is there ([updating.md](updating.md)) |

While an engine update runs, the service controls are locked and the panel says so. One owner
at a time.

## When everything is red

Work from the bottom of the stack up — each service depends on the ones started before it:

1. **Qdrant** red → open the row's log. The script says which file it could not find: the
   binary, if the archive was never unpacked into `~/.local/letapis-qdrant/bin/`, or the
   configuration beside it.

   A *green* Qdrant row is worth one caveat: the lamp asks 6333 and believes whoever answers.
   If something else on the machine was already holding that port, the row is green about a
   program that is not yours, and `/tmp/letapis-qdrant.log` ends with `Address already in use`.
2. **Embedder / Reranker** red → open the row's log. The scripts fail loudly and name the cause
   ([models.md](models.md)).
3. **letapis-core** red → open `/tmp/letapis-core.log`. The engine is the only piece that can
   also be *alive but not licensed*: that is a green lamp with work refused, and it belongs to
   [licence.md](licence.md), not here.
