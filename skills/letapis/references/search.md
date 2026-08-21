# Searching a corpus

Asking a corpus a question: phrasing that works, the three ways of reaching into it, and how to
read what comes back. What the corpus is *made of* — adding folders, following long jobs, retiring
material — is [corpus](corpus.md).


## Asking well

```python
mcp__<engine>__search(query="authentication logic", limit=10)
```

A hit carries the file path and an excerpt. **When the excerpt answers your question, you are
done** — opening the file adds nothing but tokens.

### Phrasing decides the answer

Semantic search is sensitive to register, and this is the single biggest lever you have. A query
written the way documentation talks finds documentation; a query written the way the code talks
finds code.

```python
# too abstract — finds tutorials and generic examples
mcp__<engine>__search(query="pydantic schemas API request response models")

# concrete — finds the file you meant
mcp__<engine>__search(query="schemas.py order validation pydantic")
mcp__<engine>__search(query="bearer token validation middleware")
```

What sharpens a query, in rough order of effect:

- **Name the area** — the module, service or subsystem, in the words the project itself uses.
- **Name the file** when you know it: `router.py`, `settings.yaml`.
- **Use the domain's own nouns** — the words that appear in the code, not the category they fall
  into. "webhook retry backoff" beats "error handling".
- **Prefer the specific over the general.** "bearer token validation" and "authentication" reach
  different depths of the same area.

**Sharpening a query and choosing its register are two different moves, and confusing them is the
common failure.** The list above makes a query more precise about the *machinery* — the module, the
file, the names the code uses. That is right when the answer sits in one named place. It is the
wrong move when you are asking where something happens: a symbol name returns the material built
out of that symbol, its tests and its neighbouring definitions, because that is what the corpus
holds about it. Describe what the system **does** and the place that does it comes back instead.

**One check tells you which register you are in: can you point at the file the answer must be
in?** Yes — sharpen as above; the text names itself and there is something to catch on. No —
describe the behaviour rather than the parts, because naming a part is what the structural axis is
for. A sweep is this same check applied to a change you just made (§ Meaning — the sweep).

**A query that returns the wrong thing is worth rewriting once before you reach for another
tool.** Most disappointing results are a register mismatch, not an absence.

### Which language to ask in

Register is one axis, language is another, and on a corpus written in more than one they pull
apart. Code spells its names in English whatever the team speaks; prose — docs, comments, notes —
carries the project's own language. So the language of the question quietly picks the half of the
corpus that answers it.

- **Identifiers, proper names and technical terms: English**, because that is how the code
  spells them and the keyword arm matches letters.
- **Asking about prose: the language the prose is written in.**
- **Asking about code: English plus a name FROM the code.** `RerankerService rerank` beats a
  description of what the thing does — the identifier exists in the source and not in the
  documentation, so the keyword arm has something to catch on.

Measured on our corpus: one question about file handlers returned **zero** `.py` files asked in
the prose language and **seven** asked in English. The failure is quiet — a fluent, plausible
answer built entirely from documentation, with the implementation never considered.

### `instruction` — the same query, a different facet

An instruction tells the embedding model what kind of thing you are after, which is often faster
than rewriting the query itself.

```python
mcp__<engine>__search(query="batch processing", instruction="Find documentation explaining this concept")
mcp__<engine>__search(query="batch processing", instruction="Retrieve source code implementing this feature")
mcp__<engine>__search(query="batch processing", instruction="Find configuration files for this setting")
```

Reach for it when a query returns a mix of docs, code and tests and you wanted one of them. Skip
it when the query is already specific, or when you deliberately want everything.

**An instruction changes the embedding and nothing else.** It does not move the similarity floor:
that is one constant the engine applies to every query, whatever its length and whether or not an
instruction came with it.

**Where the model's own response to instructions is concerned, corpora differ.** On some
embedders a well-aimed instruction sharpens a vague query; on others it narrows toward the named
kind of content and costs you the hit you wanted. Settle that half by running the same handful of
queries with and without one and watching where the right answer lands.

### Narrowing

A broad corpus answers broadly. Narrowing is how you turn it into the part you actually mean, and
there are two kinds of it — by **where** something lives and by **what** it is.

| Filter | Narrows to |
|---|---|
| `folder` | one indexed folder, by path prefix — `list_folders` gives the valid values |
| `groups` / `exclude_groups` | folders carrying a tag, and everything except those |
| `extensions` | file types: `["py", "ts"]` |
| `types` | node kinds, e.g. files against memory |
| `scope_id` | a research graph rather than the standing index |

**Group tags are the one worth knowing about**, because they are the only filter that is not
derivable from the material itself. A folder can be tagged — by stack, by ownership, by "ours
against vendored", by anything the corpus owner finds useful — and then one query reaches exactly
that slice:

```python
mcp__<engine>__list_groups()                                    # what tags exist, and what carries them
mcp__<engine>__search(query="retry backoff", groups=["backend"])
mcp__<engine>__search(query="retry backoff", exclude_groups=["vendored"])
```

