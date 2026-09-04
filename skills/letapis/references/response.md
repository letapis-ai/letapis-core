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
hint: Results are BM25-only: no vector candidate cleared min_similarity,
      so the semantic arm contributed nothing
```

**Why that is worse than an empty answer.** Two searches run on every query: one by meaning, one
by literal words. When the meaning half returns nothing, the word half answers alone — and on a
technical query it answers *well*, because the words you typed are the words in the code. The
result looks like a good semantic answer and is a text match. Everything named differently was
never considered.

**What to do about it.** The hint names the way back itself, and the contract for that
parameter is in its schema — read it there rather than from a second account here. What belongs
on this page is how to read the outcome: expect a genuinely different set of files, not the same
list with more of it. An arm that contributed nothing does not make the answer shorter, it makes
it a different answer.

## An episode in a search result

Ordinary search reaches episodes too, and such a row looks unlike the others: `type: "episode"`,
a similarity, and none of the file fields — no path, no excerpt, no structural context. It is not
malformed; it is a memory node surfacing in a corpus query. Read it as a pointer: the material is
in memory, and [memory](memory.md) is where it is retrieved properly.

## The scores — read the shape, not the first row

**Did anything separate the results?** Top value minus bottom value of a field. A clear leader with a
drop behind it means the engine sorted this. Rows within a few thousandths of each other mean it did
not, and the order in front of you is arbitrary — first place in a flat answer is not an answer.

**Which field did the separating?** The fields disagree, in both directions: either can be flat while
another spreads, and they can contradict outright — the row holding the highest `similarity` can hold
the lowest `rerank_score` and sit last. A position is a claim by one measure. Name the measure that
made it before you trust it.

**A flat answer is cured by narrowing the scope, not by rephrasing.** Restrict `folder` / `groups` to
where the material lives. Synonym-hunting changes the wording, not the shape.

| Field | Spread means |
|---|---|
| `rerank_score` | the only scale falling near zero; extremes informative, middle not |
| `similarity` | value stays above ~0.5 even for an absent subject — its **presence** says more than its size |
| `relevance` | can be the separator when the cross-encoder is flat |
| `rrf_score` | a function of POSITION — never read as quality |

Each field's name is its scale; they are never compared against one another, and an absent field was
not measured rather than measured zero. No thresholds here on purpose: a scale moves when its model
is replaced.

**No score says the answer came from the right corpus** — a wrong-corpus hit scores in the same band.
The path separates them, long before any number does.

## A lone number verifies nothing — check it against its neighbour

Before carrying a number out of an answer as evidence, find the other field of the same answer that
constrains it, and see whether the two agree. A count sits next to a rate; a returned figure sits
next to a total; a flag sits next to the thing it describes. Fields that disagree are the answer
telling you one of them is wrong, and that is a fact you can only get from the pair.

A field with no neighbour to check it against is not thereby trustworthy. It is unverifiable, which
is a different thing, and it should leave the answer labelled as such rather than as a measurement.

The pairing that catches this most often is a counter beside a rate derived from it: a rate cannot
be non-zero if nothing was counted, so a zero counter next to a live rate means the zero is wrong.

## `fused` in the hint — a signal from below only, and it is capped

The hint prints `fused: N → limit: M → returned: K`. `N` is the size of the merge, and it is
**bounded above by `4 × limit`**: each arm fetches `limit × branch_candidates_per_result`
(a setting, default 2), and the merge is built from two such lists.

Three consequences, and skipping any of them makes the number lie:

1. **A value at the ceiling is saturation and carries no information.** A nonsense string at
   `limit 3` returned **12 of 12** — the arms hand over their quota for any rubbish.
2. `fused` is comparable across queries only at the same `limit`, and the actual `limit` is
   printed in the hint itself. Check it before comparing, not after. Beyond the ceiling, the pool
   width also decides whether `rrf_min_score` and the vector floor can fire at all — so two
   queries at different limits are incomparable in their CONTENT as well.
3. Below the ceiling it means "at least one arm handed over less than its quota", and there
   are three reasons for that: few documents match by words, vector candidates sit under the
   floor, or the arm was switched off by an explicit `min_similarity`. So "few candidates, the
   corpus does not know this" is a **hypothesis to confirm** with a second query worded
   differently — never a rule.


## `structural_context` — how good it is depends entirely on the material

Each hit carries the section it sits in, the path of parent headings down to it, and the sibling
headings standing beside it. At its best this is a map: you learn where the hit sits in the
document and what neighbours it, and decide whether the rest matters without reading the file.

At its worst it is noise you pay for in every hit. The shape it takes:

| Material | What you get |
|---|---|
| code the extractor parses | function and class names, a true tree — the best case |
| prose with headings | the heading path and a tree of sections — equally good, often better |
| code parsed loosely | an exploded syntax tree: fragments of function bodies and truncated source lines listed as sections |
| shell and similar | first words of lines as section names, repeated once per occurrence |
| data files | the field may be absent altogether |

**Judge it per hit rather than trusting it per corpus.** When the section names read like fragments
of source, it is the parser talking; fall back to reading. When the field is missing entirely, that
is a third outcome and not an error.

**One genre where it costs more than it saves:** a document whose whole body sits under a single
heading — some memory episodes are written this way — puts that same block into both the section
and the heading path. A handful of such hits carries the same text twice, and neither a smaller
`limit` nor fewer neighbouring chunks helps, because the bulk is in the context field rather than
in the excerpt.

## `blast_radius` — the fields that say what a zero means

| Field | What it actually tells you |
|---|---|
| `symbol_found_on_disk` | **reads as a claim about the disk; is a claim about the parser.** A name written in a language with no extractor returns `false` while sitting in the files many times over — `unread` below is what tells you that is what happened |
| `hint` | the one that carries the real reason — that the extension has no extractor, that module-level names are a blind spot. Without it the flag above misleads |
| `caller_count` vs `call_site_count` | distinct callers against distinct places. One caller invoking a symbol three times reads as `1` and `3`; take the first for "one place" and you miss two |
| `definitions` | **count them yourself.** More than one definition of the same name is worth reading whichever language you are in |
| `ambiguous` | fires when a name lives on several *types*. In languages where free functions all sit at module level it stays `false` even with several definitions — so it is not a general duplicate detector |
| `scope_relation` | present on each caller **when a scope was given**. `scope` selects among definitions and cannot select among callers, so the list can hold call sites belonging to other types; this field says which is which |

**Four fields name what the lookup did NOT read, and they are what turns a zero into an answer.**

| Field | What it claims |
|---|---|
| `unread` | an extension with no extractor: `{extension, files, with_the_name}` — how many such files were scanned and how many of them carry your name. A non-zero `with_the_name` means the empty `callers` speaks only for what was read |
| `unparsed` | files that were opened and whose reader gave up, counted per extension. Different from `unread`: there the language is unknown, here the file is |
| `skipped_on_purpose` | parts a reader ignores by design — a docstring, a comment block. Declared rather than left invisible |
| `mentions` · `mention_count` | places where the name stands inside a **string** rather than in a call. Never promoted to a call: what a string means is the caller's business |

A zero beside four empty fields is a zero about the whole folder. A zero beside a non-empty one is
a zero about a part of it, and the field says which part.

**`registrations` and `named_at` — the edge a call graph cannot see.**

Some code is never called by name: it is put into a registry under a string key, and whoever wants
it names the key. `registrations` answers from both ends — ask the symbol and you learn its key,
ask the key and you learn what answers to it. `named_at` is where that key is written in markup,
with `named_at_count` for the total before the list is capped.

**Zero callers beside a registration reads "reached the other way", not "unused".**

**`scope_relation` has three values, and the third is the one that matters.**

| Value | What is known |
|---|---|
| `in_scope` | the call site sits on the type you asked about |
| `defines_its_own` | it sits on another type that defines this same name itself — so it is almost certainly calling its own, not yours |
| `undetermined` | a test class, a helper, or a type that does not define the name at all. The lookup cannot decide, and says so |

`undetermined` is not a gap waiting to be filled. A call site found by name carries no receiver,
so some of them are genuinely undecidable — and they stay in the answer with that label rather
than being dropped. **A filter would have been quieter and worse**: it would delete exactly the
entries nothing can judge, and the list would then look authoritative while being short.

When the list is mixed, `hint` says so. An answer whose callers are all `in_scope` raises no hint
at all — the warning is earned rather than automatic, because one printed on every scoped answer
is how a real one stops being read.

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
