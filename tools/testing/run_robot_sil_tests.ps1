Param(
    [ValidateSet("smoke", "regression", "manifest", "manifest-reset", "all")]
    [string]$Suite = "smoke"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Python = Join-Path $RepoRoot ".venv/Scripts/python.exe"
$RobotFile = Join-Path $RepoRoot "tests/robot/sil_campaign.robot"
$ManifestRobotFile = Join-Path $RepoRoot "tests/robot/sil_manifest.robot"
$OutDir = Join-Path $RepoRoot "logs/robot"

if (!(Test-Path $Python)) {
    throw "Python venv not found: $Python"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$tagArgs = @()
switch ($Suite) {
    "smoke" { $tagArgs = @("--include", "smoke") }
    "regression" { $tagArgs = @("--include", "regression") }
    "manifest" { $tagArgs = @("--include", "manifest") }
    "manifest-reset" { $tagArgs = @("--include", "reset") }
    default { $tagArgs = @() }
}

if ($Suite -eq "manifest" -or $Suite -eq "manifest-reset") {
    & $Python -m robot @tagArgs --outputdir $OutDir $ManifestRobotFile
}
elseif ($Suite -eq "all") {
    & $Python -m robot --outputdir $OutDir $RobotFile $ManifestRobotFile
}
else {
    & $Python -m robot @tagArgs --outputdir $OutDir $RobotFile
}
exit $LASTEXITCODE