Tags are set on the folder with `update_folder(path, groups=[…])`, and changing them takes effect
immediately — they are a search-time label, not part of the index, so no reindexing follows.
`blast_radius` takes the same `folder` and `groups` narrowing, which is what makes a structural
lookup of a common name tractable.

**Groups are folder labels, not document tags**, and the shared word causes real confusion.
Tagging a *document* is a different mechanism living elsewhere: saved findings carry tags you
query with `get_knowledge_graph(tags=[…])`, and a note vault has its own tagging outside this
engine entirely. `groups` never reaches either — it selects whole watched folders.

The rest of the knobs change the shape of the answer rather than its scope:

| Parameter | What it does |
|---|---|
| `prev_next_chunks` | 0–5 neighbouring chunks — the cure for an excerpt that stops mid-thought |
| `depth` | 1–3 hops along the graph, returning the neighbourhood of a match rather than the match alone |
| `min_similarity` | a floor for the **vector** arm only; keyword hits are not subject to it, so a high value can empty one arm and leave the other answering alone. **There is always a threshold** — unset, the engine applies one constant to every query; setting this replaces that constant, it does not switch a filter on |
| `use_reranker` | on by default; `false` gives the raw fused order — see below for when it earns its place |
| `include_forgotten` | brings back material deliberately retired — the only way to search what was hidden, and exactly what you want when asking what the corpus *used to* say |
| `verbose` | the full metadata behind each hit |

**A knob you do not know about is a knob you do not use.** The common shape of that: four queries,
one per folder, where one query with a group tag would have done — or reading a whole file because
the excerpt was cut and the parameter that widens it never came to mind.

### The reranker, and why a flat A/B does not mean it is useless

A cross-encoder over the merged result: it re-reads query and document **together**, which the
embedder cannot — that one encodes each side separately and never sees the pair. It reorders the
top candidates before you see them.

**Where it earns its place:** a mixed corpus of code, prose and memory, where the embedder is
drawn to topically similar documents. It pulls the concrete implementation up and pushes generic
prose, duplicates and stray notes down.

**On easy queries it is neutral by construction** — the right answer was already first, and there
was nowhere to improve. This is worth knowing *before* you measure: a flat result on an easy query
set says the set had no room, not that the reranker does nothing. Judge it on queries where the
embedder currently gets the order wrong.

### Deciding which to reach for

The list above is what exists. This is the order that works.

**Start by asking what the corpus is made of, not by guessing a path.** `list_folders` gives the
valid `folder` values and `list_groups` gives the tags — and tags may not exist in a given corpus
at all, which is itself worth knowing before you narrow four times by hand. One call each, once
per corpus, and after that you are choosing rather than guessing.

**A folder filter is a path prefix, so it covers nested watches too.** A parent directory that is
itself indexed alongside several of its subdirectories will return hits from all of them under one
`folder` value. That matters most in the negative: an empty result under a parent really does mean
the area is empty, not that the children were excluded.

**`types` separates kinds of node** — `file` for indexed content, `memory` for episodes. Use it
when a query is pulling documents into a memory question or the reverse.

**`limit` defaults to 10, and the default is invisible in the answer.** A result of ten is what
the parameter did, not what the corpus holds; concluding "there are about ten of these" from a
default-sized result is the most common way to be confidently wrong about volume. When the count
itself is the question, raise the limit or ask a tool that reports totals.

### Reading a hit properly

A result carries more than a path and an excerpt — structural context around the hit, and fields
that say what the engine did to your query. How good each of them is depends on the material, and
one of them is the only warning you get when the semantic half of the search did not run at all.
That is [response](response.md).


## Three reaches, and how to run each

[SKILL.md](../SKILL.md) explains why these complement each other. This is how you use them.

### Meaning — the sweep

A fix usually arrives aimed at one place: this file, this method. Real codebases hold **siblings** —
the same pattern, or the same missing guard, in another module, another entry point, another
stage of the same workflow. A sweep is a short semantic search for those, run while the change is
still fresh in your head.

**Run it per change, not batched at the end.** Three moments earn one:

- **An anomaly surfaced** — a silent skip, an unexpected error, behaviour that does not fit. Ask
  the corpus whether this happens anywhere else.
- **You are about to change a specific method.** The plan named one point, because plans name one
  point; the codebase decides how many there really are.
- **You are unsure of the scope.** Sweeping *before* the edit widens what you understand about how
  the change lands.

**How to phrase it.** Describe what you fixed along two or three axes — the behaviour, the guard,
the stage — rather than naming the symbol you touched. The symbol is what a structural lookup is
for; the sweep hunts places that *rhyme* with your change without sharing its names.

**Read every hit as one of three things:** already handled, and it is worth knowing why · genuinely
different, the resemblance is superficial · a missed surface, so either widen the fix or say out
loud that you found it and left it.

Writing the outcome down is what makes a sweep worth running twice. A short table of the surfaces
you checked and why each is safe is the difference between "I looked" and something the next
person can trust.

