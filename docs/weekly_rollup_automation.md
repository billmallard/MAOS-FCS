# Weekly Roll-Up Automation

This page explains how to generate the portfolio weekly report automatically from GitHub issues and project data.

## Script Location

- tools/reporting/generate_weekly_rollup.ps1

## Default Behavior

When run with defaults, the script:

- Reads EPIC progress from issues #17, #18, #19, #20
- Uses repository billmallard/MAOS-FCS
- Computes a 7-day reporting window ending today
- Writes output to docs/weekly_rollup_report.md

## Run Command

```powershell
powershell -ExecutionPolicy Bypass -File tools/reporting/generate_weekly_rollup.ps1
```

## Archive Mode (Date-Stamped Files)

Use this command to generate and keep weekly snapshots:

```powershell
powershell -ExecutionPolicy Bypass -File tools/reporting/generate_weekly_rollup_archive.ps1
```

Default archive output:

- docs/reports/weekly/weekly_rollup_YYYY-MM-DD.md

## Common Overrides

```powershell
powershell -ExecutionPolicy Bypass -File tools/reporting/generate_weekly_rollup.ps1 `
  -Owner billmallard `
  -Repo MAOS-FCS `
  -ProjectNumber 4 `
  -EpicIssues 17,18,19,20 `
  -OutputPath docs/weekly_rollup_report.md `
  -Days 7
```

## Typical Weekly Workflow

1. Run the archive script.
2. Open the newly created file in docs/reports/weekly.
3. Fill in executive summary, completed work, risks, and commitments.
4. Share the final markdown in your weekly update channel.

If using archive mode, open the date-stamped file created in docs/reports/weekly.

## Notes

- The report auto-populates EPIC progress and core issue counts.
- Status and date data come from your GitHub project and issue hierarchy.
- If authentication fails, run gh auth status and confirm the active account/token.
