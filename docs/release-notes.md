# Release notes

**Reindex every watched folder after installing this version.** Text is cut differently: chunks
that carried no content at all are no longer produced. Nothing already stored is lost, but it
answers from the older cut until the folder is read again — run `force_reindex` on each one.

Reindexing is not automatic and will not happen on its own. A file indexed by an earlier engine
carries no record of what cut it, and the engine treats that silence as "leave it alone" rather
than as "re-cut everything": the alternative would rebuild an entire corpus, silently, on the
first pass after an update.

## What changed

- **A chunk is no longer allowed to be made of nothing.** A boundary that would leave a stretch
  with not one word of content in it is refused, and the cut falls elsewhere. Such a chunk is
  near-identical across every document of a corpus — a document's front matter, a licence header,
  a closing brace — so it matches every question equally well and pushes the real answer down the
  list. **No text is dropped by this:** the seam moves, the file is still covered end to end.

  Measured on our corpora: markdown went to 72 contentless chunks out of 43 346 (0.17 %), and
  C++ from 378 to 147 over 200 files of `or-tools`.

- **The rule reads the text, not a list of node names.** A marker names what it *proposes*, not
  what a chunk *contains* — a tail left over from a node spanning the whole file is a legitimate
  node by type and two braces by content. So a language declares which of its atoms are labels
  rather than content, those are set aside, and what remains is asked one question: is there a
  word here. The ruler, which places a boundary when the markup offers none, now asks it too.

- **A chunk records the cutter that produced it.** The record is `<handler>=<version>`, and a
  file is read again when its handler's version changes — only the share of the corpus that
  handler owns, not the whole of it. **Rebuilding or updating the engine re-cuts nothing:** the
  number is raised deliberately, when the cut has actually changed, and never as a side effect of
  a release.

## Known limits of this version

- A service header longer than the chunk budget still yields a chunk without content, because
  there is nothing within the budget to attach it to. Measured on `or-tools`: 95 of the remaining
  147.
- PDF and Word files are cut by length alone and take no part in the rule above.
- Files indexed before this version carry no cut record and are not re-read automatically. See
  the note at the top.
