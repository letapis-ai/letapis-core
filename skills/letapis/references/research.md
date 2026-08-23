# Working through a large document

A research graph is for material that does not fit in context and will not yield to one question:
a long PDF, a law, a manual, an unfamiliar module. It indexes the thing on its own, keeps
neighbouring chunks linked so an excerpt can be widened, and stays around between sessions.


**Reach for it when** the document is long enough that reading it costs more than querying it,
when the answer needs several passes at different parts, or when the work will span sessions.
**Not for** a quick lookup in an already-indexed corpus — that is ordinary [search](search.md).

## The shape of the work

```
create a scope  →  wait for it  →  ask it in pieces  →  keep what matters  →  retire the scope
```

### Create the scope

```python
mcp__<engine>__deep_index(path="/path/to/document.pdf", scope_id="descriptive-name")
mcp__<engine>__deep_index(path="/path/to/module/", scope_id="auth-module")
```

**Name the scope for what it holds**, not for the fact that it is research: `auth-module`,
`vendor-api-manual`, `procurement-act-2026`. Generic names — `temp`, `doc1`, `research` — become
unreadable the moment there are three of them, and scopes outlive the session that made them.

**A scope is a snapshot.** It holds the files as they were when it was built; editing them
afterwards changes nothing it answers. For a folder you are actively working in, rebuild the scope
when you want it current — there is no watching option here, and a stale scope answers
confidently.

### Wait for it

Deep indexing is a background job: the call returns an **`operation_id`** and the work continues on
the engine.

```python
op = mcp__<engine>__deep_index(path="/path/to/document.pdf", scope_id="descriptive-name")
mcp__<engine>__get_operation(operation_id=op["operation_id"])       # status · phase · result
mcp__<engine>__get_indexing_progress(scope_id="descriptive-name")   # progress for this scope
```

A small file is instant, a large PDF takes seconds, a big folder takes minutes. **Querying before
it finishes returns a partial answer that looks like a complete one** — the same trap as with
ordinary indexing, and the reason the operation is worth collecting rather than assumed.

### See its shape before asking about it

```python
mcp__<engine>__get_research_structure(scope_id="descriptive-name")
```

Where the structure is present — chapters, sections, figures, tables — this returns the tree of
it. That is the cheapest orientation available: you learn what the document contains and what it
calls its own parts, which is exactly the vocabulary your queries should use.

**An empty tree usually says something about the indexer, not about the document.** The basic
analysis writes chunks and the chain between them; it does not build chapters, sections, figures
or tables at all. So a 200-page manual with a full table of contents can come back with zero
chapters beside a healthy chunk count, and nothing is wrong. Read the emptiness as "this scope has
no structure", never as "this document has none" — and get your orientation by querying the
document's own opening pages instead.

### Ask it in pieces

**One question per query.** The instinct to ask for everything at once produces an answer that is
broad and useless; a document yields to a series of narrow questions, each aimed at one thing.

```python
mcp__<engine>__search(query="purpose scope of application",
                      scope_id="descriptive-name", limit=3, prev_next_chunks=2)

mcp__<engine>__search(query="governing body composition appointment",
                      scope_id="descriptive-name", limit=3, prev_next_chunks=2)

mcp__<engine>__search(query="penalties deadlines enforcement",
                      scope_id="descriptive-name", limit=3, prev_next_chunks=1)
```

| Parameter | How to set it |
|---|---|
| `scope_id` | required — this is what confines the query to your document |
| `limit` | 3–5 when you are after a specific passage, 10–15 for a survey |
| `prev_next_chunks` | 1–2 when an excerpt is likely to cut off mid-thought, 0 for precise hits |

**Ask in the document's own language.** A query in English against a document written in another
language matches far worse than the same query in its language — and mixing a structural marker
with a keyword ("section 8 special regime") beats either alone, because the marker anchors the
position and the keyword anchors the meaning.

### Keep what matters

Two ways, and they answer different needs.

**Write a summary as you go.** Create a note when you start and append to it after each pass,
rather than holding everything in context and writing at the end. Incremental writing survives a
session break, keeps context small, and leaves something searchable behind. Any note-writing tool
you have will do — the point is that it lands outside the conversation.

**Save individual findings into the corpus** when a specific passage is worth recalling later,
beyond this document:

```python
mcp__<engine>__save_research_finding(chunk_id=hit["id"], title="Sandbox eligibility rules",
                                     tags=["regulation", "sandbox"])

mcp__<engine>__link_findings(source_id=a, target_id=b, relation="implements")

mcp__<engine>__get_knowledge_graph(query="sandbox eligibility", tags=["regulation"])
```

**Keep the bulk out of context.** Large results belong in the notes you are writing; what travels
forward is the conclusion, not the material it came from.

Findings outlive the scope they came from. That is the difference worth knowing: delete the
research graph and the chunks go, but what you deliberately saved stays.

### Retire the scope

```python
mcp__<engine>__delete_research_graph(scope_id="descriptive-name")
mcp__<engine>__list_research_graphs()   # what is still around
```

Retire it when the analysis is done and the summary is written. Keep it when the work spans
sessions or the document is one you return to. Scopes cost storage and clutter the list; a
graveyard of half-finished ones is its own small problem.

## Three shapes this usually takes

**A legal or regulatory text.** Query the structure first — these documents almost always describe
their own organisation near the front. Then walk the sections one at a time, then come back for
the cross-cutting topics that are scattered on purpose: penalties, deadlines, exceptions,
definitions.

**An unfamiliar module.** Index the folder, find the entry points, follow the
dependencies outward, then look for the patterns that repeat — the base classes, the route
declarations, the places where the same shape appears three times.

**A book or manual.** Start with the table of contents to learn its own vocabulary, then query by
chapter topic in that vocabulary, then extract the definitions. Save the concepts that will matter
outside the book as findings; leave the rest in the scope.


## What the scope does not contain at all

**Only the text layer is indexed.** Whatever a document says in pictures — an icon standing for a
key, a label on a diagram, a value on a drawing, a dimension on a figure, any page of a scan with
no recognition layer behind it — is not in the corpus. Not ranked low: absent. No phrasing reaches
it, and no amount of rephrasing will.

**The tell is not an empty answer. It is a hole inside a passage that came back.** A document
being read this way produced:

> take power off to the controller; then supply power again and keep on pushing ▮ for about
> 5 seconds

The search worked exactly as it should — that is the right passage, the one an expert would point
at. The answer to the question asked ("which button") was never in the corpus, because on the page
it is a drawing. The sentence arrives with a gap where its subject should be, and reads as *hold
[nothing] for five seconds*.

**So: when a retrieved sentence loses its object, stop querying and look at the page.** Render it
and read it yourself. Rephrasing is the wrong instinct here and costs the most time, because every
new query returns the same passage with the same hole, which feels like the search failing when it
is the corpus not holding the thing.

The same applies to the answer that is *almost* right: a passage naming a part number, a wiring
colour or a terminal, where the identifier itself sits in the illustration.

## When the answers are wrong

The knobs are the same ones ordinary search uses, and they behave the same way here —
[search](search.md) § Narrowing. The one specific to this page: an empty result where the scope
should have material usually means the scope is gone or the indexing never finished, and
`list_research_graphs` says which.

That is a different symptom from the one above, and worth telling apart: **nothing came back** is
a question about the scope; **something came back with a gap in it** is a question about what the
page holds.
