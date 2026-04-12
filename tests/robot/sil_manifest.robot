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
    Assert Max Infra Failures    ${summary}    0
    Assert Max Functional Failures    ${summary}    0
    Assert Campaign Total Runs    ${summary}    2

Manifest Reset Campaign Completes
    [Documentation]    Executes reset/startup manifest and validates repeatable scenario initialization.
    [Tags]    manifest    reset
    ${result}=    Run Campaign Manifest    tests/robot/manifests/reset_smoke_manifest.json    16 minutes    False
    ...    --stabilize-on-exit
    ...    --cleanup-target-altitude-ft
    ...    2000
    ${summary_path}=    Resolve Latest Campaign Summary
    ${summary}=    Load Campaign Summary    ${summary_path}
    Assert Max Infra Failures    ${summary}    0
    Assert Max Functional Failures    ${summary}    0
    Assert Campaign Total Runs    ${summary}    2
