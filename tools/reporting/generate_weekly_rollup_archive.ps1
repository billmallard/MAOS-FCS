param(
    [string]$Owner = "billmallard",
    [string]$Repo = "MAOS-FCS",
    [int]$ProjectNumber = 4,
    [int[]]$EpicIssues = @(17, 18, 19, 20),
    [datetime]$PeriodEnd = (Get-Date),
    [int]$Days = 7,
    [string]$OutputDir = "docs/reports/weekly"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$periodEndDate = $PeriodEnd.ToString("yyyy-MM-dd")
$outputPath = Join-Path $OutputDir ("weekly_rollup_" + $periodEndDate + ".md")

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$baseScript = Join-Path $scriptDir "generate_weekly_rollup.ps1"
if (-not (Test-Path $baseScript)) {
    throw "Missing base generator script at $baseScript"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$baseParams = @{
    Owner = $Owner
    Repo = $Repo
    ProjectNumber = $ProjectNumber
    EpicIssues = $EpicIssues
    PeriodEnd = $PeriodEnd
    Days = $Days
    OutputPath = $outputPath
}

& $baseScript @baseParams

Write-Output "Archived weekly roll-up report at $outputPath"
