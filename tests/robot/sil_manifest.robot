*** Settings ***
Documentation    Manifest-driven Robot suite for autonomous SIL campaigns.
Resource    resources/sil_manifest_keywords.robot

*** Test Cases ***
Manifest Smoke Campaign Completes
    [Documentation]    Executes scenarios from JSON manifest and validates summary.
    [Tags]    manifest    smoke
    ${result}=    Run Campaign Manifest    tests/robot/manifests/smoke_manifest.json    timeout=12 minutes
    ${summary_path}=    Resolve Latest Campaign Summary
    ${summary}=    Load Campaign Summary    ${summary_path}
    Assert Campaign Has Zero Failures    ${summary}
    Assert Campaign Total Runs    ${summary}    2
