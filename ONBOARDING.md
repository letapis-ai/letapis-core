# Setting up letapis, start to finish

One page, in order, with a box to tick at every step. Each step says **what you do**, **how you
know it worked**, and where the long version lives if something goes wrong.

Budget about an hour. Most of it is downloads; the parts that need you take a few minutes each.

The stack is five programs, and the panel starts all of them. Nothing here runs in the cloud:
everything is on your machine, and the only thing that ever leaves it is the licence check.

**How to read the commands on this page.** Anything in a black box is for you to paste into a
terminal — either to *do* something (download the models, unpack the engine) or to *check* that a
step worked. The only exceptions are marked **FYI** right above the box: those show what a button
in the panel does for you, so you can see it before you press it, or run it yourself if the button
stays silent. You never need to type an FYI box for the installation to succeed.

---

## Before you start

**From us, by hand — you cannot get these anywhere else:**

- [ ] a **download link for the engine kit** — it expires a few minutes after we make it, so ask
      when you are ready to install, not the day before;
- [ ] your **licence key** and the **email address it was issued to**. You will type both once,
      into a web page, and never again.

**Your machine:**

| | Requirement | Why |
|---|---|---|
| **OS** | macOS **13.0** or newer | the panel's minimum system version |
| **Chip** | Apple silicon | the models run on the GPU through Metal |
| **Memory** | **16 GB** or more | the two models together hold roughly 5.5 GB resident (see [models.md](docs/models.md)); the engine and Qdrant want their share on top |
| **Disk** | **~10 GB** to install, plus room for the index | Docker Desktop is ~4 GB of it, the two models ~1.2 GB, the Qdrant image ~300 MB. Already have Docker? Then 4 GB is enough to install the rest. The index grows under Qdrant as the engine feeds it — plan for that separately |
| **Docker Desktop** | installed | Qdrant runs as a container |
| **llama.cpp** | installed | both models run under its `llama-server` |
| **Homebrew** | installed | how llama.cpp gets onto the machine |

- [ ] a terminal you are willing to paste three commands into. There is no installer, on purpose:
      you see what happens on your machine, and when something goes wrong you know which step.

---

## 1. Two dependencies

The panel supervises Docker and the model servers; it does not install them.

- [ ] **Homebrew** — not part of macOS. If `brew --version` does not answer, install it from
      [brew.sh](https://brew.sh) and follow the "Next steps" it prints (on Apple silicon it asks
      you to put `/opt/homebrew/bin` on your `PATH`, and `brew` does not work until you do).
