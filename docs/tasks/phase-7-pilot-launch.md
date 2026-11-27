# Phase 7: Pilot, handover and launch

**Dates:** 1 to 31 March 2027 · **Tasks:** 7 · **Points:** 38 (Dev 30, QA 8)

**Goal:** real Discoms use the portal in a pilot, ITPED takes ownership, and the Steering Group approves go-live on 31 March 2027.

`P7-CON-01` is owned by ITPED. Its 5 points count in the Dev total because the development team supports the bulk import.

**Exit criteria**

- [ ] GL-01, GL-02 and GL-13 to GL-15 pass
- [ ] Every acceptance criterion in SRS Section 8 passes

---

### P7-PIL-01 — Run the pilot with a subset of Discoms

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 8 | Dev | `P6-QA-01` | SRS Section 8 |

**Goal:** real users test the portal on real tasks, and their problems are fixed before launch.

**Scope**

- With ITPED, pick 3 to 5 Discoms of different sizes and regions. Register and activate them.
- Run a 2-week pilot: each Discom submits at least 2 items and runs searches for its own needs.
- Collect feedback through a short form and two check-in calls.
- Fix S1 and S2 defects during the pilot. Log the rest for maintenance.
- Watch the search log for zero-result searches, for `P7-SRCH-01`.

**Security**

- Pilot Discoms use real accounts, so all production security controls apply. Restricted content is allowed only if `P6-SEC-02` is Done.

**Acceptance criteria**

- [ ] Every pilot Discom has submitted and searched, and feedback is recorded
- [ ] No open S1 or S2 defect at the end of the pilot

**Tests:** a regression test per fix.

---

### P7-SRCH-01 — Tune taxonomy and search from pilot results

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P7-PIL-01`, `P5-SRCH-04` | FR-5.6, GL-02 |

**Goal:** search works well for the persona test queries, using evidence from real use.

**Scope**

- Review the pilot's zero-result and low-click searches.
- With ITPED, add synonyms, adjust subcategories and tune ranking weights.
- Agree a set of test queries for each persona (Discom engineer, commercial officer, regulatory or legal officer, policy researcher and senior manager), with expected top results.

**Security**

- Changes go through the Admin screens and are audited.

**Acceptance criteria**

- [ ] Each persona's test queries return the expected items in the top 5

**Tests:** `tests/search/test_persona_queries.py`, built from the agreed list.

---

### P7-CON-01 — Load 60 resources and 5 expert profiles

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 5 | ITPED | `P6-SEC-02` | SRS Section 8, GL-13 |

**Goal:** the portal launches with enough real content to be useful.

**Scope**

- ITPED prepares at least 60 resources (5 per subcategory) and 5 expert profiles with recorded consent.
- Load them through the bulk importer and the expert form, then run each through the workflow to Approved.
- The development team supports with import errors and file problems.

**Security**

- Restricted content may be loaded only because `P6-SEC-02` is Done.
- Remove the MVP test content from production after the real content is live.

**Acceptance criteria**

- [ ] At least 5 published resources in each of the 12 subcategories, and 5 published expert profiles (GL-13)

**Tests:** a count query recorded on the task.

---

### P7-TRN-01 — Deliver two ITPED sessions and one Discom webinar

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P7-PIL-01` | SRS 5.8 |

**Goal:** ITPED staff and Discom users know how to use the portal.

**Scope**

- Session 1 for ITPED: Admin tasks, the workflow, tag management, experts and Gallery, bulk import, and KPIs.
- Session 2 for ITPED: operations, including the runbook, backups, monitoring, incident response and account recovery.
- A webinar for Discoms: registration, submission, search, alerts and feedback.
- Record each session and share the slides and recordings.

**Security**

- Session 2 covers MFA recovery, phishing awareness for privileged users, and the incident reporting steps.

**Acceptance criteria**

- [ ] All three sessions are delivered, recorded and shared

**Tests:** none.

---

### P7-DOC-01 — Complete the handover of code, guides, manual and credentials

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 8 | Dev | `P6-OPS-01`, `P7-TRN-01` | SRS 5.8, GL-14 |

**Goal:** ITPED can run, change and hand on the system without the development team.

**Scope**

Hand over every SRS 5.8 deliverable:

- The source code repository, with full history, transferred to ITPED's organisation
- The final architecture, security, decisions and workflow docs
- The user manual, built from the quick guides and extended to every Phase 5 feature
- The operations runbook, updated after the disaster-recovery rehearsal
- The API and data model documentation
- All credentials and secrets, through ITPED's password manager, then rotated by ITPED
- The test suite and how to run it

**Security**

- After handover, remove development team access to production, except for the agreed support arrangement.
- ITPED rotates every secret once it holds them.

**Acceptance criteria**

- [ ] ITPED accepts each deliverable in writing (GL-14)
- [ ] Development team production access is removed or changed to the agreed support level

**Tests:** none.

---

### P7-QA-01 — Run the final UAT against SRS Section 8

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 8 | QA | `P7-PIL-01`, `P7-SRCH-01`, `P7-CON-01` | SRS Section 8, GL-01, GL-02 |

**Goal:** a final, complete check of every acceptance criterion with ITPED.

**Scope**

- Run every SRS Section 8 criterion with ITPED, including AC-01 to AC-22 (GL-01) and the persona search queries (GL-02).
- Collect the evidence for GL-01 to GL-15 into one acceptance record.

**Security**

- Re-run the sentinel, direct-URL and route registry checks on production with test accounts, then remove the accounts.

**Acceptance criteria**

- [ ] GL-01 and GL-02 pass, and the full acceptance record is complete

**Tests:** the final UAT record.

---

### P7-REL-01 — Obtain Steering Group sign-off and go live

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P7-QA-01`, `P7-DOC-01` | SRS Section 8, GL-15 |

**Goal:** the portal is formally launched to all Discoms.

**Scope**

- Present the acceptance record, the security confirmation, the load test report and the pilot results to the Steering Group.
- On sign-off, tag `v1.0.0`, release, and open registration to all Discoms.
- Announce the launch with ITPED.

**Security**

- Confirm every production go-live gate in [security.md](../security.md) is met before the release.

**Acceptance criteria**

- [ ] The Steering Group signs off (GL-15), and `v1.0.0` is live

**Tests:** the smoke check.
