# Decisions

The build follows these decisions. D-01 to D-08 resolve conflicts and gaps in the SRS. D-09 to D-13 fill gaps the SRS leaves open.

All of them need ITPED confirmation, because the SRS is ITPED's document. `P0-GOV-01` records each confirmation in the status column. A changed decision must update every task spec that cites it.

## SRS conflicts and gaps

| ID | Issue in the SRS | Decision | Affects | Status |
| --- | --- | --- | --- | --- |
| D-01 | Image limit: 400 MB in FR-3.5, 20 MB in Appendix A | Images (JPG, PNG) must not exceed 20 MB. Admin can lower the limit but never raise it above 20 MB. The limit is stated in the administrator manual, the Member guide and the upload error message | `P2-UPL-02`, `P4-DOC-02` | Awaiting confirmation |
| D-02 | Experts and Gallery are members-only in Section 3.2 but public in Section 2.3 and FR-13.6 | Visitors see consented expert fields and published Gallery listings, following FR-13 | `P3-EXP-02`, `P3-GAL-01` | Awaiting confirmation |
| D-03 | Access Tier must never show (FR-3.3), but FR-13.3 and FR-13.5 reveal it to visitors | The tier value is never rendered. The visitor lock label and the "Show only items I can open" filter are the only exceptions | `P3-PUB-02`, `P2-CON-02` | Awaiting confirmation |
| D-04 | Zero-result search logging is Must in FR-11.1 but Could in FR-5.5 | Zero-result searches are logged from the MVP. Only analytics reporting stays Could | `P3-SRCH-01`, `P4-KPI-01` | Awaiting confirmation |
| D-05 | View and download counts are mixed up (FR-6.4, FR-11.1) | Two separate counters. "Citation count" means downloads and is shown to users. Most Viewed sorts by views | `P3-LIST-02` | Awaiting confirmation |
| D-06 | The state table has no Rejected state, though the Approver can reject (FR-4.4) | Rejected is a final state. The record is kept, and a new submission is required | `P2-WF-01`, `P2-WF-04` | Awaiting confirmation |
| D-07 | The Approver's return path is unclear (FR-4.4) | Pending Approval returns directly to Under Review | `P2-WF-01`, `P2-WF-04` | Awaiting confirmation |
| D-08 | Retirement points to Section 7, which does not cover it | Retired is a status flag only, with no hard delete | `P5-LIFE-02` | Awaiting confirmation |
| D-09 | The SRS is silent on what users see during a substantive edit (FR-4.9) | The published version stays live until the Approver signs off the new version | `P2-WF-06` | Awaiting confirmation |
| D-10 | FR-2.3 gives no default for the sixth-session policy | The default is `block`. Admin can switch to `end_oldest` | `P1-ACC-07` | Awaiting confirmation |
| D-11 | FR-1.3 does not say how the System knows which Discom a registrant belongs to | The registrant picks their Discom from the master list, and the email domain must match that Discom's recorded domain | `P1-ACC-02`, `P1-ACC-03` | Awaiting confirmation |
| D-12 | The SRS does not say which state bulk-imported content enters | Imported items enter Submitted as ITPED-sourced items, so they still pass Reviewer and Approver | `P2-CON-07` | Awaiting confirmation |
| D-13 | The SRS does not say whose views count | View and download counts include Members and visitors only. Views and downloads by Admin, Reviewer and Approver are not counted | `P3-LIST-02` | Awaiting confirmation |

## Open items from the SRS

| ID | Question | Default until answered | Owner |
| --- | --- | --- | --- |
| Q-05 | FR-6.1 limits Newly Added to 2 items. Is that intended? | 2, as an Admin setting | ITPED |
| Q-07 | AIDA Endorsed criteria, Gallery entry conditions and fee model | Fee terms are free text, and criteria are configurable in Phase 5 | AIDA |
| Q-08 | Wording of the AIDA Endorsed disclaimer (FR-9.3) | Draft text in `P2-END-01` | AIDA |
| Q-09 | List of the 70 recognised Discoms with official email domains | Three test Discoms until supplied | ITPED |
| Q-10 | Text for the About page, terms of use, disclaimer, privacy notice and cookie notice | Placeholder text, clearly marked | ITPED |
| Q-11 | Visual design: a designer's mock-ups and brand assets, or a default theme | Clean default theme built in `P1-UI-02` from the UI and motion rules | ITPED |

## Taxonomy baseline (SRS Appendix A)

This baseline applies unless ITPED supplies a different taxonomy in `P0-GOV-02`. Admin can change subcategories and functional groups later without a code change (FR-3.10).

| Module (Category) | Subcategories |
| --- | --- |
| Research Study Reports | Research Study Reports; Regulatory Filings & Orders; Policies & Guidelines |
| Best Practices | Best Practices; Standards & International Benchmarks; Tender & Procurement References; AI/ML Use Cases & Cybersecurity Practices |
| Case Studies | Case Studies; Pilots from Donor-Funded Initiatives; IT Pilot Documentation |
| Training Material | Training Material; Equipment & Meter Manuals |
| Go-To Discom Partner | No subcategories. Shows the List of Experts |
| Technology Demonstration Gallery | No subcategories. Governed by Appendix C |

**Functional groups (admin-only):** Asset operations, Network operations, System operations, Business operations, Customer experience, Cybersecurity.

**Access tiers:** Public (no login) and Restricted (Member login). ITPED-internal material is not a tier. It lives only in the Admin internal workspace (`P5-ACC-01`).

## File formats and limits

| Group | Formats | Maximum per file | Modules |
| --- | --- | --- | --- |
| Documents | PDF, DOC, DOCX, XLS, XLSX, CSV, PPT, PPTX | 25 MB | All document modules and the Gallery |
| Images | JPG, PNG | **20 MB** (D-01) | All document modules and the Gallery |
| Media | MP4, MP3 | 1 GB | All document modules and the Gallery |
| E-learning | SCORM 1.2 and SCORM 2004 ZIP packages | 1 GB | Training Material only, from Phase 5 |

MP4 demonstration videos should be 16:9 landscape, ideally 1920×1080. The player preserves the source aspect ratio.
