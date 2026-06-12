---
name: ship
description: Turn a completed milestone branch into a reviewed, merged PR. Use when a milestone's exit criteria pass and work is ready to land ("ship it", "create the PR", "let's merge milestone N").
---

# Ship: PR → Review → Merge (HITL)

## Preconditions (verify, don't assume)

All exit-criteria tests green on the milestone branch; issue checklist current; branch pushes cleanly on top of latest main (rebase or merge main first if it moved, then re-run the full suite).

## 1. Create the PR

```bash
git push -u origin <branch>
gh pr create --title "Milestone <n>: <goal>" --body-file <tmpfile>
```

Body (write to temp file — inline `--body` mangles formatting): **What** (2–3 sentences), **Why** (one sentence linking the milestone goal), **Validated** (exit criteria + how each was proven, including manual validation results), `Closes #<milestone-issue>`. No play-by-play, no file-by-file narration — the diff shows the what; the body carries what the diff can't.

## 2. Review

Run the built-in `/code-review` and `/security-review` on the branch. Triage findings honestly: fix accepted ones (as additional commits with the same message discipline), and list disputed/deferred ones in a PR comment with one-line reasoning — silent dismissal of a finding is corner-cutting.

## 3. Human gate

Present to the user: PR link, validation summary, review findings and how each was handled, anything you're uncertain about. **Merging is the user's decision.** On approval:

```bash
gh pr merge --squash --delete-branch
```

Confirm the milestone issue auto-closed; update `docs/roadmap.md` status. If `/retro` hasn't run for this milestone, suggest it now — retro findings are freshest before the next milestone starts.
