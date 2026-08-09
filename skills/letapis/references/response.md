# Reading a response

An answer carries more than the text you asked for, and several of its fields say things the text
cannot. This page is what each one means, and which of them change how you should read everything
else in the result.


## `hint` — read this before the results

When the engine did something to your query that you did not ask for, it says so here. **Nothing
else in the answer will tell you**, and the results will look entirely normal.

The one that matters most: a query can come back **keyword-only**, with the semantic half filtered
out entirely, and the hint is the only place that appears.

```
hint: Results are BM25-only: the adaptive min_similarity threshold
      filtered the vector (semantic) arm down to 0 candidates
```

**Why that is worse than an empty answer.** Two searches run on every query: one by meaning, one
by literal words. When the meaning half returns nothing, the word half answers alone — and on a
technical query it answers *well*, because the words you typed are the words in the code. The
result looks like a good semantic answer and is a text match. Everything named differently was
never considered.

**What to do about it is not what the hint suggests.** It advises lowering `min_similarity`, which
you probably never set: the engine computes a threshold from the shape of your query whenever you
leave it unset. The move that works is the opposite — set an explicit low floor to override the
computed one. Expect a genuinely different set of files, not the same list with more of it.

## An episode in a search result

Ordinary search reaches episodes too, and such a row looks unlike the others: `type: "episode"`,
a similarity, and none of the file fields — no path, no excerpt, no structural context. It is not
malformed; it is a memory node surfacing in a corpus query. Read it as a pointer: the material is
in memory, and [memory](memory.md) is where it is retrieved properly.

## `score` and `similarity` — and what neither of them can tell you

`score` ranks within one answer. The top row is always `1.0`, including for a nonsense query,
because it is relative to the rest of that result set. It is not comparable across queries.

`similarity` is the raw measure, and it appears **only on semantically matched rows**. Its absence
on a keyword-matched row means "not measured", not "zero".

**Neither says whether the answer came from the right corpus.** A query sent to an engine that
knows nothing about your subject returns its best matches in the same numeric band as a correct
answer elsewhere — a wrong-corpus hit can outscore the right one. There is no threshold that
separates them, and hunting for one is the trap. **The path in each hit is what separates them**:
material with nothing to do with your work says so in its location long before any number does.

## `structural_context` — how good it is depends entirely on the material

Each hit carries the section it sits in, the path of parent headings, and an outline of the file.
At its best this is a map: you learn what else is in the file and where, and decide whether the
rest matters without reading it.

At its worst it is noise you pay for in every hit. The shape it takes:

| Material | What you get |
|---|---|
| code the extractor parses | function and class names, a true tree — the best case |
| prose with headings | the heading path and a tree of sections — equally good, often better |
| code parsed loosely | an exploded syntax tree: fragments of function bodies and truncated source lines listed as sections |
| shell and similar | first words of lines as section names, repeated once per occurrence |
| data files | the field may be absent altogether |

**Judge it per hit rather than trusting it per corpus.** When the outline reads like fragments of
source, it is the parser talking; fall back to reading. When the field is missing entirely, that
is a third outcome and not an error.

**One genre where it costs more than it saves:** a document whose whole body is a single heading —
some memory episodes are written this way — puts that same block in the section, the heading path
and the outline at once. A handful of such hits is mostly the same text repeated, and neither a
smaller `limit` nor fewer neighbouring chunks helps, because the bulk is in the context field
rather than in the excerpt.

## `blast_radius` — the fields that say what a zero means

| Field | What it actually tells you |
|---|---|
| `symbol_found_on_disk` | **reads as a claim about the disk; is a claim about the parser.** A name written in a language with no extractor returns `false` while sitting in the files many times over |
| `hint` | the one that carries the real reason — that the extension has no extractor, that module-level names are a blind spot. Without it the flag above misleads |
| `caller_count` vs `call_site_count` | distinct callers against distinct places. One caller invoking a symbol three times reads as `1` and `3`; take the first for "one place" and you miss two |
| `definitions` | **count them yourself.** More than one definition of the same name is worth reading whichever language you are in |
| `ambiguous` | fires when a name lives on several *types*. In languages where free functions all sit at module level it stays `false` even with several definitions — so it is not a general duplicate detector |

## What a recall carries

An episode arrives with more than its text, and three of its fields are about the record rather
than the subject: `t_valid` (the date it can be filtered by — **null means it cannot be**),
`provenance` (observed, inferred, confirmed by a person) and `confidence`. Together they are why
two episodes saying opposite things are not equally weighted.

Two numbers head the response and belong to the **session**, not to the answer:

| Field | What it measures | What it does **not** mean |
|---|---|---|
| `Trust` | a running average over this session of whether recalls found confident matches | nothing about whether *this* answer is correct |
| `Self-Continuity` | how close this query is to the previous one in the same session | it drops when you change subject, which is normal and not a warning |

Repeat a query verbatim and self-continuity reads 1.00; ask something unrelated and it falls.
Neither number is a quality signal for the material you got back.

**`memory_barrier` is the one that is.** It appears when nothing crossed the confidence bar —
`no_match` when nothing was found at all, `uncertain` when only weak matches were. An answer that
carries it is telling you its own contents are thin.

## What a folder listing tells you beyond paths

`list_folders` is not only "is this indexed". Four of its fields answer questions you would
otherwise guess at: `active` (a watch can be listed and switched off), `files_indexed` and
`last_update` (zero files or a date months old is a diagnosis), `ignore_patterns` (the most common
reason a file in a watched folder never appears), and `odoo_aware` (which extraction mode decides
what the call graph can see).

**`description` and group tags are free text, and free text outlives its meaning.** A folder
described as one thing and tagged as another will answer confidently from material that is neither.
When a name and its contents disagree, the contents win — count the files or read a couple of hits
rather than trusting the label.
