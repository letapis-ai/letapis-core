# Installing the engine

**This page picks up where the panel's installation leaves off.** It assumes the machine already
has the panel, Docker and Qdrant, and the two model servers — all of that is the panel's half,
and it is written up in [the panel's install guide](https://github.com/letapis-ai/letapis-panel/blob/main/docs/install.md). If you have not done it
yet, do that first: the engine expects those services to be there.

Two steps here: put the engine where the panel starts it from, and log the machine in. When both
are done, go back to the panel's guide for
[step 8, confirming the whole stack](https://github.com/letapis-ai/letapis-panel/blob/main/docs/install.md#8-confirm-the-whole-stack) — that is where
you find out whether everything talks to everything.

## 1. Put the engine in place

The engine is the licensed part, and it is not in this repository. **You receive it from the
owner** — as a `.dmg` for macOS, together with your licence key. There is no public download and
no package to install from.

It goes here, and the layout is the engine's own:

```
~/.local/letapis-core/
├── ota_0/letapis.app/          the version you install now
├── ota_1/                      empty until the first update fills it
└── letapis-current -> ota_0/letapis.app     the entry point, a link
```

There are two slots, and an update always fills whichever one is free — so after your first
update this link points at `ota_1`, after the next one at `ota_0` again. Which slot is current is
never something you need to know: the link is the answer.

The panel starts the engine **through the link**, never through a slot directly:

```
~/.local/letapis-core/letapis-current/Contents/MacOS/letapis
```

That is the whole reason the link exists — the panel keeps one fixed path and never has to know
which version is current, and an update is a single rename of the link.

**Putting it there — three commands.** Open the `.dmg` you were given; it mounts as a disk named
`letapis-core` with `letapis.app` inside. There is no installer on purpose: you can see exactly
what is about to happen on your machine, and if something goes wrong you know which of the three
steps to look at.

```bash
mkdir -p ~/.local/letapis-core/ota_0
ditto /Volumes/letapis-core/letapis.app ~/.local/letapis-core/ota_0/letapis.app
ln -sfn ~/.local/letapis-core/ota_0/letapis.app ~/.local/letapis-core/letapis-current
```

The app is **copied out of the image**, not dragged: `ditto` brings its signature and metadata
across intact. Check it arrived by asking it its version — this also runs it through the link,
which is the path the panel will use:

```bash
~/.local/letapis-core/letapis-current/Contents/MacOS/letapis --version
```

Then eject the disk. If Finder shows the disk under a different name — `letapis-core 1`, say,
because something of that name is already mounted — use the name it actually shows in the second
command.

The panel identifies the engine by *where the running executable lives*, not by its name, so a
copy left somewhere else will start and the panel will not recognise it as the service it
manages. Keep it under that directory.

### The engine's configuration

The engine reads its own configuration from `~/.config/letapis/config.yaml` — note that this
is `letapis`, not `letapis-app`; the engine's configuration is deliberately outside the
panel's directory.

**You do not have to write this file — the panel already did**, at the same first launch that
created the service cards in step 3. It carries the addresses of the very services those cards
start:

```yaml
server:
  host: localhost
  port: 3131

qdrant:
  url: http://localhost:6333

embeddings:
  provider: openai
  api_url: http://localhost:12436
  model: harrier-0.6b

reranker:
  url: http://localhost:8086
  model: qwen3-reranker-0.6b
```

The panel writes it **only when it is not there**, and never touches it again — edit it freely.
Every line earns its place, and the engine's own defaults are why: left to them it would look for
embeddings at `localhost:11434` — an Ollama you never installed — and would listen on `3100`
while the panel probes `3131`, keeping the row red on a stack that is otherwise fine.

If the file is missing — you moved it, or you are setting the engine up by hand — the engine says
so plainly on start: `no config file was found on this machine`. Put the block above in
`~/.config/letapis/config.yaml` and it will start. The addresses are the two models and
Qdrant you started in steps 4 and 5; `data_dir` is where the engine keeps what it learns.

There is more the engine can be told — search behaviour, indexing, API keys — and none of it is
needed to start. Leave it out until you have a reason.

**Do not press Start yet.** An engine that has never been logged in refuses to start, and the row
would go red for a reason that is not a fault. Log in first — the next step — and press Start
after it.

When you do: the engine listens on **3131**, the panel probes
`http://localhost:3131/api/v1/health`, and its log is `/tmp/letapis-core.log`.

## 2. Activate the licence

Until this machine has been logged in, the engine refuses to start — so this step comes before a
green lamp, not after one.

Press the **key button** on the engine's row. The window that opens prints the address of our
login page; open it in a browser, type your **licence key** and the **email the licence was
issued to**, and it answers with a string beginning `lt_`. Paste that string back into the
window.

Your key and your email stay in the browser — they are never written to this machine.

When the window says the machine is licensed, press **Start** on the engine row. The lamp turns
green when the engine answers its health address — that is the first moment a green lamp here
means anything.

The details, the command-line equivalent and what each refusal means are in
[licence.md](licence.md).


---

**Both steps done?** Back to the panel's guide for
[step 8 — confirm the whole stack](https://github.com/letapis-ai/letapis-panel/blob/main/docs/install.md#8-confirm-the-whole-stack): five rows green,
five checks by hand. If a row stays red, the panel's [panel.md](https://github.com/letapis-ai/letapis-panel/blob/main/docs/panel.md) explains every
state it can show.
