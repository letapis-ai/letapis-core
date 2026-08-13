---
name: letapis
description: 'Work with a letapis engine — search a codebase or document corpus by meaning, trace who calls a symbol, analyse large documents, and recall what was decided before. Use this whenever you are looking for something in an indexed corpus and a plain text match is not obviously enough: "where is X handled", "who calls this", "what did we decide about Y", "make sense of this book/repo", "why is search returning nothing". Also use it when deciding whether a folder belongs in the index, or when old material should stop surfacing in results.'
---

# letapis

letapis answers several different kinds of question, and knowing which one you are asking is most
of the skill. The tools themselves describe what they do — the MCP layer carries that. What this page
adds is the part a tool cannot tell you: **which question each tool is good for, and how to read
an answer you did not expect.**

## Which question are you asking?

| Your question | What answers it | Where it is written up |
|---|---|---|
| Where is this handled? What exists about X? | semantic search over the corpus | [search](references/search.md) |
| Who calls this symbol? What breaks if I change it? | structural lookup (`blast_radius`) | [search](references/search.md) |
| Does this name exist anywhere at all? | structural lookup **and** a literal text match | [search](references/search.md) |
| Make sense of this book / paper / unfamiliar codebase | a research graph over the document | [research](references/research.md) |
| Was this decided before? What happened last time? | episodic memory (ENA) — **a date window only bites on episodes that carry a date; check it narrowed** | [memory](references/memory.md) |
| Memory has grown large — what is worth keeping? | a read-only audit of the episodes | [hygiene](references/hygiene.md) |
| The audit found something broken — how is it mended? | `letapis doctor`, a command of the engine | [hygiene](references/hygiene.md) |
| Should this folder be indexed? Should this doc stop appearing? | index and visibility management | [corpus](references/corpus.md) |
| Search is coming back wrong or empty and I do not know why | diagnosis from inside the session | [admin](references/admin.md) |
| What do these fields in the answer mean? | reading a result properly | [response](references/response.md) |

Pick by the question, not by habit. These tools have genuinely different reach, and the useful
answer usually comes from the one that matches the shape of what you are after.

## Addressing an engine — and choosing between engines

Every tool on these pages arrives to you prefixed with the name of the MCP server it came from:

```
mcp__<engine>__search(...)      mcp__<engine>__blast_radius(...)      mcp__<engine>__ena_get_context(...)
```

`<engine>` is not part of the tool. It is the key someone wrote in the client's configuration, so
it is whatever your setup calls it. **The names in your own tool list are the authoritative
answer**; the pages here write the slot out rather than guess it.

The joining pattern also differs by client: some compose `mcp__<engine>__search`, others
`<engine>_search` with no `mcp__` at all. A bare `search` resolves to nothing in either — the
tool is always reached through its server.

**More than one engine is a normal setup, and then the prefix is a real choice.** Each registered
engine has its own corpus and its own store: point one at the work you have in hand and another at
reference material you consult but do not edit, and you get two different answers to the same
query — correctly, because you asked two different corpora.

That makes picking the engine part of asking the question, not a detail of the call:

| What you are after | Which engine |
|---|---|
| the code, docs and decisions you are working on | the one indexing the working set |
| someone else's framework, library or manual | the one indexing reference material |
| what was decided before | the one your memory is written into — **check, do not assume: an engine with a marked folder of someone else's documentation grows episodes from their frontmatter and answers confidently with none of yours** |

Asking the wrong one fails in two ways, and the second is worse. Usually you get nothing, and
nothing looks exactly like "there is no such thing". Sometimes you get an answer — plausible,
confident, drawn from a corpus that has nothing to do with your question. Neither failure
announces itself, and both cost nothing to avoid: name the corpus before you name the query.

## The three reaches, and why they complement each other

**Meaning.** Semantic search finds things that are *about* something. Ask for "authentication"
and it returns `login()`, `verify_token()`, the middleware and the doc that explains the flow —
none of which contain the word you typed. This is the reach nothing else has, and it is why
search is the natural first move into unfamiliar ground.

**Structure.** `blast_radius` answers by the call graph: these are the places that actually call
this symbol, with file and line. It reads the files on disk each time, so it follows a branch
switch without reindexing.

**Letters.** A literal match answers about strings — a key in a config, a column name, an event
name, a value passed around as data. Whatever lives as data rather than as code is invisible to
the graph, and this is where a text match is the only tool that works.

Completeness is their intersection. When it matters that nothing was missed — before removing a
name, before a rename, when auditing a class of defect — asking two of the three and comparing
is what turns a claim into a finding.

## Reading an answer that surprises you

**An empty result is a fact about the question, not about the world.** Semantic search is
sensitive to phrasing: a generic query returns generic results, and a query in the wrong register
returns nothing at all. The productive move is to ask differently — in the words the material
itself would use — rather than to conclude the thing does not exist.

**And a full result is not proof either.** What the engine did to your query — whether the semantic
half ran at all, what a zero from the graph means, how much of a hit's structure is real — is in
the answer's own fields and nowhere in its text. The numbers cannot stand in for that: a hit from
the wrong corpus outscores the right one as easily as not.

## How this skill is arranged

The rooms below go deeper. Read the one that matches your question; there is no need to read
them all.

- **[references/search.md](references/search.md)** — asking a corpus: phrasing, narrowing, the
  three reaches, and reading a result properly.
- **[references/corpus.md](references/corpus.md)** — what the corpus is made of: what is indexed,
  adding and fetching material, following background jobs, retiring what should stop surfacing.
- **[references/response.md](references/response.md)** — what an answer carries besides its text:
  the hint that says the semantic half did not run, what the graph's flags actually claim, when
  structural context is a map and when it is noise.
- **[references/admin.md](references/admin.md)** — when the engine misbehaves: what to read to
  find out why, and the short list of operations that change state rather than report on it.
- **[references/research.md](references/research.md)** — turning a large unfamiliar document
  into something you can work through: research graphs, incremental analysis, keeping findings.
- **[references/memory.md](references/memory.md)** — **ENA, the Episodic Narrative Architecture**:
  recalling decisions and events, correcting what turned out to be false, forgetting what stopped
  being relevant. **A date window can filter nothing while looking as though it did** — how to
  tell is there too. Not merely a log: every episode carries where it came from and what it led to.
- **[references/hygiene.md](references/hygiene.md)** — auditing that memory once it has grown:
  finding orphaned, empty, stale or unlabelled episodes. The scan only ever reads and proposes;
  what to forget, correct or keep stays a decision someone makes deliberately.

Each room is written to stand on its own, so you can arrive there directly from the table above.
