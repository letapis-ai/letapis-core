# Services and their cards

Everything the panel knows about your machine is data, not code. It reads one index file and
one card per service, and it never learns what any of it means. That is why you can change a
port, move a model, or add a service the panel has never heard of, without a new build.

## The layout

```
~/.config/letapis-app/
├── services.yaml            the index: start order + the autostart switch
└── services/
    ├── qdrant.yaml          one card per service
    ├── embedder.yaml
    ├── embedder.sh          the script a card's start line invokes
    └── …
```

The index is a list of pointers, in **start order**: the panel starts from the top down, so
the database comes before the models and the models before the engine:

```yaml
autostart:
  boot_stack: true
services:
  - conf: ~/.config/letapis-app/services/qdrant.yaml
  - conf: ~/.config/letapis-app/services/embedder.yaml
  - conf: ~/.config/letapis-app/services/reranker.yaml
  - conf: ~/.config/letapis-app/services/letapis-bin.yaml
```

`boot_stack` is the second half of the panel's **Autostart** switch; the first half is the
login item. The switch arms and disarms both together, so it never leaves you half-armed.

## A card, field by field

```yaml
id: reranker                                   # unique, internal
name: Reranker                                 # what the row is called
health:
  kind: http                                   # http | command | letapis
  url: http://127.0.0.1:8086/health
start: nohup bash ~/.config/letapis-app/services/reranker.sh &
restart_policy: manual                         # manual | unmanaged
stop:
  kind: port                                   # port | docker
  port: 8086
logs:
  kind: file                                   # file | docker
  path: /tmp/letapis-reranker.log
config:
  file: ~/.config/letapis-app/services/reranker.yaml
  params:
    engine: llama-cpp
    model: ~/models/Qwen3-Reranker-0.6B.Q8_0.gguf
    alias: qwen3-reranker-0.6b
    port: '8086'
    host: 127.0.0.1
    ctx: '4096'
```

| Field | What it decides |
|---|---|
| `health` | how the lamp is lit. `http` — a GET returning 2xx. `command` — a shell command exiting 0 (this is how a container runtime is checked). `letapis` — the same 2xx rule, but the reply is also read as an engine health payload, which is where the version and update lines on the engine row come from |
| `start` | the command the Start button runs. Absent → no Start button |
| `stop` | `port` kills whatever process tree is listening there; `docker` stops a container. Absent → no Stop button |
| `logs` | what the Logs button opens: a file in Console, or the container's log in a terminal |
| `requires_runtime` | the card is shown only when that container runtime is on the machine. `docker`, `podman`, or `any` for a card that works with whichever one is present. Absent → the card is always shown |
| `config.file` | what the pencil button opens |
| `config.params` | key/value pairs handed to the start command as environment, upper-cased and prefixed: `port: '8086'` arrives as `LETAPIS_SVC_PORT=8086` |

## Cards that run a container

Qdrant runs as an ordinary program by default, and no card in the list needs a container runtime.
Three cards that do are written into `services/` all the same, with nothing pointing at them:
`qdrant-docker.yaml`, `docker.yaml` and `podman.yaml`. Putting one in the list is how you turn
that path on — [ONBOARDING.md](../ONBOARDING.md) walks both directions.

A card that runs a container does not name the runtime itself. It writes `{{runtime}}`, and the
panel substitutes whichever runtime it found — either one works, and a machine with both gets the
one the panel prefers:

```yaml
id: qdrant
name: Qdrant
requires_runtime: any                          # docker | podman | any
health:
  kind: http
  url: http://127.0.0.1:6333/healthz
start: '{{runtime}} start letapis-qdrant || {{runtime}} run -d --name letapis-qdrant …'
stop:
  kind: container
  container: letapis-qdrant
  runtime: '{{runtime}}'                       # the marker belongs here too
logs:
  kind: container
  container: letapis-qdrant
  runtime: '{{runtime}}'
```

**The marker has to be in every place the runtime is named**, `stop` and `logs` included. A card
that writes `{{runtime}}` in its start line and a fixed runtime in `stop` starts under either
engine and then refuses to stop under one of them.

`kind: docker` is the older spelling, still read so that a file written before Podman was
supported goes on working. It is not the same as `kind: container`: it means docker
specifically, and it takes no `runtime` field. On a machine with only Podman a card written that
way starts fine and cannot be stopped, because Stop runs `docker` and there is no docker. Writing
a container card today, use `kind: container` with the marker.