- [ ] **llama.cpp** — `brew install llama.cpp`
- [ ] **Docker Desktop** — download from [docker.com](https://www.docker.com/products/docker-desktop/)
      and open it once so it can finish its own setup. Installing it through Homebrew instead
      (`brew install --cask docker-desktop`) asks for your **admin password** partway through,
      to put its credential helper on the system path — expected, and it needs a terminal you
      can type into.

**Worked?**

```bash
brew --version && llama-server --version && docker info >/dev/null && echo "all three answer"
```

---

## 2. The panel

- [ ] Download `letapis-app-rs.dmg` from
      [the panel's Releases](https://github.com/letapis-ai/letapis-panel/releases) and open it.
- [ ] The window has two icons — the app and the `Applications` folder. Drag the first onto the
      second. It is signed and notarised, so macOS opens it without argument.
- [ ] Eject the disk image. Launch the app.

**Worked?** The panel lives in the **menu bar**, not the Dock — its icon is at the top right.
There is no window until you ask for one: click the icon, or pick **Show Panel**.

---

## 3. What the first launch made for you

You do not have to do anything here — read it, tick it, move on. The panel wrote two things and
will never touch either again:

- [ ] `~/.config/letapis-app/` — the five service cards it starts things from. **Yours** from now
      on: change a port or a path and the panel obeys ([services.md](docs/services.md));

  ```
  ~/.config/letapis-app/
  ├── services.yaml            the list of services, in start order
  └── services/
      ├── docker.yaml          one card per service…
      ├── qdrant.yaml
      ├── embedder.yaml
      ├── reranker.yaml
      ├── letapis-bin.yaml
      ├── embedder.sh          …and the two launch scripts
      └── reranker.sh
  ```

- [ ] `~/.config/letapis/config.yaml` — the **engine's** configuration, already pointing at the
      services you are about to start. Without it the engine refuses to start, and nothing else
      on the machine creates it.

**Want to see what a working machine actually runs?** [`config/default/`](config/default/) in
this repository holds the same files as they are on ours — both the cards and the engine's
config, with every value commented. What the panel writes is deliberately shorter: it fills in
what your machine needs and leaves the rest to the engine's own defaults.

Take them, take a few lines out of them, or ignore them entirely. They are a reference, not a
step: the panel already gave you a working set, launch flags included. The embedder's flags
matter more than they look — on stock defaults that server reserves memory for inputs sixty
times larger than ours and aborts under indexing load — and the panel writes them for you.
Nothing here needs copying.

> **Both are written on a first launch — one where `~/.config/letapis-app/` does not yet exist.**
> A panel that already has its cards leaves both files alone: they are yours, and it will not
> write over your edits. To start from scratch, remove `~/.config/letapis-app/` and
> `~/.config/letapis/` before launching — that throws away any service cards you had changed.

**Worked?** The panel window shows **five rows**, and all of them except Docker are red. That is
correct — nothing else is installed yet.

---

## 4. Qdrant

The database the engine keeps its index in. You do not create the container by hand.

- [ ] Make sure Docker Desktop is running (the Docker row is green).
- [ ] Press **Start** on the Qdrant row. The first Start creates the container and its storage
      volume; every later Start just starts it again.

**Worked?**

```bash
curl -s 127.0.0.1:6333/healthz          # healthz check passed
```

**FYI — you do not type this.** It is the whole of what **Start** does, no magic behind it. Run it
yourself only if the button stayed silent:

```bash
docker start letapis-qdrant || docker run -d --name letapis-qdrant \
  -p 6333:6333 -p 6334:6334 -v letapis_qdrant_storage:/qdrant/storage \
  qdrant/qdrant
```

Then press **Logs** on the row: a port already taken, or an image that could not be pulled, says
so in as many words. Both are about your machine, not about the panel — a container of another
project may already be holding 6333.

> **Your index lives in the volume `letapis_qdrant_storage`.** Removing the container is
> harmless. Removing that volume throws away everything the engine indexed.

---

## 5. The two models

Both are public downloads, about 610 MiB each. **The commands rename the files** — the service
cards look for the names on the left.

- [ ] Download them:

```bash
mkdir -p ~/models

curl -L -o ~/models/harrier-oss-v1-0.6b-Q8_0.gguf \
  https://huggingface.co/majentik/harrier-oss-v1-0.6b-GGUF-Q8_0/resolve/main/harrier-0.6b-Q8_0.gguf

curl -L -o ~/models/Qwen3-Reranker-0.6B.Q8_0.gguf \
  https://huggingface.co/ggml-org/Qwen3-Reranker-0.6B-Q8_0-GGUF/resolve/main/qwen3-reranker-0.6b-q8_0.gguf
```

**Note that both commands rename the file.** On the hub they are `harrier-0.6b-Q8_0.gguf` and
`qwen3-reranker-0.6b-q8_0.gguf`; the service cards look for the names on the left. Download them
any other way and you must either use these names or point the cards at the real paths
([services.md](docs/services.md) shows how). A file the card cannot find gives a readable
`FATAL: model weights not found` in the row's log — not a mystery, but not a working stack
either.

- [ ] Press **Start** on the **Embedder** row, then on the **Reranker** row.

**What that button does.** Each row runs a small script the panel wrote next to its cards
(`~/.config/letapis-app/services/embedder.sh` and `reranker.sh`). The script starts `llama-server`
with the weights you just downloaded and leaves it running in the background — there is no window,
and nothing appears in the Dock. Loading the weights takes a few seconds, so a row goes green a
moment after the click, not instantly. The log goes to `/tmp/letapis-embedder.log`.

Nothing else happens: no download, no install, no change to your system. If you would rather run
the script yourself, it is an ordinary file and you can read it first.

**Worked?**

```bash
curl -s 127.0.0.1:12436/v1/models >/dev/null && curl -s 127.0.0.1:8086/health && echo " both up"
```

If a row stays red, press **Logs** on it — a missing weights file says so in as many words, and so
does `llama-server` not being on your `PATH`.
What each model is and why the launch flags are what they are: [models.md](docs/models.md).

---

## 6. The engine

This is the licensed part. It is not in this repository and there is no public download — you
received a link from us.

- [ ] Download the kit with the link we gave you. It is a `.tar.gz` whose single top-level entry
      is `letapis.app`.

> **`letapis.app` is not an app to drag into `/Applications`.** It is a bundle only because
> that is how a signed program travels on macOS: double-clicking it does nothing you can see,
> and putting it in `/Applications` leaves the panel unable to find it. The app that belongs in
> `/Applications` is the panel, `letapis-app-rs.app`, from step 2 — this one goes where the
> commands below put it, and the panel starts it for you.

The engine goes under `~/.local/letapis-core/`, and the layout is the engine's own:

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

- [ ] Put it where the panel starts it from — three commands, and the third one is a link, which
      is why this is not a drag in Finder:

```bash
mkdir -p ~/.local/letapis-core/ota_0
tar -xzf ~/Downloads/letapis-core-*-darwin-aarch64.tar.gz -C ~/.local/letapis-core/ota_0
ln -sfn ~/.local/letapis-core/ota_0/letapis.app ~/.local/letapis-core/letapis-current
```

**Worked?** Ask it its version — this also runs it through the link, which is the path the panel
will use:

```bash
~/.local/letapis-core/letapis-current/Contents/MacOS/letapis --version
```

**Do not press Start yet.** An engine that has never been logged in refuses to start, and the row
would go red for a reason that is not a fault. Log in first — the next step.

---

## 7. Log this machine in

- [ ] Press the **key button** on the engine's row. A window opens with the address of our login
      page.
- [ ] Open that address in a browser, type your **licence key** and the **email the licence was
      issued to**. It answers with a string beginning `lt_`.
- [ ] Paste that string back into the panel's window.

Your key and your email stay in the browser — they are never written to this machine. The string
leaves the screen by itself a few minutes after it appears; copy it while it is there.

- [ ] When the window says the machine is licensed, press **Start** on the engine row.

**Worked?**

```bash
curl -s 127.0.0.1:3131/api/v1/health
```

Every refusal this step can produce, and what each one asks you to do: [licence.md](docs/licence.md).

---

## 8. Five green

- [ ] The panel shows five green rows. Confirm by hand if you like:

| Row | Port | Check |
|---|---|---|
| Docker daemon | — | `docker info` |
| Qdrant | 6333 | `curl -s 127.0.0.1:6333/healthz` |
| Embedder | 12436 | `curl -s 127.0.0.1:12436/v1/models` |
| Reranker | 8086 | `curl -s 127.0.0.1:8086/health` |
| letapis-core | 3131 | `curl -s 127.0.0.1:3131/api/v1/health` |

- [ ] Turn on **Autostart** if you want the machine to bring this up by itself. The switch arms
      two things at once: the panel relaunches when you log in, and it starts the whole stack.

---

### Who can reach the engine

The engine listens on the loopback address with **no key**, and it accepts requests from any
origin. That is deliberate: this is your machine, and a key here would have to be repeated in
every client's config — including the proxy in step 9, which would then refuse to start until
you fixed it too.

The part worth knowing: a web page open in your browser can also reach a loopback address. So
while the engine is running, a page you visit could in principle ask it what is in your index,
or start indexing a folder. Nothing on the open web knows the engine is there — but the
protection is that nobody is looking, not that the door is shut.

If that is not a trade you want, `~/.config/letapis/config.yaml` takes a key and a narrower
list of callers:

```yaml
server:
  api_keys: ["pick-your-own"]
  cors_origins: ["http://127.0.0.1:8000"]
```

Set it and every client needs the same key — the proxy reads it from `LETAPIS_API_KEY`. Leave
it and the stack works out of the box, which is why it ships this way.

---

## 9. Point your assistant at it

This is what the whole stack is for. The MCP proxy asks the engine what it can do and passes it
through, so nothing here needs updating when the engine learns something new.

- [ ] Install the proxy. There are two ways, and they differ in more than typing:

      **Clone the repository**, then start it from there:

      ```bash
      uv run --project <where-you-cloned>/letapis-mcp letapis-mcp
      ```

      Versions come from the lock file, and it runs with no network at all. The price is a
      repository you keep on the machine.

      **Straight from git**, nothing to clone:

      ```bash
      uvx --from "git+https://github.com/letapis-ai/letapis-core#subdirectory=letapis-mcp" letapis-mcp
      ```

      The price is that **every start goes to the network**. This stack otherwise never leaves
      your machine except to check the licence, and this is the one piece that would.

- [ ] Register it with your client — the config blocks for Claude Code, opencode and the others
      are in [letapis-mcp/README.md](letapis-mcp/README.md). Whichever way you installed it, the
      command above is what goes in the client's config.

**A key is not part of this step.** The engine on your own machine answers without one, and the
proxy sends none. If you later close the engine off with a key, put it in `LETAPIS_API_KEY` and
the proxy will carry it.

**Worked?** Your assistant lists letapis tools and answers about your own files.

That is the whole installation. From here the machine looks after itself: the engine renews its
own login, and updates arrive through the panel's **Update** button
([updating.md](docs/updating.md)).

---

## 10. Before you index your first folder

A folder is taken whole. Build output, vendored copies and generated files are indexed as eagerly
as your sources, and they cost more than space: machine-generated text is a dense scatter of your
own identifiers with no meaning behind it, which is exactly what a vector search scores highly.
Junk of that kind does not sit quietly at the bottom of the results — it competes with the answer
you wanted.

**The built-in exclusions are deliberately basic.** They cover what nearly every tree has —
version control, `node_modules`, Python caches and virtualenvs, `build/`, `dist/`, `target/`,
`out/`, editor droppings — plus a set of binary extensions refused by name. They carry **nothing**
for Xcode, Java, .NET, Go, mobile toolchains or your framework's cache directory, and that is a
decision rather than an oversight: an engine that shipped a list for every stack would impose it
on everyone who does not use them.

**So the first folder you add from an unfamiliar stack is yours to fence off.** The scale is not
marginal: an Xcode `DerivedData` directory can carry **tens of thousands** of indexable nodes, and
a packaged application server inside a platform repository can account for **more than half** of
everything indexed from it. Fencing either off is one line.

- [ ] **Look at the folder before you add it.** Whatever your build writes — `DerivedData/`,
      `.gradle/`, `bin/obj/`, `.next/`, `vendor/`, a packaged application server — name it.

- [ ] **Ask what is already covered**, so you write only what is yours:

      ```bash
      curl -s http://127.0.0.1:<your engine port>/api/v1/files/ignore-patterns | jq
      ```

      The port is `server.port` in your engine config (step 3).

      Every layer comes back named, with what each one is for. Your assistant asks the same
      question with the `ignore_patterns` tool.

- [ ] **Add yours when you add the folder**, through your assistant:

      ```
      index_folder(path="/path/to/repo", ignore_patterns=["DerivedData/", ".gradle/", "*.class"])
      ```

      The answer names any of your patterns that add nothing in that folder, checked against the
      files actually there, and says which of two things it found: nothing there matched the
      pattern at all, or what it catches is already caught — and then it names the rule doing
      that. Nothing is dropped; it just tells you what you did not need to type.

- [ ] **Machine-wide instead of per-folder?** Put it in `indexing.exclude_patterns` in your
      config file (step 3 wrote it) and restart the engine. Use this for what every folder on
      this machine should skip — your sync tool's droppings, your own toolchain's caches.

**Layers only add up.** A pattern set globally cannot be cancelled for one folder, so keep the
global list to what is genuinely machine-wide and let each folder carry its own.

**Already indexed the junk?** Add the pattern, then force a reindex of that folder. Changing the
patterns stops new files arriving; it does not remove what is already stored.

---

## When a step does not work

| What you see | What it means | Where to look |
|---|---|---|
| a row stays red | the service did not come up | **Logs** button on that row |
| `no config file was found on this machine` | the engine's config is missing or moved | step 3 — the panel writes it at first launch |
| `this machine has not been logged in yet` | the engine is fine, the licence step is not done | step 7 |
| the login page refuses your key and email | one of the two does not match | [licence.md](docs/licence.md) — every refusal by name |
| the download link says it expired | it lives minutes, by design | ask us for another |
| a model row is red right after Start | the weights are not where the card looks | step 5 — the names on the left matter |
| your build output turned up in search results | the built-in exclusions are basic and carry nothing for your stack | step 10 — ask what is covered, add what is yours |

Something wrong that is not in this table — **open an issue on this repository**. That is what it
is here for, and it is the one place you can reach us about the engine.
