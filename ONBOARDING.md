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
| **Memory** | **16 GB** or more | the two models together hold roughly 3 GB resident (see [models.md](docs/models.md)); the engine and Qdrant want their share on top |
| **Disk** | **~1.6 GB** to install, plus room for the index | the two models ~1.2 GB, the engine ~240 MB, Qdrant ~70 MB, the panel ~20 MB, llama.cpp ~20 MB. Add another ~240 MB when the first engine update fills the second slot. The index grows in `~/.letapis/qdrant/` as the engine feeds it — plan for that separately |
| **llama.cpp** | installed | both models run under its `llama-server` |
| **uv** | installed | how the MCP proxy runs (step 9) |
| **Homebrew** | installed | how llama.cpp and uv get onto the machine |

- [ ] a terminal you are willing to paste three commands into. There is no installer, on purpose:
      you see what happens on your machine, and when something goes wrong you know which step.

---

## 1. Three dependencies

The panel supervises the model servers and the database; it does not install them.

- [ ] **Homebrew** — not part of macOS. If `brew --version` does not answer, install it from
      [brew.sh](https://brew.sh) and follow the "Next steps" it prints (on Apple silicon it asks
      you to put `/opt/homebrew/bin` on your `PATH`, and `brew` does not work until you do).
- [ ] **llama.cpp** — `brew install llama.cpp`
- [ ] **uv** — `brew install uv`. Step 9 runs the MCP proxy with it.

**Worked?**

```bash
brew --version && llama-server --version && uv --version && echo "all three answer"
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

You do not have to do anything here: read it, tick it, move on. The panel wrote three things and
will never touch any of them again:

- [ ] `~/.config/letapis-app/` — the service cards it starts things from. **Yours** from now
      on: change a port or a path and the panel obeys ([services.md](docs/services.md));

  ```
  ~/.config/letapis-app/
  ├── services.yaml            the list of services, in start order
  └── services/
      ├── qdrant.yaml          one card per service…
      ├── embedder.yaml
      ├── reranker.yaml
      ├── letapis-bin.yaml
      ├── qdrant.sh            …and the three launch scripts
      ├── embedder.sh
      ├── reranker.sh
      ├── qdrant-docker.yaml   …and three cards nothing points at — see "Qdrant in a container"
      ├── docker.yaml
      └── podman.yaml
  ```

- [ ] `~/.config/letapis/config.yaml` — the **engine's** configuration, already pointing at the
      services you are about to start. Without it the engine refuses to start, and nothing else
      on the machine creates it.
- [ ] `~/.local/letapis-qdrant/config.yaml` — **Qdrant's** configuration: where it keeps the
      index and which ports it binds. The panel wrote it beside where the binary goes, at the
      same moment it made the Qdrant card, because it is the only one that knows those numbers.
      You do not write this file, and you do not need to wait for it — it is there now, before
      the binary it belongs to.

**Want to see what a working machine actually runs?** [`config/default/`](config/default/) in
this repository holds the same files as they are on ours: the cards, the engine's config and
Qdrant's, with every value commented. What the panel writes is deliberately shorter: it fills in
what your machine needs and leaves the rest to the engine's own defaults.

Take them, take a few lines out of them, or ignore them entirely. They are a reference, not a
step: the panel already gave you a working set, launch flags included. The embedder's flags
matter more than they look — on stock defaults that server reserves memory for inputs sixty
times larger than ours and aborts under indexing load — and the panel writes them for you.
Nothing here needs copying.

> **When each of the three appears is not the same question, and the panel never writes over
> one that is there.**
>
> The cards and the engine's config come from a launch that finds no `~/.config/letapis-app/` at
> all. A panel that already has cards leaves both alone: they are yours.
>
> Qdrant's config goes by its card, not by the launch. The panel writes it in the run where it
> creates `services/qdrant.yaml` itself — the launch above on a fresh machine, or a later one
> where a card you never had is added. A card that was already on disk is somebody's else work,
> and the panel writes nothing beside it.
>
> To start from scratch, remove `~/.config/letapis-app/` and `~/.config/letapis/` before
> launching — that throws away any service cards you had changed.

**Worked?** The panel window shows **four rows**, all of them red. That is correct; nothing they
start is installed yet.

---

## 4. Qdrant

The database the engine keeps its index in. One download and one unpack, the same shape as the
models in step 5 and the engine in step 6.

There is no Homebrew formula for it, so you take the archive from its Releases.

- [ ] Download the build for Apple silicon and unpack it where the card looks for it:

```bash
mkdir -p ~/.local/letapis-qdrant/bin

