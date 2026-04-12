# MAOS-FCS Weekly Roll-Up Report Template

Automation option: see [Weekly Roll-Up Automation](weekly_rollup_automation.md) to auto-generate a prefilled report.

Reporting period: YYYY-MM-DD to YYYY-MM-DD
Report owner: <name>
Portfolio project: MAOS-FCS: Flight Control Systems

## 1) Executive Summary

Overall status: Green | Yellow | Red

This week in one paragraph:
- Briefly summarize major outcomes, key blockers, and next focus.

## 2) Portfolio Snapshot (EPIC Roll-Up)

Use one line per EPIC parent issue.

| EPIC | Status | Sub-issues Done/Total | Trend vs last week | Target date | Notes |
|---|---|---:|---|---|---|
| #17 EPIC P0-A | In progress | X/5 | Up/Flat/Down | YYYY-MM-DD | |
| #18 EPIC P0-B | In progress | X/3 | Up/Flat/Down | YYYY-MM-DD | |
| #19 EPIC P0-C | In progress | X/4 | Up/Flat/Down | YYYY-MM-DD | |
| #20 EPIC P0-D | In progress | X/3 | Up/Flat/Down | YYYY-MM-DD | |

## 3) Completed This Week

- Issue #<n>: <title> (why it matters)
- Issue #<n>: <title>
- Issue #<n>: <title>

## 4) In Progress and Next Up

In progress:
- Issue #<n>: <title>, owner, expected completion
- Issue #<n>: <title>

Next up:
- Issue #<n>: <title>
- Issue #<n>: <title>

## 5) Risks and Blockers

| Risk/Blocker | Impact | Mitigation | Owner | ETA |
|---|---|---|---|---|
| <short description> | Low/Med/High | <plan> | <owner> | YYYY-MM-DD |

## 6) Metrics

Core metrics:
- Open P0 issues: <count>
- Closed this week: <count>
- New issues this week: <count>
- EPIC completion: P0-A <x%>, P0-B <x%>, P0-C <x%>, P0-D <x%>

Quality indicators:
- Reopened issues: <count>
- Infra fails vs test fails (if available): <ratio>

## 7) Decisions Needed

- Decision: <question>
  - Options: <a>, <b>, <c>
  - Recommended: <option>
  - Needed by: YYYY-MM-DD

## 8) Next Week Commitments

- Commit 1: <outcome statement>
- Commit 2: <outcome statement>
- Commit 3: <outcome statement>

## Optional Appendix: Copy/Paste Query Cheatsheet

Example issue list query:

```powershell
gh issue list --state open --search "P0-" --json number,title,url
```

Example project snapshot query:

```powershell
gh project item-list 4 --owner billmallard --format json
```
