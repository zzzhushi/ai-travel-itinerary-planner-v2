# Roadmap template (docs/roadmap.md)

```markdown
# Roadmap: <product>
PRD: docs/prd.md (approved <date>) · Status: approved <date>

## Milestone overview
| # | Goal (demo sentence) | Risk it retires | Issue |
|---|---|---|---|
| 0 | Scaffolding: repo runs tests/lint/CI green | none (foundation) | #_ |
| 1 | <user-visible demo sentence> | <assumption tested> | #_ |

## Milestone <n>: <goal>
**Demo:** <one sentence a human can perform and judge>
**Exit criteria:**
- [ ] <observable behavior> — proven by `<test id or command>`
- [ ] <observable behavior> — proven by `<...>`
**Validation steps:** exact commands/clicks, copy-pasteable.
**Degradation:** <new external dep> down → <user-visible behavior>.
**Architecture notes:** decisions made for this slice (mirrored to docs/decisions.md).

**Tasks:**
| id | task | complexity | model | why | depends_on |
|---|---|---|---|---|---|
| 1 | <imperative description> | standard | sonnet | follows pattern X | — |
| 2 | ... | complex | opus | novel ranking logic, ambiguity in tie-breaks | 1 |
```

Author notes:
- The demo sentence is the forcing function for vertical slicing — write it first; if you can't, the slice is wrong.
- Exit criteria must each name their proof. An exit criterion nobody can check is a wish.
- Keep milestone count honest: 4–8 milestones for a small product. Twenty milestones means slices are too thin to demo meaningfully.
```
