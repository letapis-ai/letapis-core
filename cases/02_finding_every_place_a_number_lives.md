# Case 02 — Finding every place a number lives

A benchmark figure had to be retired. The search quality of the engine had been measured months
of work ago, the measurement was redone on a changed system, and the old numbers now described
something that no longer existed. Before the new table could be published, every place carrying
the old one had to be found and marked superseded.

This is the ordinary "find all occurrences" job, and it is the one where a text match feels
sufficient. It is not, and the way it fails is quiet.

## A literal search found 28 lines in 14 files. Two files were missing.

The figure was `0.9809`. Searching for that string across the project returned 28 lines in 14
files — stage documents, implementation notes, task files, a status page. A complete-looking
answer with no gaps in it.

The two files it did not return were the two written for readers:

| File | How it spells the same number |
|---|---|
| `13_What_Cuts_A_Search_Result` | `0.981` |
| `14_Where_We_Stand_Among_Memory_Systems` | `98.1 %` |

Internal notes quote the instrument, so they carry the raw four-decimal figure. Documents meant
for an audience round and convert. **The two files that would have gone out with a stale number
were exactly the two the literal query could not see** — not by bad luck, but because facing
outward is what causes a document to reformat its numbers.

A semantic query returned both, ranked near the top, because it matches on what a passage is
about rather than on the characters in it.

## The same afternoon, the reverse mistake

The next question was whether the marketing site carried the figure too. Instead of asking the
index, the same literal sweep was pointed at the site's working tree.

The site is an Astro project, so its dependencies sit on disk beside the source: 141 MB in
`node_modules`. A recursive text match walked all of it and returned 238 KB of output — a
README from a TOML parser, some inline SVG icons. The answer to the actual question was in
there somewhere.

The index had no such problem, and the numbers say why:

| | |
|---|---|
| the site's dependency directory, on disk | 141 MB |
| files of that project in the index | 14 |

`node_modules/` is refused by the engine's built-in ignore layer, before any per-folder
configuration is written. A scoped semantic query against that one folder answered in a single
call: the site's figures are `1.4M+ chunks`, `37 tools`, `530+ tests` — no recall or nDCG
anywhere. The number had never been published.

**Both mistakes are the same mistake.** A text match goes past every ignore rule, and that is
precisely its value when proving a name is absent — and precisely its cost when the tree contains
things nobody wrote.

## And a zero that was not a zero

Checking whether an instrument reported a particular condition, a search for the phrase
`вне своей` came back empty across every log file. Empty read as "no instrument reports this".

The logs spell it `ВНЕ своей`, in capitals. Re-run without case sensitivity, the phrase was in
five files. The first answer was not wrong about what it was asked; it was asked the wrong
question, and it had no way to say so.

A literal match returns nothing in two indistinguishable situations: the thing is absent, or the
query does not describe it. Both print the same.

## What the three reaches are for

| | Answers | Blind to |
|---|---|---|
| **meaning** | what a passage is about, whatever words it uses | a name it has no reason to consider relevant |
| **structure** | who calls this symbol, with file and line | anything passed as data rather than called |
| **letters** | the exact characters, anywhere on disk | the same value written differently; drowned by generated files |

Completeness is their intersection, and the retirement above needed two of the three: the semantic
reach to find the documents that had reformatted the figure, and the literal one to enumerate the
exact lines to edit. Either alone would have shipped a stale number.

## Take-aways

Ask the index first, and scope it to a folder. It is one call, it respects the ignore rules, and
it costs no output you have to read past.

When a number or a name is the target, assume it is written more than one way. Percentages,
rounding, thousands separators and locale spelling all break a character match while leaving the
meaning intact.

An empty literal result is a fact about the query. Before concluding the thing is absent, vary the
case, vary the spelling, and ask a second reach.

Keep the text match for what only it can do: proving a name appears nowhere, and enumerating exact
lines once you already know where to look. Point it at a path, not at a tree with a dependency
directory in it.

## Where this is documented

- [Asking a corpus][search]: phrasing, narrowing with a folder filter, the three reaches, and
  reading a result properly.
- [What an answer carries besides its text][response]: the fields that say what the engine
  actually did with the query.
- [What the corpus is made of][corpus]: which layers refuse a file before it is opened.

[search]: ../skills/letapis/references/search.md
[response]: ../skills/letapis/references/response.md
[corpus]: ../skills/letapis/references/corpus.md