curl -L -o /tmp/qdrant.tar.gz \
  https://github.com/qdrant/qdrant/releases/latest/download/qdrant-aarch64-apple-darwin.tar.gz

tar -xzf /tmp/qdrant.tar.gz -C ~/.local/letapis-qdrant/bin
```

- [ ] Press **Start** on the Qdrant row.

Its configuration is already there — `~/.local/letapis-qdrant/config.yaml`, written by the panel
in step 3. It says where the index lives and which ports to bind, and you do not have to touch it.

**Worked?**

```bash
curl -s 127.0.0.1:6333/healthz          # healthz check passed
```

**That check is answered by whatever holds the port**, and on a machine where 6333 was already
busy it will be something other than the Qdrant you just installed. The panel's lamp reads the
same address and goes green on the same stranger. The one place that tells you apart is the log:

```bash
grep -c "Address already in use" /tmp/letapis-qdrant.log     # 0 if the port was yours
```

If the row stays red, press **Logs** on it. The script names what is missing in as many words:
`binary not executable` means the unpack did not land where the card looks, `no config` means the
configuration file is not there.

> **Your index lives in `~/.letapis/qdrant/storage`.** It is an ordinary folder; you can open it
> in Finder. Deleting it throws away everything the engine indexed, and re-indexing is the only
> way back. Replacing the Qdrant binary does not touch it.

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
`FATAL: model weights not found` in the row's log. Not a mystery, but not a working stack
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

If a row stays red, press **Logs** on it. A missing weights file says so in as many words, and
so does `llama-server` not being on your `PATH`.
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

There are two slots, and an update always fills whichever one is free, so after your first
update this link points at `ota_1`, after the next one at `ota_0` again. Which slot is current is
never something you need to know: the link is the answer.

The panel starts the engine **through the link**, never through a slot directly:

```
~/.local/letapis-core/letapis-current/Contents/MacOS/letapis
```

That is the whole reason the link exists: the panel keeps one fixed path and never has to know
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

## 8. Four green

- [ ] The panel shows four green rows. Confirm by hand if you like:

| Row | Port | Check |
|---|---|---|
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
or start indexing a folder. Nothing on the open web knows the engine is there, but the
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

## Qdrant in a container instead

By default Qdrant runs as an ordinary program on your Mac, and the container path is not used.
It is still there: on an install made from this page the panel wrote its cards into `services/`
at step 3 and points at none of them, so turning it on is an edit to the list and no yaml of your
own. Coming the other way, off a container you have been running for a while, costs a little
more — the second half of this section says what.

Both directions are the same edit, and both need Docker Desktop or Podman installed first.

**One line, exchanged, not added.** Port 6333 belongs to one program at a time, so the list holds
one Qdrant line. Adding a second leaves two cards fighting over the port, and the row that loses
sits red with nothing to explain it.

**The order below is the point of it.** Stop the Qdrant you are leaving before you swap anything:
it is holding 6333, and the one you are moving to cannot have the port while it is up. Press
**↻** at the top of the window afterwards — that is what makes the panel re-read the list from
disk; without it the window goes on showing the card it loaded at launch
([services.md](docs/services.md)).

Skip the stop and you land in the trap from step 4, and you land in it harder than anyone: the
new Qdrant fails to bind, the old one answers `healthz` from the same port, and the row goes
green about the program you were trying to leave. `grep -c "Address already in use"
/tmp/letapis-qdrant.log` is what tells them apart.

### Moving to the container

- [ ] Press **Stop** on the Qdrant row first, and check the port is free:
      `lsof -nP -iTCP:6333 -sTCP:LISTEN` should answer nothing.
- [ ] In `~/.config/letapis-app/services.yaml`, replace the Qdrant line:

```yaml
services:
- conf: ~/.config/letapis-app/services/qdrant-docker.yaml   # was qdrant.yaml
- conf: ~/.config/letapis-app/services/embedder.yaml
```

- [ ] Add `docker.yaml` (or `podman.yaml`) above it if you want a row showing whether the runtime
      itself is up. That one is an addition, not an exchange — it is a different service.
- [ ] Press **↻**, then **Start** on the Qdrant row.

The Qdrant row now starts a container instead. **Your index does not come with it.** The native
index is a folder, `~/.letapis/qdrant/storage`; the container keeps its own in a runtime volume,
`letapis_qdrant_storage`, and starts empty. Re-index, or copy the folder across yourself. Either
way it is a copy.

### Moving off the container

**If you installed letapis before the native path existed, the exchange has nothing to exchange
with.** Your `services/qdrant.yaml` is the container card — that is what the panel wrote at the
time — and the native card, its script and Qdrant's own configuration were never put on your
machine. The panel will not add them now: it does not write over cards it once made.

So this direction is three files you copy, and they are all in this repository, in
[`config/default/`](config/default/):

- [ ] Press **Stop** on the Qdrant row. A container the panel did not stop keeps running and
      keeps 6333, and the native Qdrant you are about to install will not get the port. Check:
      `lsof -nP -iTCP:6333 -sTCP:LISTEN` answers nothing.
- [ ] Install the Qdrant binary — step 4, the download and unpack part.
- [ ] Copy the native card and its script into your configuration, over the container card:

```bash
cp config/default/letapis-app/services/qdrant.yaml ~/.config/letapis-app/services/qdrant.yaml
cp config/default/letapis-app/services/qdrant.sh   ~/.config/letapis-app/services/qdrant.sh
```

- [ ] Copy Qdrant's own configuration and **put your own home directory in it** — Qdrant does not
      expand `~`, and a path with one in it makes a folder called `~`:

```bash
mkdir -p ~/.local/letapis-qdrant
cp config/default/letapis-qdrant/config.yaml ~/.local/letapis-qdrant/config.yaml
$EDITOR ~/.local/letapis-qdrant/config.yaml     # /Users/you/... → your home
```

- [ ] Drop the runtime's own card from `services.yaml` if you had one. The Qdrant line already
      points at `qdrant.yaml`, so it needs no edit.
- [ ] Press **↻**, then **Start** on the Qdrant row. You replaced a file the panel had already
      read, so without ↻ it starts the card it still remembers — the container one.

Coming from a fresh install instead, where all three cards are already in `services/`? Then it
really is one line: `qdrant-docker.yaml` out, `qdrant.yaml` in, and the same order around it —
Stop, swap, ↻, Start.

Here too the index stays where it was. The volume keeps what it has, and the native side starts
with an empty folder.

---

## 9. Point your assistant at it

This is what the whole stack is for. The MCP proxy asks the engine what it can do and passes it
through, so nothing here needs updating when the engine learns something new.

- [ ] Install the proxy. There are two ways, and they differ in more than typing:

      **Clone this repository**, then start it from there:

      ```bash
      git clone https://github.com/letapis-ai/letapis-core.git ~/letapis-core
      uv run --project ~/letapis-core/letapis-mcp letapis-mcp
      ```

      Versions come from the lock file, and it runs with no network at all. The price is a
      repository you keep on the machine — put it wherever you like and change the path to match.

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

## 9a. One setting worth checking before you index

If you installed before 2026-08-27, your `config.yaml` may carry a value that leaves the
embedder no room to work. It takes half a minute to check.

Open your engine config — the panel wrote it at the path shown on the Engine card — and look at
the `embeddings:` block:

```yaml
embeddings:
  token_batch_size: 2048        # <- this one
  chars_per_token: 2
  chunk_size: 1024
