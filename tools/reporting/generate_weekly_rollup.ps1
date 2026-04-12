param(
    [string]$Owner = "billmallard",
    [string]$Repo = "MAOS-FCS",
    [int]$ProjectNumber = 4,
    [int[]]$EpicIssues = @(17, 18, 19, 20),
    [string]$OutputPath = "docs/weekly_rollup_report.md",
    [datetime]$PeriodEnd = (Get-Date),
    [int]$Days = 7
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-EpicProgress {
    param(
        [string]$Owner,
        [string]$Repo,
        [int]$IssueNumber
    )

    $query = @'
query($owner:String!, $repo:String!, $number:Int!) {
  repository(owner:$owner, name:$repo) {
    issue(number:$number) {
      number
      title
      state
      url
      subIssues(first:100) {
        totalCount
        nodes {
          number
          title
          state
          url
        }
      }
    }
  }
}
'@

    $resp = gh api graphql -f query=$query -f owner=$Owner -f repo=$Repo -F number=$IssueNumber | ConvertFrom-Json
    $issue = $resp.data.repository.issue
    if (-not $issue) {
        throw "Issue #$IssueNumber not found in $Owner/$Repo"
    }

    $children = @($issue.subIssues.nodes)
    $total = [int]$issue.subIssues.totalCount
    $done = @($children | Where-Object { $_.state -eq "CLOSED" }).Count
    $open = @($children | Where-Object { $_.state -eq "OPEN" }).Count

    $status = if ($done -eq $total -and $total -gt 0) {
        "Done"
    } elseif ($open -gt 0) {
        "In progress"
    } else {
        "Todo"
    }

    $percent = if ($total -gt 0) {
        [math]::Round((100.0 * $done) / $total, 0)
    } else {
        0
    }

    [pscustomobject]@{
        Number = [int]$issue.number
        Title = [string]$issue.title
        Url = [string]$issue.url
        Status = $status
        Done = $done
        Total = $total
        Open = $open
        Percent = $percent
    }
}

function Get-IssueCounts {
    param(
        [string]$Owner,
        [string]$Repo,
        [datetime]$Start,
        [datetime]$End
    )

    $openP0 = @(
        gh issue list --repo "$Owner/$Repo" --state open --label priority/p0 --limit 500 --json number |
            ConvertFrom-Json
    ).Count

    $startIso = $Start.ToString("yyyy-MM-ddTHH:mm:ssZ")
    $endIso = $End.ToString("yyyy-MM-ddTHH:mm:ssZ")

    $closedThisWeek = @(
        gh issue list --repo "$Owner/$Repo" --state closed --search "closed:$startIso..$endIso" --limit 500 --json number |
            ConvertFrom-Json
    ).Count

    $createdThisWeek = @(
        gh issue list --repo "$Owner/$Repo" --state all --search "created:$startIso..$endIso" --limit 500 --json number |
            ConvertFrom-Json
    ).Count

    [pscustomobject]@{
        OpenP0 = $openP0
        ClosedThisWeek = $closedThisWeek
        CreatedThisWeek = $createdThisWeek
    }
}

$periodStart = $PeriodEnd.AddDays(-1 * $Days)
$periodStartDate = $periodStart.ToString("yyyy-MM-dd")
$periodEndDate = $PeriodEnd.ToString("yyyy-MM-dd")
$generatedUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$epics = @()
foreach ($epic in $EpicIssues) {
    $epics += Get-EpicProgress -Owner $Owner -Repo $Repo -IssueNumber $epic
}

$counts = Get-IssueCounts -Owner $Owner -Repo $Repo -Start $periodStart -End $PeriodEnd

$report = New-Object System.Collections.Generic.List[string]
$report.Add("# MAOS-FCS Weekly Roll-Up Report")
$report.Add("")
$report.Add("Reporting period: $periodStartDate to $periodEndDate")
$report.Add("Report owner: <name>")
$report.Add("Portfolio project: MAOS-FCS: Flight Control Systems")
$report.Add("Generated at (UTC): $generatedUtc")
$report.Add("")
$report.Add("## 1) Executive Summary")
$report.Add("")
$report.Add("Overall status: Green | Yellow | Red")
$report.Add("")
$report.Add("This week in one paragraph:")
$report.Add("- Fill in major outcomes, blockers, and next focus.")
$report.Add("")
$report.Add("## 2) Portfolio Snapshot (EPIC Roll-Up)")
$report.Add("")
$report.Add("| EPIC | Status | Sub-issues Done/Total | Trend vs last week | Target date | Notes |")
$report.Add("|---|---|---:|---|---|---|")

foreach ($e in $epics) {
    $epicCell = "[#" + $e.Number + " " + $e.Title + "](" + $e.Url + ")"
    $progressCell = "$($e.Done)/$($e.Total)"
    $report.Add("| $epicCell | $($e.Status) | $progressCell | Up/Flat/Down | YYYY-MM-DD | $($e.Percent)% complete |")
}

$report.Add("")
$report.Add("## 3) Completed This Week")
$report.Add("")
$report.Add("- Issue #<n>: <title> (why it matters)")
$report.Add("- Issue #<n>: <title>")
$report.Add("- Issue #<n>: <title>")
$report.Add("")
$report.Add("## 4) In Progress and Next Up")
$report.Add("")
$report.Add("In progress:")
$report.Add("- Issue #<n>: <title>, owner, expected completion")
$report.Add("- Issue #<n>: <title>")
$report.Add("")
$report.Add("Next up:")
$report.Add("- Issue #<n>: <title>")
$report.Add("- Issue #<n>: <title>")
$report.Add("")
$report.Add("## 5) Risks and Blockers")
$report.Add("")
$report.Add("| Risk/Blocker | Impact | Mitigation | Owner | ETA |")
$report.Add("|---|---|---|---|---|")
$report.Add("| <short description> | Low/Med/High | <plan> | <owner> | YYYY-MM-DD |")
$report.Add("")
$report.Add("## 6) Metrics")
$report.Add("")
$report.Add("Core metrics:")
$report.Add("- Open P0 issues: $($counts.OpenP0)")
$report.Add("- Closed this week: $($counts.ClosedThisWeek)")
$report.Add("- New issues this week: $($counts.CreatedThisWeek)")
$epicSummary = ($epics | ForEach-Object { "#$($_.Number) $($_.Percent)%" }) -join ", "
$report.Add("- EPIC completion: $epicSummary")
$report.Add("")
$report.Add("Quality indicators:")
$report.Add("- Reopened issues: <count>")
$report.Add("- Infra fails vs test fails (if available): <ratio>")
$report.Add("")
$report.Add("## 7) Decisions Needed")
$report.Add("")
$report.Add("- Decision: <question>")
$report.Add("  - Options: <a>, <b>, <c>")
$report.Add("  - Recommended: <option>")
$report.Add("  - Needed by: YYYY-MM-DD")
$report.Add("")
$report.Add("## 8) Next Week Commitments")
$report.Add("")
$report.Add("- Commit 1: <outcome statement>")
$report.Add("- Commit 2: <outcome statement>")
$report.Add("- Commit 3: <outcome statement>")
$report.Add("")
$report.Add("## Appendix: Query and Command Traceability")
$report.Add("")
$report.Add("- Data source: gh CLI and GitHub GraphQL API")
$report.Add("- Repo: $Owner/$Repo")
$report.Add("- Project number: $ProjectNumber")
$report.Add("- EPIC source issues: $($EpicIssues -join ', ')")

$outputDir = Split-Path -Path $OutputPath -Parent
if (-not [string]::IsNullOrWhiteSpace($outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

Set-Content -Path $OutputPath -Value $report -Encoding UTF8
Write-Output "Wrote weekly roll-up report to $OutputPath"
