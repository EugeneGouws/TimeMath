---
name: handoff
description: Session handoff — sync .md docs with what this session established, then recommend /clear and a model for the next task. Invoke at task boundaries, before /clear, before model switch, or when context usage feels high. Keeps docs the single source of truth so a fresh session loses nothing.
---

# Handoff

Purpose: everything durable lives in the repo docs, nothing lives only in chat.
Then the chat is disposable — /clear is free.

## Steps (in order)

1. **Harvest this session.** List facts established, decisions made, code
   written/reviewed, bugs found, beliefs corrected. Only durable items — skip
   anything derivable from the code itself.
2. **Update CLAUDE.md**, minimal diff:
   - New facts → correct section, tagged with provenance tier
     (Solid / Solid (new) / Provisional) per the existing convention.
   - Corrected beliefs → "Corrections to earlier beliefs" section.
   - Resolved open questions → remove from "Open questions".
   - Rewrite "Current state" to reflect now: what is done, what is next,
     what blocks it.
3. **Update docs/PLAN.md / PRODUCT.md** only if approach or scope changed.
4. **Do not duplicate** — no new doc files, no memory entries repeating repo
   docs. Terse prose, match existing style.
5. **Print handoff summary** to user, exactly this shape:

   ```
   Docs updated: <files + one-line what>
   Next task: <one line>
   Recommend: /clear [yes/no + why]
   Recommend model: <model + why>   (see docs/TOKENS.md rules)
   ```

## Rules

- Written docs are normal prose (caveman mode never applies to files).
- If session established nothing durable, say so and change no files.
- Never delete provenance tags or weaken a Provisional item to Solid without
  a derivation from raw data.