```

**The rule.** Those three numbers decide one thing between them:

```
window = token_batch_size × chars_per_token
```

and every chunk, **plus a context prefix the engine adds in front of it (up to 192 characters)**,
has to fit inside that window. A chunk that outgrows the window is refused by name — the engine
treats it as a wiring fault rather than trimming your text silently.

With `chunk_size: 1024` the arithmetic is:

| `token_batch_size` | window | chunk + prefix | verdict |
|---|---|---|---|
| 512 | 1024 | up to 1216 | **too tight** — the prefix has nowhere to go |
| 2048 | 4096 | up to 1216 | fine, roughly threefold headroom |

**If yours says 512, change it to 2048 and restart the engine from the panel.** Nothing else in
the block needs touching, and nothing needs reindexing: this value does not change how text is
cut, only how much of it travels in one request.

**It is not tied to the embedder's own flags.** You may have seen `--batch-size 512` in
`embedder.sh` and assumed the two must match. They do not: that flag sizes an internal pass
inside the server, not the input it accepts. Measured on llama-server 10360 with
`--batch-size 512`, an input of 2668 tokens was accepted and returned a vector, with the server
none the worse. Leave the launch flags exactly as the panel wrote them — each is there to keep
the server alive under indexing load.

Full reference: [`docs/EMBEDDING_SETTINGS.md`](docs/EMBEDDING_SETTINGS.md).

## 10. Before you index your first folder

A folder is taken whole. Build output, vendored copies and generated files are indexed as eagerly
as your sources, and they cost more than space: machine-generated text is a dense scatter of your
own identifiers with no meaning behind it, which is exactly what a vector search scores highly.
Junk of that kind does not sit quietly at the bottom of the results; it competes with the answer
you wanted.

**The built-in exclusions are deliberately basic.** They cover what nearly every tree has —
`node_modules`, Python caches and virtualenvs, `build/`, `dist/`, `target/`, `out/`, editor
droppings — plus a set of binary extensions refused by name, and the version control directories
in a layer of their own that nothing overrules. They carry **nothing**
for Xcode, Java, .NET, Go, mobile toolchains or your framework's cache directory, and that is a
decision rather than an oversight: an engine that shipped a list for every stack would impose it
on everyone who does not use them.

**So the first folder you add from an unfamiliar stack is yours to fence off.** The scale is not
marginal: an Xcode `DerivedData` directory can carry **tens of thousands** of indexable nodes, and
a packaged application server inside a platform repository can account for **more than half** of
everything indexed from it. Fencing either off is one line.

- [ ] **Look at the folder before you add it.** Whatever your build writes — `DerivedData/`,
      `.gradle/`, `bin/obj/`, `.next/`, `vendor/`, a packaged application server — name it.

- [ ] **Ask what is already covered**, so you write only what is yours. Ask your assistant —
      *what does the engine already exclude?* — and it answers with the `ignore_patterns` tool:

      ```
      ignore_patterns()
      ```

      Every layer comes back named, with what each one is for.

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

**A folder can overrule the machine.** The lists are glued in one order — the built-in list, your
config, then the folder's own rules — and the last line that matches wins. A folder cancels a
pattern from either list above it by writing `!<pattern>` among its own rules. Still keep the
global list to what is genuinely machine-wide: a cancellation is worth writing once, not in every
folder.

Two things no `!` reaches: the version control directories, which sit below the folder on purpose,
and the sets matching by file extension or file name, which are not part of the pattern list at
all. `ignore_patterns()` names every layer and says which of them a folder may overrule.

**Already indexed the junk?** Add the pattern, then force a reindex of that folder. Changing the
patterns stops new files arriving; it does not remove what is already stored.

### Notes are a second decision

Adding a folder of notes — an Obsidian vault, a directory of design documents, anything where you
write down what you decided — indexes it for search like any other folder. It does **not** make
those documents part of the engine's memory. That is a separate choice, and it is off unless you
make it:

```
index_folder(path="/path/to/vault", episodes=True)     # when you add the folder
update_folder(path="/path/to/vault", episodes=True)    # or later, on a folder already there
```

With the flag on, a document that records a decision or a milestone also becomes an episode: the
engine can later be asked what was decided about something and answer from those notes rather
than from a keyword match. With it off, the folder is searched exactly as any other; its
documents simply never become episodes.

The flag is set on the watched root and covers everything under it — subdirectories do not need
their own. The default is off on purpose: memory grows only where somebody allowed it to.

One folder should stay unmarked — the one the engine writes its own memory files into. Marking it
would make the engine remember its own memories, and the copies pile up.

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
