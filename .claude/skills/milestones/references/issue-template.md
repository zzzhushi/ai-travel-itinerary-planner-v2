# GitHub issue template (one per milestone)

Title: `Milestone <n>: <goal demo sentence>`

Body:

```markdown
## Goal
<demo sentence> — from docs/roadmap.md (PRD: docs/prd.md)

## Exit criteria
- [ ] <observable behavior> — proven by `<test id or command>`
- [ ] <...>

## Validation
```bash
# exact commands a human runs to validate, copy-pasteable
```

## Degradation behavior
<external dep> unavailable → <user-visible behavior>

## Tasks
- [ ] T1 (standard/sonnet): <description>
- [ ] T2 (complex/opus, depends: T1): <description>

## Context for cold-start sessions
2–4 sentences: where this milestone sits in the roadmap, what exists before it,
any decisions a fresh session needs to know (link docs/decisions/ ADRs).
```

Mechanics:
- `gh issue create --title "..." --body-file <tmpfile>` — write the body to a temp file; inline `--body` mangles backticks and newlines.
- After creation, record the issue number in docs/roadmap.md.
- The task checklist is updated by `/build-milestone` via `gh issue edit` as work proceeds (or sub-issues if `--subissues` was chosen).
- "Context for cold-start sessions" exists because every future session starts with zero memory of this conversation — write it for a stranger.
