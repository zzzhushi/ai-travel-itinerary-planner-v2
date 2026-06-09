---
name: prd-builder
description: Product Requirements Document creation and feature specification writing. Use when writing PRDs, technical specs, feature documentation, or requirements. Triggers on "PRD", "product requirements", "feature spec", "technical requirements", "functional spec".
allowed-tools: web-search, read, write, grep
model: opus 
---

# PRD Generation Protocol

## Trigger Conditions
- Trigger when the user uses `/prd`, says "write a product document", "create a spec", or requests feature definitions.

## Operational Flow

### Phase 1: Gather context
Do not generate the PRD immediately. Collect essential information through a discovery conversation:

**Required Information:**
- **Feature/Product Name**: What are we building?
- **Problem Statement**: What problem does this solve?
- **Target Users**: Who is this for?
- **Business Goals**: What are we trying to achieve?
- **Success Metrics**: How will we measure success?
- **Timeline/Constraints**: Any deadlines or limitations?

**Discovery Questions to Ask:**

```
1. What problem are you trying to solve?
2. Who is the primary user/audience for this feature?
3. What are the key business objectives?
4. Are there any technical constraints we should be aware of?
5. What does success look like? How will you measure it?
6. What's the timeline for this feature?
7. What's explicitly out of scope?
```

**Note:** If the user provides a detailed brief or requirements upfront, you can skip some questions. Always ask for clarification on missing critical information.

### Phase 1.5: Surface latent requirements (do NOT rely on the user to list everything)

Enumerating features is YOUR job, not the user's — their job is to triage what you surface.
Relying on the user to remember every feature up front defeats the purpose of discovery.
Before writing the PRD, actively generate candidate requirements via all three techniques,
then raise the strongest ones one at a time (each with a recommended answer):

1. **Persona role-play.** Derive 2–3 personas from the domain — the primary user AND at least
   one adjacent expert plus a returning power user (e.g. travel planner → traveller, travel
   agent, repeat user). Walk the core flow as each; note what they'd reach for that's missing.
2. **Coverage checklist.** Sweep for commonly-forgotten gaps:
   - Editing & lifecycle: create / update / delete / undo / duplicate the core entities?
   - Multiplicity & scale: one vs many? behaviour at 10× usage?
   - Time: fixed vs flexible items, durations, recurrence, time zones, ordering constraints.
   - Money: cost / budget / limits.
   - Fixed/external anchors: things the user cannot move (bookings, appointments).
   - Errors & edges: empty, oversupply, conflicting, unavailable, partial data.
   - Personalisation & accessibility; multi-user / sharing; import / export / integrations.
3. **Pre-mortem / 10×:** "After 3 real uses, what will you wish it did?" /
   "What missing piece makes this useless in practice?"

Triage EACH candidate with the user: MVP / Next / Later / No. Keep it proportional — surface
the strongest few and offer to go deeper rather than interrogating every category every time.
Record everything not in the MVP in the PRD's **Future Requirements** parking lot (see below)
so nothing is lost.

### Phase 2: Document Structure
Once details are aligned, generate a Markdown PRD utilizing this exact structural framework:

Use the standard PRD template from `references/prd_template.md` to create a well-structured document. The PRD should include:

1. **Executive Summary** - High-level overview (2-3 paragraphs)
2. **Problem Statement** - Clear articulation of the problem
3. **Goals & Objectives** - What we're trying to achieve
4. **User Personas** - Who we're building for
5. **User Stories & Requirements** - Detailed functional requirements
6. **Success Metrics** - KPIs and measurement criteria
7. **Scope** - What's in and out of scope
8. **Technical Considerations** - Architecture, dependencies, constraints
9. **Design & UX Requirements** - UI/UX considerations
10. **Timeline & Milestones** - Key dates and phases
11. **Risks & Mitigation** - Potential issues and solutions
12. **Dependencies & Assumptions** - What we're relying on
13. **Open Questions** - Unresolved items

### Phase 3: Create User Stories

For each major requirement, generate user stories using the standard format:

```
As a [user type],
I want to [action],
So that [benefit/value].

Acceptance Criteria:
- [Specific, testable criterion 1]
- [Specific, testable criterion 2]
- [Specific, testable criterion 3]
```

Reference `references/user_story_examples.md` for common patterns and best practices.

### Phase 4: Define Success Metrics

Use appropriate metrics frameworks based on the product type:

- **AARRR (Pirate Metrics)**: Acquisition, Activation, Retention, Revenue, Referral
- **HEART Framework**: Happiness, Engagement, Adoption, Retention, Task Success
- **North Star Metric**: Single key metric that represents core value
- **OKRs**: Objectives and Key Results

Consult `references/metrics_frameworks.md` for detailed guidance on each framework.

## PRD Best Practices

### Writing Quality Requirements

**Good Requirements Are:**
- **Specific**: Clear and unambiguous
- **Measurable**: Can be verified/tested
- **Achievable**: Technically feasible
- **Relevant**: Tied to user/business value
- **Time-bound**: Has clear timeline

**Avoid:**
- Vague language ("fast", "easy", "intuitive")
- Implementation details (let engineers decide how)
- Feature creep (stick to core requirements)
- Assumptions without validation

### User Story Best Practices

**DO:**
- Focus on user value, not features
- Write from user perspective
- Include clear acceptance criteria
- Keep stories independent and small
- Use consistent format

**DON'T:**
- Write technical implementation details
- Create dependencies between stories
- Make stories too large (epics)
- Use internal jargon
- Skip acceptance criteria

### Scope Management

**In-Scope Section:**
- List specific features/capabilities included
- Be explicit and detailed
- Link to user stories

**Out-of-Scope Section:**
- Explicitly state what's NOT included
- Prevents scope creep
- Manages stakeholder expectations
- Can include "future considerations"

**Future Requirements parking lot:**
- Every candidate surfaced in Phase 1.5 (or later) that isn't in the MVP goes here — never
  discard a deferred idea, park it.
- Give each a one-line verdict: **MVP / Next / Later / No**, plus a one-line disposition
  (where it would plug in, or why it's deferred). A compact table works well.
- This is the durable home for "good idea, not now" so the next session can pick it up.

### Success Metrics Guidelines

**Choose Metrics That:**
- Align with business objectives
- Are measurable and trackable
- Have clear targets/thresholds
- Include both leading and lagging indicators
- Consider user and business value

**Typical Metric Categories:**
- **Adoption**: How many users use the feature?
- **Engagement**: How often do they use it?
- **Satisfaction**: Do users like it?
- **Performance**: Does it work well?
- **Business Impact**: Does it drive business goals?


## Guardrails
- If a requirement cannot be verified by an automated integration test, flag it as "Ambiguous" and prompt the user to re-define.
- Always check if an existing PRD or `CLAUDE.md` file covers this feature scope before appending new documentation.
