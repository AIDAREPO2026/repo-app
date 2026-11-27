# Acceptance criteria

## MVP (17 December 2026)

The MVP is released only when all 22 criteria pass on staging. `P4-QA-03` records the sign-off.

| Code | Criterion | Verified by |
| --- | --- | --- |
| AC-01 | Registration with valid and invalid CAPTCHA, followed by Admin activation | `P1-QA-01` |
| AC-02 | All four login types work, with MFA on privileged logins | `P1-QA-02` |
| AC-03 | Five Member sessions work, and the sixth follows the Admin policy | `P1-QA-02` |
| AC-04 | Lockout after five failed attempts, and logout after 30 idle minutes | `P1-QA-01` |
| AC-05 | Submission, Admin edit, returns and resubmission all work | `P2-QA-02` |
| AC-06 | Rejected items reach the Rejected state and are retained | `P2-QA-02` |
| AC-07 | Only the Approver can publish or apply AIDA Endorsed | `P2-QA-02` |
| AC-08 | The workflow works for content, expert profiles and Gallery listings | `P3-QA-03` |
| AC-09 | Every workflow, login and administrative action is in the audit log | `P2-QA-02` |
| AC-10 | A 21 MB image is refused before upload, with a message stating the 20 MB limit | `P2-QA-01` |
| AC-11 | A 1 GB MP4 upload is interrupted and resumes | `P2-QA-01` |
| AC-12 | An infected file is quarantined and the submitter is notified | `P2-QA-01` |
| AC-13 | PDF, Office, image, MP4 and MP3 items open in the browser | `P3-QA-01` |
| AC-14 | Central and module search return the correct items | `P3-QA-01` |
| AC-15 | Public items open and download without login | `P3-QA-02` |
| AC-16 | Restricted files cannot be reached by direct URL | `P3-QA-02` |
| AC-17 | Restricted items flagged No are absent from search, listings and counts | `P3-QA-02` |
| AC-18 | Functional Group, Access Tier values and jurisdiction never show to end users | `P2-QA-03` |
| AC-19 | Expert consent withdrawal hides the profile immediately | `P3-QA-03` |
| AC-20 | Gallery listings show the paid-placement disclosure | `P3-QA-03` |
| AC-21 | The anonymous download limit triggers a CAPTCHA | `P4-QA-01` |
| AC-22 | OWASP ZAP high findings are fixed, and backup restore is rehearsed | `P4-SEC-01`, `P4-OPS-01` |

## Go-live (proposed 31 March 2027)

These criteria come from SRS Section 8. `P7-QA-01` verifies them, and `P7-REL-01` records the Steering Group sign-off.

| Code | Criterion | Verified by |
| --- | --- | --- |
| GL-01 | All MVP criteria AC-01 to AC-22 still pass | `P7-QA-01` |
| GL-02 | Search returns correct results for the test queries of each persona: Discom engineer, commercial officer, regulatory or legal officer, policy researcher and senior manager | `P7-QA-01` |
| GL-03 | A review-date change is blocked without Approver countersignature | `P5-QA-01` |
| GL-04 | A Reviewer recusal is routed to the alternate | `P5-QA-01` |
| GL-05 | SCORM 1.2 and SCORM 2004 packages launch in the embedded player | `P5-QA-01` |
| GL-06 | An external link is flagged as broken | `P5-QA-01` |
| GL-07 | Internal workspace content is unreachable by any role except Admin | `P5-QA-01` |
| GL-08 | The independent security review is complete, with OWASP ASVS Level 2 critical and high findings closed | `P6-SEC-02` |
| GL-09 | The formal load test meets 350 Member and 200 visitor sessions, including peak Gallery video, and ITPED signs the report | `P6-PERF-01` |
| GL-10 | The WCAG 2.1 Level AA audit is passed | `P6-A11Y-01` |
| GL-11 | A full backup and disaster-recovery rehearsal completes within the 8-hour RTO | `P6-OPS-01` |
| GL-12 | Availability monitoring is configured against the 99.5% target | `P6-OPS-02` |
| GL-13 | At least 60 resources (5 per subcategory) and 5 expert profiles are published | `P7-CON-01` |
| GL-14 | All handover deliverables in SRS Section 5.8 are accepted by ITPED | `P7-DOC-01` |
| GL-15 | The Steering Group signs off after the pilot | `P7-REL-01` |
