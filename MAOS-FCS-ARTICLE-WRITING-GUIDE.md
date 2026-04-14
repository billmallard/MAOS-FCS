# AeroCommons Article Writing Guide — For MAOS-FCS Claude Instance

This document teaches you how to write and structure articles for the AeroCommons website. You cannot push files directly — your output will be copied by a human and placed into the repository. Write clean, complete markdown files that can be dropped in verbatim.

---

## How the site works

AeroCommons is a Hugo static site that publishes to `aerocommons.org`. The repository is at GitHub. A Cloudflare Pages build runs automatically on every push — no human approval required. An article appears live within ~60 seconds of being pushed.

All articles live in `content/articles/`. You produce a single `.md` file. A human copies it into that directory and pushes.

---

## File naming

```
YYYY-MM-DD-short-title.md
```

Examples:
```
2026-04-13-fcs-actuator-selection.md
2026-04-14-maos-fcs-sensor-redundancy.md
2026-04-15-fly-by-wire-control-law-architecture.md
```

Rules:
- Date first, always, in `YYYY-MM-DD` format
- Lowercase only, hyphens only — no spaces, no underscores, no special characters
- Keep the slug short (4–6 words is ideal)
- One file = one article

---

## Required front matter

Every article starts with a YAML block between `---` markers. **This must be exact — the site will not render correctly without it.**

```yaml
---
title: "Your Full Article Title Here"
date: 2026-04-13T10:00:00-06:00
description: "One sentence. Shown in article cards and meta tags. Make it specific and precise."
tags: ["tag-one", "tag-two", "tag-three"]
author: "MAOS Design Board"
summary: "Two-sentence summary for article cards. More detail than description. What was asked, what was decided."
project: "maos"
article_type: "design"
draft: false
---
```

### Field reference

| Field | Required | Notes |
|---|---|---|
| `title` | Yes | Full human-readable title. Always use quotes. |
| `date` | Yes | ISO 8601 with timezone. Use `-06:00` for US Central. |
| `description` | Yes | One sentence. Appears in article cards and `<meta>` tags. |
| `tags` | Yes | Array of lowercase hyphenated tags. See tag list below. |
| `author` | Yes | Use `"MAOS Design Board"` for FCS board sessions. |
| `summary` | Recommended | Two sentences for the article card excerpt. More detail than description. |
| `project` | **Yes** | Must be `"maos"` for all FCS work. |
| `article_type` | **Yes** | See article types below. |
| `session` | No | Board session ID if applicable, e.g. `"BOARD-007"`. |
| `draft` | Yes | `false` to publish. `true` to commit without displaying on site. |

#### article_type values

| Value | When to use |
|---|---|
| `"design"` | Design decisions, architecture discussions, board sessions, trade studies with a closure |
| `"analysis"` | CFD, structural, thermal, control law derivations, or other technical analysis outputs |
| `"build-log"` | Build progress, fabrication notes, test stand results |
| `"methodology"` | Process documentation, how-tos, workflow guides |
| `"announcement"` | Milestone updates, status changes, program announcements |

For FCS board sessions, use `article_type: "design"`.

---

## Standard tags

Use these consistently. Multiple tags are expected.

**Meta tags:**
```
board-meeting         — formal board sessions
design-decisions      — records of closed decision gates
analysis              — CFD, structural, thermal, or other analysis outputs
build-in-public       — transparent design process documentation
```

**Technical domain tags:**
```
propulsion            — propulsion system topics
structures            — airframe and structural topics
aerodynamics          — aero analysis and stability
systems               — avionics, ECS, electrical
avionics              — electronics, sensors, flight control
electric-aviation     — electric propulsion, motors, controllers
hybrid-electric       — series/parallel hybrid architectures
manufacturing         — build process and tooling
safety                — safety analysis and fail-safe design
```

**Specialized tags relevant to FCS work:**
```
fly-by-wire           — FBW architecture and control law topics
flight-controls       — control surface actuation, linkages, servo selection
redundancy            — failure tolerance, backup channel design
sensors               — sensor selection, IMU, air data, GPS
actuators             — servo/actuator selection and integration
control-laws          — control law derivation, gain scheduling
simulation            — X-Plane, HIL, SIL, digital twin
systems-engineering   — requirements, interface control, gate criteria
experimental          — experimental aircraft methodology
regulatory            — FAA, certification, owner-produced parts
```

For FCS board sessions: always include `board-meeting` plus relevant technical domain tags.

---

## Article body format

After the front matter, write standard markdown. The site renders:

- `## Heading` and `### Subheading` (use these liberally — readers skim)
- `**bold**` and `*italic*`
- Bullet and numbered lists
- Tables (GitHub-flavored markdown table syntax)
- `` `inline code` `` and fenced code blocks
- `> blockquotes` — styled prominently
- `---` horizontal rules as section breaks

---

## Recommended structures by article type

### Board session / design decision

Use this structure for any FCS board meeting note or architectural decision article.

```yaml
---
title: "MAOS FCS Board Meeting XXX — [Topic]"
date: 2026-04-13T10:00:00-06:00
description: "One-sentence summary of the primary conflict or decision."
tags: ["board-meeting", "flight-controls", "design-decisions", "systems-engineering"]
author: "MAOS Design Board"
summary: "Two-sentence summary covering what was discussed and what was decided."
project: "maos"
article_type: "design"
session: "BOARD-XXX"
draft: false
---
```

**Body structure:**

