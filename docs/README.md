# DISCOM Digital Resource Repository: Developer Documentation

This folder is the single source of truth for building the Digital Resource Repository for DISCOMs. It turns the Software Requirements Specification (SRS) into coded tasks that developers can pick up and build.

- **MVP release:** 17 December 2026 (Public or test content only until the independent security review is complete)
- **Proposed production go-live:** 31 March 2027
- **Team for the MVP:** 5 developers and 2 testers

## Where to start

New to the project? Read in this order:

1. [conventions.md](conventions.md): task codes, points, branches, Definition of Done and coding rules
2. [architecture.md](architecture.md): stack, folder layout, request and file flows, settings
3. [security.md](security.md): security controls every task must meet
4. [decisions.md](decisions.md): how SRS conflicts and gaps are resolved
5. [workflow.md](workflow.md): the content governance state machine
6. [tasks/README.md](tasks/README.md): the index of every task, then the phase file for your task

## File map

| File | What it holds |
| --- | --- |
| [conventions.md](conventions.md) | How to code, branch, commit, review and close a task |
| [architecture.md](architecture.md) | Technical design every task builds on |
| [security.md](security.md) | Threats, mandatory controls, secure process and release gates |
| [decisions.md](decisions.md) | Decisions D-01 to D-13 and the taxonomy baseline |
| [workflow.md](workflow.md) | States, transitions, permissions and side effects |
| [plan.md](plan.md) | Schedule, capacity, risks and open decisions |
| [acceptance.md](acceptance.md) | MVP and go-live acceptance criteria |
| [tasks/README.md](tasks/README.md) | Index of all 123 tasks |
| [tasks/phase-0-mobilise.md](tasks/phase-0-mobilise.md) | Phase 0 task specs |
| [tasks/phase-1-platform-access.md](tasks/phase-1-platform-access.md) | Phase 1 task specs |
| [tasks/phase-2-content-governance.md](tasks/phase-2-content-governance.md) | Phase 2 task specs |
| [tasks/phase-3-discovery-directories.md](tasks/phase-3-discovery-directories.md) | Phase 3 task specs |
| [tasks/phase-4-hardening-release.md](tasks/phase-4-hardening-release.md) | Phase 4 task specs |
| [tasks/phase-5-complete-features.md](tasks/phase-5-complete-features.md) | Phase 5 task specs |
| [tasks/phase-6-assurance.md](tasks/phase-6-assurance.md) | Phase 6 task specs |
| [tasks/phase-7-pilot-launch.md](tasks/phase-7-pilot-launch.md) | Phase 7 task specs |

## Source documents

- **SRS:** Software Requirements Specification, Digital Resource Repository for DISCOMs. Requirement IDs such as `FR-3.5` and section numbers such as `5.3` in these docs refer to it.
- **Inception Report:** referenced by the SRS for the RACI matrix and the risk register. It is not in this repository.
- **Planning tracker:** the shared delivery tracker holds live task status. These docs hold the task detail. If they disagree, raise it with the tech lead and fix both.

## Keeping these docs current

A pull request that changes behaviour described here must update the matching doc in the same pull request. This includes task acceptance criteria, settings, decisions and the workflow.
