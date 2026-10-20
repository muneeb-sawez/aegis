# Start here — using this pack with Antigravity

## 1. Install the pack
Copy the contents of this pack into the **root of the `aegis` repo** (keep the folder names):
```
aegis/
  AGENTS.md          <- always-on project context
  GEMINI.md          <- pointer to AGENTS.md
  .agent/rules/      <- standing rules (always-on or file-scoped)
  .agent/workflows/  <- week-01 … week-10 + verify-loop (slash commands)
  docs/              <- reference docs the agent reads on demand
```
Open the `aegis` folder as the workspace in Antigravity. If your Antigravity version expects rules/workflows in a different folder name, move them accordingly — the files are plain Markdown and work anywhere you can point the agent at them. Confirm the rules show up in the Antigravity customizations/rules panel.

## 2. First session prompt (paste once)
> Read `AGENTS.md`, every file in `.agent/rules/`, and `docs/02-CONTRACTS.md` and `docs/03-MODULES.md`. Summarise in 10 lines: the Phase 1 goal, the frozen contracts, and the rules you must never break. Then wait for my role and task.

## 3. Daily prompt template
> I am **role [A|B|C|D]**, working on **module [Mx]** for **Week [N]**. Run `/week-0N`, tell me which tasks are mine, list files you'll touch and the exit test, then implement test-first and run the tests.

## 4. Working loop for each task
1. Agent restates task + files + exit test → you approve (Planning mode is a good fit).
2. Agent writes tests, then code, then runs tests/lint.
3. Agent reports pass/fail output. You review the diff.
4. Open a PR; the designated reviewer checks it (see `01-TEAM-AND-PROCESS.md`).
5. Friday: run `/verify-loop`.

## 5. Tips
- One module per agent session/conversation keeps context small and focused.
- If the agent proposes changing a contract, hard-coding a number, or touching Phase 2 — say no and point it to `AGENTS.md` rule list.
- Record anything you decide in `docs/07-DECISIONS.md`.
- Keep API keys in `.env` (never commit). Get a free Gemini or Groq key and install Ollama in Week 1.
