# Contributing

Thanks for contributing to MAOS-FCS.

## Licensing Classification Rules (Important)

This repository uses a dual-license model:

- Code files are licensed under PolyForm Noncommercial 1.0.0 (see LICENSE-CODE).
- Non-code design and documentation content is licensed under CC BY-NC-SA 4.0 (see LICENSE-DOCS).

Use these rules when adding files:

1. Treat executable or build-consumed files as code.
2. Treat narrative, diagrams, models, and design artifacts as non-code.
3. If a file is mixed-content or ambiguous, add a file-level license notice.
4. File-level notice overrides repository default for that file.

## Typical Classification Examples

Code (PolyForm NC):

- Firmware and libraries: .c, .cpp, .h, .hpp
- Tooling and test scripts: .py, .ps1
- Robot or test automation logic and parsers
- Build/config logic used by tooling and CI

Non-code (CC BY-NC-SA):

- Architecture and requirements docs: .md
- Interface specs and engineering reports
- Published simulation result artifacts and figures

## Pull Request Expectations

- Keep changes scoped and reviewable.
- Keep timing, units, and fault semantics explicit where relevant.
- Include test evidence for behavior changes.
- Do not claim certification, compliance approval, or airworthiness status.

## Commercial Use

Commercial use is not granted by default.
For commercial licensing inquiries: contact@aerocommons.org
