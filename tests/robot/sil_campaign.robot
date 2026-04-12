*** Settings ***
Documentation    Robot regression harness for autonomous SIL campaigns via X-Plane Web API.
Library    Process
Library    OperatingSystem
Library    Collections
Library    BuiltIn

*** Variables ***
${REPO_ROOT}    d:/Users/wpballard/Documents/github/MAOS-FCS
${PYTHON}    d:/Users/wpballard/Documents/github/MAOS-FCS/.venv/Scripts/python.exe
${CAMPAIGN_SCRIPT}    tools/testing/run_sil_campaign_webapi.py
${LOG_ROOT}    logs/sil_campaign

*** Test Cases ***
Smoke Campaign Completes
    [Documentation]    Runs a short autonomous campaign and requires zero failures.
    [Tags]    smoke
    ${result}=    Run Process    ${PYTHON}    ${CAMPAIGN_SCRIPT}    --profile    smoke    --repeats    1
    ...    cwd=${REPO_ROOT}    stdout=PIPE    stderr=STDOUT    timeout=8 minutes    on_timeout=terminate
    Should Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stdout}    [campaign] X-Plane
    Should Contain    ${result.stdout}    [campaign] complete:
    ${summary_path}=    Resolve Latest Summary Path
    ${summary}=    Load Summary JSON    ${summary_path}
    Should Be Equal As Integers    ${summary['failures']}    0
    Should Be Equal As Integers    ${summary['total_runs']}    2

Default Campaign Completes
    [Documentation]    Runs the normal campaign profile once and requires zero failures.
    [Tags]    regression
    ${result}=    Run Process    ${PYTHON}    ${CAMPAIGN_SCRIPT}    --profile    default    --repeats    1
    ...    cwd=${REPO_ROOT}    stdout=PIPE    stderr=STDOUT    timeout=20 minutes    on_timeout=terminate
    Should Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stdout}    [campaign] complete:
    ${summary_path}=    Resolve Latest Summary Path
    ${summary}=    Load Summary JSON    ${summary_path}
    Should Be Equal As Integers    ${summary['failures']}    0
    Should Be Equal As Integers    ${summary['total_runs']}    3

*** Keywords ***
Resolve Latest Summary Path
    ${latest}=    Evaluate    str(sorted(__import__('pathlib').Path(r'''${REPO_ROOT}/${LOG_ROOT}''').glob('*/summary.json'))[-1])
    Should Not Be Empty    ${latest}
    RETURN    ${latest}

Load Summary JSON
    [Arguments]    ${summary_path}
    ${text}=    Get File    ${summary_path}
    ${summary}=    Evaluate    __import__('json').loads(r'''${text}''')
    RETURN    ${summary}
