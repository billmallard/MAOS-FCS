*** Settings ***
Documentation    Keywords for manifest-driven autonomous SIL campaign execution.
Library    Process
Library    OperatingSystem
Library    BuiltIn

*** Variables ***
${REPO_ROOT}    d:/Users/wpballard/Documents/github/MAOS-FCS
${PYTHON}    d:/Users/wpballard/Documents/github/MAOS-FCS/.venv/Scripts/python.exe
${CAMPAIGN_SCRIPT}    tools/testing/run_sil_campaign_webapi.py
${LOG_ROOT}    logs/sil_campaign

*** Keywords ***
Run Campaign Manifest
    [Arguments]    ${manifest_path}    ${timeout}=30 minutes
    ${result}=    Run Process    ${PYTHON}    ${CAMPAIGN_SCRIPT}    --manifest    ${manifest_path}
    ...    cwd=${REPO_ROOT}    stdout=PIPE    stderr=STDOUT    timeout=${timeout}    on_timeout=terminate
    Should Be Equal As Integers    ${result.rc}    0
    Should Contain    ${result.stdout}    [campaign] using manifest:
    Should Contain    ${result.stdout}    [campaign] complete:
    RETURN    ${result}

Resolve Latest Campaign Summary
    ${latest}=    Evaluate    str(sorted(__import__('pathlib').Path(r'''${REPO_ROOT}/${LOG_ROOT}''').glob('*/summary.json'))[-1])
    Should Not Be Empty    ${latest}
    RETURN    ${latest}

Load Campaign Summary
    [Arguments]    ${summary_path}
    ${text}=    Get File    ${summary_path}
    ${summary}=    Evaluate    __import__('json').loads(r'''${text}''')
    RETURN    ${summary}

Assert Campaign Has Zero Failures
    [Arguments]    ${summary}
    Should Be Equal As Integers    ${summary['failures']}    0

Assert Campaign Total Runs
    [Arguments]    ${summary}    ${expected_total}
    Should Be Equal As Integers    ${summary['total_runs']}    ${expected_total}