```markdown
## Session Overview

**Date:** YYYY-MM-DD  
**Session ID:** BOARD-XXX  
**Agents present:** [list agents — e.g., Chairman, FCS, AERO, SYSTEMS]  
**Status:** Complete — decisions recorded

Brief one-paragraph summary of the session.

---

## Decisions Closed This Session

### 1. Decision Name

**Decision:** One sentence stating the decision.

**Rationale:** Why this was selected over alternatives. Use as many paragraphs as needed.

**Dissenting notes:** Any unresolved concerns from a specialist agent (optional — omit if none).

---

## Open Gates After This Session

| Gate | Description | Current Recommendation | Priority |
|---|---|---|---|
| GATE-XXX | Description | Recommendation | High/Medium/Low |

---

## Next Session Agenda

- Item one
- Item two
```

---

### Technical analysis article

Use this for control law derivations, sensor trade studies, actuator comparisons, simulation results, etc.

```yaml
---
title: "Descriptive Title of the Analysis"
date: 2026-04-13T10:00:00-06:00
description: "One sentence stating what was analyzed and the key finding."
tags: ["analysis", "flight-controls", "relevant-tag"]
author: "MAOS Design Board"
summary: "Two sentences: what question was being answered, and what the answer was."
project: "maos"
article_type: "analysis"
draft: false
---
```

**Body structure:**

```markdown
## Problem Statement

What question was being answered. What constraint or decision this analysis was supporting.

---

## Method

What approach was used. Tools, assumptions, simplifications.

---

## Results

Quantitative outputs. Use tables where applicable. Do not hide the numbers.

| Parameter | Value | Notes |
|---|---|---|
| ... | ... | ... |

---

## Interpretation

What the results mean for the design. What they do and do not prove.

---

## Effect on Open Gates

Which gates this analysis bearing on. What has changed.
```

---

## Voice and tone

AeroCommons articles are technical and direct. These norms apply to all articles:

- **Write for a competent engineer, not a beginner.** Do not over-explain standard concepts.
- **State decisions plainly.** "MAOS selects X" is better than "it appears that X may be appropriate."
- **Show the numbers.** Vague qualitative claims without data are weak. Use tables.
- **Acknowledge trade-offs.** Readers lose trust in analysis that only argues one side.
- **Avoid preamble.** The first sentence should carry information, not context-setting.
- **Use horizontal rules (`---`) to separate major sections.** Readers skim.
- **Attribute dissent.** If an agent or reviewer flagged a concern, record it — even if the decision went the other way.

---

## Attribution conventions

| Situation | Use in `author` field |
|---|---|
| Standard FCS board output | `"MAOS Design Board"` |
| Output primarily from one agent | `"MAOS Design Board"` — note agent in body |
| Authored directly by Bill | `"Bill (Builder)"` |
| Cross-project or community content | `"AeroCommons"` |

Do not invent author names. If in doubt, use `"MAOS Design Board"`.

---

## Draft vs. publish

Set `draft: false` to make the article visible on the site.  
Set `draft: true` to push to the repository without showing it on the live site. Use this when the content is complete but pending human review.

**Default to `draft: false`** for FCS board sessions and analysis articles unless instructed otherwise.

---

## Complete working example

This is a complete, ready-to-file article demonstrating the format:

```markdown
---
title: "MAOS FCS Actuator Architecture: Redundancy Channel Selection"
date: 2026-04-13T11:00:00-06:00
description: "FCS board closes actuator redundancy strategy: dual-channel EMA on primary surfaces, single-channel with mechanical reversion on secondary surfaces."
tags: ["board-meeting", "flight-controls", "actuators", "redundancy", "design-decisions"]
author: "MAOS Design Board"
summary: "The FCS board evaluated three actuator redundancy strategies across primary and secondary control surfaces. Dual-channel EMA on primary surfaces with mechanical reversion on secondary surfaces was selected as the minimum viable fail-safe architecture."
project: "maos"
article_type: "design"
session: "BOARD-012"
draft: false
---

## Session Overview

**Date:** 2026-04-13  
**Session ID:** BOARD-012  
**Agents present:** Chairman, FCS, SYSTEMS, AERO  
**Status:** Complete — decisions recorded

The board reviewed three actuator redundancy strategies for primary and secondary flight controls. One strategy was closed. Two open gates related to surface hinge moments were deferred pending AERO analysis.

---

## Decision Closed

### FCS-ACT-001: Primary Surface Actuator Redundancy Strategy

**Decision:** Dual-channel EMA (electromechanical actuator) on primary surfaces (aileron, elevator, rudder). Single-channel EMA with mechanical reversion on secondary surfaces (flaps, trim tabs).

**Rationale:** Dual-channel EMA provides independent power and signal paths. A single-channel failure leaves full primary control authority via the surviving channel. Secondary surface failure modes are lower criticality; mechanical reversion provides a known fallback at lower system complexity.

**SYSTEMS agent note:** Dual-channel EMA requires two independent power buses reaching each primary actuator. This has been accepted as a routing constraint. Bus separation architecture is addressed in GATE-015.

---

## Open Gates After This Session

| Gate | Description | Current Recommendation | Priority |
|---|---|---|---|
| GATE-015 | Primary actuator bus separation routing | Awaiting SYSTEMS layout | High |
| GATE-016 | Elevator hinge moment at Vd | Awaiting AERO analysis | High |
| GATE-017 | Aileron reversal speed margin | Awaiting AERO analysis | Medium |

---

## Next Session Agenda

- Review AERO outputs for GATE-016 and GATE-017
- Close FCS-ACT-002: actuator supplier selection
```

---

## What to hand off to the human

When you produce an article, output:

1. **The filename** — e.g., `2026-04-13-fcs-actuator-selection.md`
2. **The complete file contents** — front matter through end of body, ready to copy verbatim

Do not summarize the article separately. Do not add instructions around the file output. The human needs exactly one thing: a clean file they can paste and push.
