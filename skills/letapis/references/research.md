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
mcp__<engine>__deep_index(path="/path/to/module/", scope_id="auth-module", watch=True)
```

**Name the scope for what it holds**, not for the fact that it is research: `auth-module`,
`vendor-api-manual`, `procurement-act-2026`. Generic names — `temp`, `doc1`, `research` — become
unreadable the moment there are three of them, and scopes outlive the session that made them.

`watch=True` keeps a folder scope current as its files change, which is what you want for a module
you are actively working in and not what you want for a fixed document.

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

Where the document has structure — chapters, sections, figures, tables — this returns the tree of
it. That is the cheapest orientation available: you learn what the document contains and what it
calls its own parts, which is exactly the vocabulary your queries should use. A scope indexed
without structure returns nothing here, and that is an answer too.

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
| `min_similarity` | lower for a broad sweep, higher when you know roughly what you want |

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

**An unfamiliar module.** Index the folder with `watch=True`, find the entry points, follow the
dependencies outward, then look for the patterns that repeat — the base classes, the route
declarations, the places where the same shape appears three times.

**A book or manual.** Start with the table of contents to learn its own vocabulary, then query by
chapter topic in that vocabulary, then extract the definitions. Save the concepts that will matter
outside the book as findings; leave the rest in the scope.


## When the answers are wrong

The knobs are the same ones ordinary search uses, and they behave the same way here —
[search](search.md) § Narrowing. The one specific to this page: an empty result where the scope
should have material usually means the scope is gone or the indexing never finished, and
`list_research_graphs` says which.