**When it is overkill:** a typo or a rename carries no behavioural pattern to find; a plan that
already swept upfront has done this work; a fix at a level everything inherits from covers its
siblings by construction.

**What skipping costs:** a surface nobody covered does not announce itself. It sits quietly and
turns up weeks later as an incident, in the one path that was never on the list.

### Structure — `blast_radius`

```python
mcp__<engine>__blast_radius(symbol="action_done")                 # exact callers, plus definitions
mcp__<engine>__blast_radius(symbol="create", scope="SomeModel")   # scope when the name is ambiguous
```

It returns exact call sites with file and line, the definitions, and an `ambiguous` flag when the
name lives on more than one type. It walks edges rather than embeddings, so it is deterministic,
and it reads the files on disk, so it follows a branch switch without reindexing.

**Aim at the symbol that carries the impact, not at the facade.** Run it on a widely overridden
method or a UI-facing entry point and you get hundreds of callers, most of them tests. Run it on
the inner symbol that actually does the thing and you get a clean map.

**"Every caller is a test, none in production" is a signal, not an answer.** It usually means the
real entry arrives over a transport — a route, an event, a `model.method` string called from a
front end — which a same-language call graph cannot see. Go looking for the contract string
itself rather than concluding nobody calls it.

**Declarative links live outside the graph.** A call graph is keyed by symbols. A contract that
travels as a **string** — a view attribute read by a template, a config key, a data binding — is
not a symbol and not a call edge, so the lookup comes back empty **by design**. For those surfaces
the honest check is a list-to-list diff of the two sides. Missing one is a silent no-op: invisible
to the graph, invisible to unit tests, visible only when someone opens the page.

**`ambiguous=true` with several definitions is a duplication detector**, not merely a hint to
narrow. The same name on several types is often one piece of logic copied twice, and reading all
the definitions is a cheap way to find drift a semantic sweep would not surface.

**Output larger than you want to read** — narrow with `scope`, `folder` or a group tag. There is
no `limit` here; a structural lookup returns what it found.

**What comes back needs reading, not just counting.** Two counters mean different things, one
flag claims more than it knows, and the `hint` carries the real reason for a zero —
[response](response.md) § blast_radius.

**Whole languages sit outside the graph, not just declarative links.** A call graph is built by a
parser, and a parser covers the languages it was written for. Everything else — shell scripts,
configuration, templates, generated code — produces no edges at all, and asking the graph about a
symbol defined in one of them returns zero every time.

**A zero has two readings and they are indistinguishable in the answer:** the name may live as
*data* rather than as code — a config key, an event name, a value passed around — in which case a
literal match finds it immediately; or the file may be in a language the parser does not cover, in
which case the zero is about the parser and nothing about callers. Before reading a zero as "nothing calls
this", ask what the thing is written in; if the graph does not cover it, the question belongs to
the textual axis from the start.

**`scope` disambiguates by class or model**, which is worth knowing in a corpus where the same
method name lives on many types. Where names are already unique, it does nothing for you.

### Letters — a literal match

A text search answers about strings: a key in a config, a column name, an event name, a value
passed around as data. Names that live as *data* rather than as code are invisible to the graph,
and this is exactly where a text match is the only tool that works.

It is also the pinpoint step **after** a semantic search has located the file: the exact string
for an edit, the exact line to confirm.

**Two traps when refactoring:**

- **A text-match hit is a candidate, not a fact — commented-out code looks alive.** A plain match
  cannot tell a live call from one behind a comment marker. Either build the inventory from
  corpus chunks, which carry enough context to see it, or confirm each hit by reading around it.
- **When you replace a symbol or an event, verify by symbols, not by names.** Turning "publish an
  event, listen for it" into a direct method call makes a text search for the event name blind to
  the callers you missed — the new pattern does not contain the old name, so there is nothing to
  match. The loop that works, per migration step: sweep by meaning for who else takes part → make
  the change → `blast_radius` each symbol you touched → account for every caller as done, known
  remainder, or noise. The same query cheaply reveals dead methods: zero callers of your own is a
  strong candidate for removal.

**Proving a name appears nowhere needs two of the three.** The graph answers about calls, a text
match about strings; a name that lives in a config or as a passed value is visible only to the
second. One axis gives a claim, two give a finding.

## Deep analysis of one document

For a large file or an unfamiliar module, a research graph gives you neighbouring-chunk context
that ordinary indexing does not carry. That workflow, and what to do with what you find, lives in
[research](research.md).

## When search comes back empty

- **Check you asked the right engine.** With several registered, an empty result most often means
  the corpus you queried never held the thing.
- **Check it is indexed** — `list_folders`, and see [corpus](corpus.md) if it is not.
- **Rewrite the query in the register of the material**, once, before switching tools.
- **If the target is a name rather than a concept**, the semantic route is the wrong one: use the
  structural lookup, or a literal match.

If none of those is it, the fault may be below the query — a half-built index, missing vectors,
chunks out of step with the files. [admin](admin.md) is where that gets diagnosed.
