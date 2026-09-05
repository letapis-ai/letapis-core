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


## `structural_context` — where the excerpt sits, and whether the page goes on

Every hit is an EXCERPT, and nothing in its text says so. Read one as though it were the whole
page and you will write, in perfect good faith, things the page does not say — the commonest way
a summary drifts from its source, and one that rereading the summary never catches. This field is
what tells you otherwise, and it arrives without being asked for.

| Key | What it says |
|---|---|
| `section` | the nearest heading above the excerpt, **at whatever level** — on a page with subheadings this is the subheading, not the section a reader would say it belongs to |
| `section_path` | the chain of enclosing headings down to that one, starting at the page title when the page has one |
| `position` | `"7 of 43"` — the heading above the excerpt is the 7th of the page's 43. It counts headings, not text: "1 of 3" can be nine tenths of the page or two lines |
| `after` | the next heading in the outline — and it is **often a subheading INSIDE your own section** rather than the next section beside it: the outline is one flat list holding every heading of every level, and the answer never says which level an entry has. Read it as "there is more, and it is called X", never as "your section has ended" — and when the heading really is nested inside yours, `after_is_inside_this_section` says so |
| `before` | the previous heading in the outline — **often the heading that CONTAINS your excerpt**, in which case it repeats the second-to-last name in `section_path`. Not necessarily a section beside yours either |
| `section_continues` | `true`, and never anything else: the excerpt stopped before its own section did |
| `after_is_inside_this_section` | `true`: the heading `after` names is nested inside the excerpt's own section, so that section has NOT ended |
| `section_end_unknown` | `true`: the excerpt carried no end line, so whether it read its section out was never established |
| `outline_truncated` | `true`: the stored outline hit the 2000-heading cap, so every count in this field covers a PART of the file |

**`after` is the one to read first.** `"7 of 43"` with an `after` naming a heading you have not
seen means you are holding a fragment. Deciding to open the file is what this field is for.

### The outline is one flat list, so `after` can be inside your own section

The index stores one entry per heading, every level in the same list, in the order the document
writes them. A `###` sits in that list next to the `##` above it, and the answer never says which
level an entry has. `before` and `after` are simply the entries either side of yours.

So one `after` covers two situations that read nothing alike on the page:

```
## Shift handover            <- the excerpt is here, and `section` names this
...
### Checking the shift log   <- `after` names THIS: a subheading of your own section
...
## Escalation                <- on another page, `after` would name a heading like this
                                one instead: the next section beside yours
```

`before` mirrors this from the other side, and there the giveaway is visible: for an excerpt under
a subheading, the previous entry in the outline is the heading that CONTAINS it, so `before`
repeats the second-to-last name in your own `section_path`. That is the outline being read in
document order, not a duplicate.

Both `after` cases come back as a bare string, and nothing distinguishes them.
`after: "Checking the shift log"` does not say the page has moved on from shift handover — it says the next heading in the file is
that one, and here it is part of what you were reading. Read `after` as "there is more, and it is
called X", never as "your section has ended".

**What ends a section is decided by the outline of the material, and in markdown any heading ends
the one before it.** So `section_continues` compares your excerpt against the text up to the NEXT
HEADING, not up to the end of the `##` block a reader would call the section. On a page with
subheadings, no `section_continues` means "you read as far as the next heading" — which can be a
small part of the section as the page reads. In parsed code, where the outline genuinely nests, a
class runs to the end of the class and the key means what it looks like.

### Three keys arrive only when the obvious reading is wrong

`after_is_inside_this_section`, `section_end_unknown` and `outline_truncated` are marks, not
descriptions. Each is present in one state and absent in the other, and the state it marks is the
one where the reading a stranger brings to the answer is false:

| You see | It means | Without it |
|---|---|---|
| `after_is_inside_this_section: true` | the next heading is nested in your own section — it has not ended | `after` is the section beside yours, which is what you assumed |
| `section_end_unknown: true` | there was no end line to compare, so nobody asked whether you read the section out | you read it out (or `section_continues` says you did not) |
| `outline_truncated: true` | the outline was cut at the cap; counts here cover part of the file | the outline is the whole file |

They are never sent as `false`. That is deliberate rather than an omission: the unmarked reading
holds on the great majority of hits, and a key saying so on every hit of every answer would buy
a reader nothing except the confirmation of what they already had right. The label is spent where
it changes an answer.

Which also means the silence is doing work, and copying these keys into your own summary as
`false` throws that work away.

**How you can tell what a missing key means differs between them, and one way is sturdier than
the other.** For `section_end_unknown` and `outline_truncated` the keys around them move with the
state: `section_continues: true` on a neighbouring hit, `position` shifting to `"8 of at least
2000"` — an empty place is legible against a full one.