Podman on macOS has no daemon that runs all the time. Its work is done by a virtual machine,
which has to be running before containers will start, and the Podman card starts that machine
(`podman machine start`) when you press Start.

A card whose runtime is not installed is not shown at all, and it does not turn the menu-bar icon
red — an absent runtime is not a broken service. That is what keeps a container card harmless on
a machine with no runtime: put `qdrant-docker.yaml` in the list without Docker or Podman
installed, and the row simply is not there. The cards you already have are never rewritten.

**The panel does not interpret `params`.** It passes them through; the script decides what a
key means and which flag it becomes, so changing a model runtime is an edit to a `.sh` file,
never to the panel.

Two more fields appear on the cards that can tell their own process apart — the engine's and
Qdrant's:

| Field | What it decides |
|---|---|
| `owner_hint` | a label only — a fallback process name, used when a card declares no `owner_exe_roots` |
| `owner_exe_roots` | the directories a process must be running from to count as *this card's* process |

**Which row is an engine is not decided by that label.** It is decided by the card's `health:
kind: letapis` probe, and whether a row shows the version lying on disk is decided by its
`start:` line: the card that launches the engine executable is the card that has an install
directory. Both answers come from the panel's backend; neither reads a name.

`owner_exe_roots` is the identity check, and it is stricter than a name on purpose: a stray
copy of the engine binary launched from somewhere else has the same process name, and killing
it because the name matched would be a coin flip. See [panel.md](panel.md) for what the panel
shows when the port is held by something it does not recognise.

**Which cards have the check, and which cannot.** A card can name install roots when the program
it starts lives somewhere the card itself decides. That is true of the engine and of Qdrant —
both are unpacked into a directory the card names. It is not true of the embedder and the
reranker: they run `llama-server`, which comes from your `PATH`, and the kit cannot know whether
that is Homebrew's copy, a build of your own, or something else. Those two rows still light from
the port alone, so a stranger holding 12436 or 8086 lights them.

If you pinned `llama-server` with a `bin:` parameter (below), you know where it lives and can add
`owner_exe_roots` to match. The two model cards would then need different roots — two cards
claiming the same tree is a configuration the panel warns about, because a process could be
attributed to either.

**A card that runs a container is outside this check entirely.** The port is held by the
container runtime's own process, not by the program inside it, so the panel cannot say whether
what answers is yours. That is a property of containers, not a gap to be filled: the container
Qdrant card lights from the port, as every card did before this check existed.

## Common changes

**Move a model, or use different weights.** Edit `model:` in the card. The pencil button on the
row opens the right file.

```yaml
config:
  params:
    model: /Volumes/big-disk/models/my-reranker.gguf
```

**Change a port.** It appears in three places in one card — `health.url`, `stop.port` and
`config.params.port` — and all three must agree. The first is how the panel checks the service,
the second is how it stops it, the third is what the service actually binds. Change one and you
get a service running somewhere the panel is not looking.

**Point at a runtime outside `PATH`.** Add a `bin:` parameter with the full path to
`llama-server`.

**Add a service of your own.** Write a card, put it in `services/`, and add a `conf:` line to
`services.yaml` in the position you want it started. Nothing else is needed: the panel has no
list of known services.

**Remove one.** Delete its line from `services.yaml`. The card file can stay; nothing reads it.

## After editing

Press **↻** in the panel. It re-reads the configuration, not just the health: added, removed
and edited services all appear. Services that are already running are left alone; this only
re-reads data.

If a file has a syntax error the panel says so rather than starting with half a stack.

## Ports, all together

| Service | Port | Bound to |
|---|---|---|
| Qdrant | 6333 REST, 6334 gRPC | whatever its own config binds — `~/.local/letapis-qdrant/config.yaml` |
| Embedder | 12436 | `127.0.0.1` — the card's `host` |
| Reranker | 8086 | `127.0.0.1` — the card's `host` |
| letapis-core | 3131 | whatever its own configuration says |

Both model servers listen on the loopback address by default. That is the `host` value in
each card's `config.params`, which reaches the script as `LETAPIS_SVC_HOST` and becomes the
server's `--host`. Nothing in this stack needs them to be reachable from your network, so
change it only if something outside this machine has to call them; anything other than a
loopback address exposes the model server to whatever can route to you. The engine's bind
address is not the panel's to set: it comes from `server.host` in
`~/.config/letapis/config.yaml`, the file the panel writes at first launch —
[ONBOARDING.md § 3](../ONBOARDING.md#3-what-the-first-launch-made-for-you) describes it.
