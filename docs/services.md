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
  - conf: ~/.config/letapis-app/services/docker.yaml
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
| `health` | how the lamp is lit. `http` — a GET returning 2xx. `command` — a shell command exiting 0 (this is how the Docker daemon is checked). `letapis` — the same 2xx rule, but the reply is also read as an engine health payload, which is where the version and update lines on the engine row come from |
| `start` | the command the Start button runs. Absent → no Start button |
| `stop` | `port` kills whatever process tree is listening there; `docker` runs `docker stop`. Absent → no Stop button |
| `logs` | what the Logs button opens: a file in Console, or `docker logs` in a terminal |
| `config.file` | what the pencil button opens |
| `config.params` | key/value pairs handed to the start command as environment, upper-cased and prefixed: `port: '8086'` arrives as `LETAPIS_SVC_PORT=8086` |

**The panel does not interpret `params`.** It passes them through; the script decides what a
key means and which flag it becomes, so changing a model runtime is an edit to a `.sh` file,
never to the panel.

Two more fields appear only on the engine card:

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
| Qdrant | 6333 REST, 6334 gRPC | all interfaces (Docker publishes them) |
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