`after_is_inside_this_section` has no such neighbour. `after` reads the same in both worlds, and
nothing else in the answer moves with it, so its absence is readable on one thing only: the key's
name makes sense the first time you meet it. A name comes with the answer; this page has to have
been read beforehand. If you have never seen the key, you read `after` as the next section along
— which is right — and the day the key does appear, it tells you the rest without sending you
here.

That is the thinner of the two grounds, and it is a bet on the name being obvious rather than an
argument. Worth knowing which of the two you are relying on when you read an absence.

**A key you cannot see is the part to get right.** Each one goes missing in more states than the
one it was added for, and the second state is where a confident misreading comes from:

| Key | Absent when | What its absence does NOT say |
|---|---|---|
| `section`, `section_path` | the excerpt sits above the page's first heading — frontmatter, a preamble — and in no other case | not that the page is unstructured |
| `position` | never, as long as the field itself is there. Above the first heading it takes its other shape, `"start of page, 43 sections"` | — |
| `before` | this IS the page's first heading, or the excerpt sits above it | not that no text precedes the excerpt |
| `after` | no FURTHER HEADING follows in the stored outline — and `outline_truncated` beside it tells you whether "stored" and "in the file" are the same thing here | **not that the page ends here.** Body text under the last heading runs on for as long as it likes, and nothing in this field measures it |
| `section_continues` | the excerpt reached its section's end — or it has no enclosing section at all, being above the first heading. The third old state now answers for itself: no end line to compare against arrives as `section_end_unknown: true` | above the first heading, not that anything was checked |

A corpus indexed by an older engine is where the missing end line comes from; on anything a
current engine indexed the line is there, so `section_end_unknown` is a mark you will rarely see
and should trust completely when you do.

**The outline is stored up to 2000 headings per file, and past that limit every count here covers
part of the file.** `position`, and whether there is an `after` at all, are over the STORED
headings rather than the page's. The answer says when that has happened:

- every hit from it carries `outline_truncated: true`, and `position` states what it actually
  knows: `"8 of 2500"` where the file's heading count was stored, `"8 of at least 2000"` where it
  was not — an index written before the count existed reads the outline stopping exactly at the
  cap and reports a floor rather than a number it cannot back.
- an excerpt from PAST the cut is not placed at all. It carries `outline_truncated: true` and
  `position: "past the 2000 stored headings"`, and no `section`, `before`, `after` or
  `section_continues` — because nothing about where it sits is known.

That second case used to be the field's one outright lie: the excerpt was anchored on the last
stored heading and came back with somebody else's `section`, `"2000 of 2000"`, and neither
`after` nor `section_continues` — "the page's last section, read out, nothing follows" with
hundreds of headings still to come.

One false positive is left and it is declared: a file holding exactly 2000 headings, indexed
before the count was stored, is reported as cut. It is a generated file either way — an export, a
merged changelog — and reindexing it makes the answer exact.

**The whole field can be absent, and that is a different fact from a missing key.** It happens
when the hit IS the file rather than a piece of it — a whole-file hit has no place inside the
file, so there is nothing to name; when the file has no headings for a reader to be placed among,
which is the ordinary answer for data files; when the corpus was indexed before outlines were
stored and has none to answer from; and when the lookup that fetches them fails. None of these is
an error, and none of them says the page is short.

### It describes the page's shape, and nothing about what is written there

Every key here is about SHAPE: which headings the page has, how many, which one the excerpt fell
under. None of them is about the text inside those sections. The one piece of content that does
leak through is a heading's wording, and a heading is the label the author chose for a section,
not a description of what ended up in it.

That distinction is easy to lose, because the field arrives looking like knowledge. Holding
`position: "1 of 3"` and `after: "Escalation"`, it is a short step to a confident-sounding claim
about a page never opened: that the material is short, that some subject is not covered, that the
rest of it is about escalation. Nothing in the answer supports any of that. `position` counts
headings rather than lines, so "1 of 3" measures no proportion of anything; and a heading is a
promise the section may or may not keep.

This is a failure that has actually happened: a reader who would otherwise have opened the page,
or said nothing at all, instead built a statement on `"1 of 3"` about content they had never
seen. The field answers one question — is this an excerpt, and does the page go on — and the
move it is there to prompt is opening the file. If you catch yourself saying what an unread
section contains, this field did not tell you.

**How good the naming is depends entirely on the material:**

| Material | What you get |
|---|---|
| code the extractor parses | function and class names, a true tree — the best case |
| prose with headings | the heading path and the page's own sections — equally good, often better |
| code parsed loosely | an exploded syntax tree: fragments of function bodies and truncated source lines listed as sections |
| shell and similar | first words of lines as section names |
| data files | the field may be absent altogether |

**Judge it per hit rather than trusting it per corpus.** When the section names read like fragments
of source, it is the parser talking; fall back to reading.

`structural_context: false` switches the whole field off, and that also spares the one extra store
round-trip it costs. Worth doing when you are scanning a list of paths and never intend to read a
hit through.

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
