# TOKENS.md — token economy for this project

Priority: stretch usage as far as possible. Chat is disposable; docs are the
memory. Run `/handoff` before anything that discards context.

## When to /clear

Clear whenever the next message doesn't need the current conversation:

- After `/handoff` at any task boundary (module finished, design agreed, bug
  closed).
- When context passes ~50% (`/context` to check) and no active debugging state
  would be lost.
- Before starting a new phase or switching to an unrelated file.
- **Never mid-debug** — reproducing the mental state costs more than the
  context saves. Prefer `/compact <focus instruction>` if forced.

## When to switch models (`/model`)

| Task | Model |
|-|-|
| Phase design, feasibility math, subtle bug stuck >2 rounds, doc handoffs that reshape CLAUDE.md | Opus (or Fable if credits allow) |
| Day-to-day coaching, code review, boilerplate, running checks against data | Sonnet (default) |
| Mechanical: rename sweeps, format checks, running fixtures | Haiku |

Switch **down** immediately after a design is agreed; switch **up** only when
stuck or designing. Switching is free — do it often. Fable draws usage
credits: reserve for genuinely hard reasoning, and `/handoff` + `/clear`
first so it starts with a lean context.

## Standing token rules for Claude (all sessions)

1. Guided-coding mode is itself the biggest saver — Claude never writes large
   files, only diffs/snippets. Keep it.
2. Read files **surgically**: offset/limit and Grep, never whole workbooks or
   whole modules when one function is in question.
3. No subagents unless explicitly asked — each one re-reads context cold.
4. Heavy skills (dataviz, artifact-design, cloudflare:*, ai-integration) are
   **off by default**: do not load them. If one would clearly save effort
   (e.g. a chart of section floors), *ask first*, stating rough cost.
5. Batch questions — one message with all open decisions, not four rounds.
6. Paste-exact errors from the user beat re-running to reproduce.
7. Don't re-read files just edited; don't re-verify what a tool already
   confirmed.

## User-side procedures (proven, popular)

- `/context` regularly; act at ~50%, don't coast to auto-compact (auto-compact
  is an uncontrolled summary — `/handoff` + `/clear` is a controlled one).
- `/compact <instructions>` beats bare `/compact` when you must keep going.
- Disable unused plugins/MCP servers — their tool schemas and instructions are
  loaded every session: `/plugin` → disable **cloudflare** (many skills + MCP
  servers, unused here); `/mcp` → disconnect Gmail/Drive/Calendar connectors
  if not needed for this project.
- Keep CLAUDE.md dense but pruned — it is re-sent with every session; dead
  sections are a per-session tax. `/handoff` prunes as it updates.
- Start each session by naming the one task; avoid open-ended "look around".
