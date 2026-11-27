# Delivery plan

The project started on 23 November 2026, and the MVP ships on 17 December 2026 after 19 weekdays. Feature freeze is at the end of 10 December. The MVP plan uses 81% of developer capacity.

## Schedule

| Phase | Dates | Weekdays | Tasks | Dev points / capacity | QA points / capacity |
| --- | --- | --- | --- | --- | --- |
| 0 Mobilise | 23 to 25 November 2026 | 3 | 12 | 20 / 30 | 6 / 12 |
| 1 Platform and access | 26 to 30 November 2026 | 3 | 16 | 28 / 30 | 8 / 12 |
| 2 Content and governance | 1 to 7 December 2026 | 5 | 22 | 40 / 50 | 11 / 20 |
| 3 Discovery and directories | 8 to 10 December 2026 | 3 | 16 | 28 / 30 | 9 / 12 |
| 4 Hardening and release | 11 to 17 December 2026 | 5 | 19 | 37 / 50 | 12 / 20 |
| **MVP total** | | **19** | **85** | **153 / 190** | **46 / 76** |
| 5 Complete the SRS features | 18 December 2026 to 22 January 2027 | 24 | 24 | 76 | 18 |
| 6 Independent assurance | 25 January to 26 February 2027 | 25 | 7 | 41 | 8 |
| 7 Pilot, handover and launch | 1 to 31 March 2027 | 23 | 7 | 30 | 8 |

Capacity assumes 5 developers and 2 testers at 2 points per person per day. Public holidays are not deducted, so confirm the working calendar. Phases 5 to 7 are proposals, and Phase 6 depends on when the independent reviewer is available.

Features freeze at the end of 10 December. After that, only the three Phase 4 tasks `P4-PUB-01`, `P4-PUB-02` and `P4-KPI-01` add behaviour, and they finish by 14 December.

## Critical path

`P0-SET-01` → `P0-SET-02` → `P1-ACC-08` → `P1-ACC-04` → `P1-ACC-06` → `P2-CON-02` → `P2-WF-01` → `P2-WF-02` → `P2-WF-03` → `P2-WF-04` → `P3-LIST-01` → `P3-PUB-02` → `P4-QA-02` → `P4-REL-02`

A slip on any of these tasks moves the MVP date unless work is reassigned.

## Risks

| Code | Risk | Response |
| --- | --- | --- |
| R-01 | Hosting is not ready by 25 November | Develop locally in Docker and use no real data until India hosting exists |
| R-02 | Decisions D-01 to D-13 are confirmed late | Build to [decisions.md](decisions.md), and treat later changes as change requests |
| R-03 | The team is smaller than 5 developers and 2 testers | Move the Gallery tasks to Phase 5 first, then the Experts tasks |
| R-04 | AI-written code contains security defects | Human review tasks `P1-SEC-01`, `P2-SEC-01` and `P4-SEC-02`, and two reviewers for security-sensitive areas |
| R-05 | AIDA criteria and the Gallery fee model are not final | Use test listings in the MVP, with a fee-terms field and disclosure label |
| R-06 | New requests arrive during the build | Any new request goes to Phase 5 |
| R-07 | Public holidays reduce the 19 weekdays | Confirm the calendar now, and take cover from Phase 4 |
| R-08 | One shared Member login per Discom can be locked by anyone who knows the User ID (FR-1.7 lockout) | Lockout lasts only 15 minutes. CAPTCHA on login after repeated failures is a possible later mitigation; raise with ITPED if abuse appears |

## Open decisions

| Code | Decision needed | Owner | Due |
| --- | --- | --- | --- |
| Q-01 | Confirm decisions D-01 to D-13, or record changes | ITPED | 20 November 2026 |
| Q-02 | Confirm an owner for each work stream | Project lead | 20 November 2026 |
| Q-03 | Select the India hosting provider and provide access | ITPED | 20 November 2026 |
| Q-04 | Supply the final taxonomy, or accept Appendix A as the baseline | ITPED | 20 November 2026 |
| Q-05 | Confirm the Newly Added limit, which FR-6.1 sets at 2 items | ITPED | 20 November 2026 |
| Q-06 | Appoint the independent security reviewer | ITPED | 22 January 2027 |
| Q-07 | Finalise Endorsed criteria, Gallery conditions and fee model | AIDA | 22 January 2027 |
| Q-08 | Approve the AIDA Endorsed disclaimer wording | AIDA | 4 December 2026 |
| Q-09 | Supply the list of 70 Discoms with official email domains | ITPED | 30 November 2026 |
| Q-10 | Supply About, terms of use, disclaimer, privacy and cookie notice text | ITPED | 8 December 2026 |
