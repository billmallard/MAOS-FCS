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
    [Arguments]    ${manifest_path}    ${timeout}=30 minutes    ${allow_nonzero_rc}=False    @{extra_args}
    ${result}=    Run Process    ${PYTHON}    ${CAMPAIGN_SCRIPT}    --manifest    ${manifest_path}
    ...    @{extra_args}    cwd=${REPO_ROOT}    stdout=PIPE    stderr=STDOUT    timeout=${timeout}    on_timeout=terminate
    IF    not ${allow_nonzero_rc}
        Should Be Equal As Integers    ${result.rc}    0
    END
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

Assert Max Infra Failures
    [Arguments]    ${summary}    ${max_infra_failures}
    ${infra_count}=    Evaluate    sum(1 for r in $summary['results'] if r.get('status') == 'INFRA_FAIL')
    Should Be True    ${infra_count} <= int(${max_infra_failures})
    ...    msg=INFRA_FAIL count ${infra_count} exceeded max ${max_infra_failures}

Assert Max Functional Failures
    [Arguments]    ${summary}    ${max_failures}
    ${func_count}=    Evaluate    sum(1 for r in $summary['results'] if r.get('status') == 'FAIL')
    Should Be True    ${func_count} <= int(${max_failures})
    ...    msg=Functional FAIL count ${func_count} exceeded max ${max_failures}
