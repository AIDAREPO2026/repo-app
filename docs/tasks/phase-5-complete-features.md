# Phase 5: Complete the SRS features

**Dates:** 18 December 2026 to 22 January 2027 · **Tasks:** 24 · **Points:** 94 (Dev 76, QA 18)

**Goal:** every SRS feature left out of the MVP is built, so Phase 6 can assure a complete system.

These dates are a proposal. Public holidays are not deducted, so confirm the working calendar before committing.

**Work streams**

- **Stream A (search and discovery):** `P5-SRCH-01` to `P5-SRCH-04`, `P5-PUB-01`
- **Stream B (governance and lifecycle):** `P5-WF-01`, `P5-LIFE-01`, `P5-LIFE-02`, `P5-ACC-01`, `P5-ACC-02`, `P5-END-01`, `P5-GAL-01`, `P5-EXP-01`
- **Stream C (content types):** `P5-CON-01`, `P5-VIEW-01`, `P5-CON-02`
- **Stream D (engagement and reporting):** `P5-NOT-01` to `P5-NOT-03`, `P5-KPI-01`, `P5-KPI-02`, `P5-REP-01`

**Exit criteria**

- [ ] GL-03 to GL-07 pass
- [ ] Full regression passes, so AC-01 to AC-22 still hold

---

### P5-WF-01 — Add the next-review date with Approver countersignature

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P2-WF-04` | FR-3.7, FR-4.7, GL-03 |

**Goal:** every published item has a next-review date, and no one can move it without the Approver agreeing.

**Scope**

- Set `next_review_date` at approval. The Approver picks it, with a default of 2 years from publication.
- A Reviewer or Admin may propose a new date with a reason. The proposal waits in the Approver queue as "Review date change".
- The Approver countersigns or declines. Only a countersigned change updates the date.
- `next_review_date` appears only in `ItemAdminView`.

**Security**

- The date can only change through the countersign action, which is audited with old and new dates.

**Acceptance criteria**

- [ ] A proposed date change does nothing until the Approver countersigns (GL-03)
- [ ] The date never appears in Member or public views

**Tests:** `test_fr_4_7_review_date_needs_countersign`, `test_fr_3_7_review_date_admin_only`.

---

### P5-LIFE-01 — Build the reassessment queue and outcomes

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 5 | Dev | `P5-WF-01`, `P2-WF-06` | FR-10.1, FR-10.2, FR-10.3 |

**Goal:** items due for review are surfaced and reassessed, so the repository stays current.

**Scope**

- A daily Celery beat job that puts items whose `next_review_date` is within 30 days into a reassessment queue, and notifies the assigned Reviewer.
- A reassessment screen with three outcomes:
    - Confirm current: set a new review date, with Approver countersignature
    - Update: start a substantive edit through `P2-WF-06`
    - Retire: set the Retired flag (`P5-LIFE-02`), with Approver sign-off
- Overdue items are highlighted on the Admin console.

**Security**

- Each outcome goes through `apply_action()` and is audited.

**Acceptance criteria**

- [ ] An item 30 days from review appears in the queue, and the Reviewer is notified
- [ ] Each outcome produces the right result

**Tests:** `test_fr_10_1_due_items_queued`, `test_fr_10_2_confirm_sets_new_date`, `test_fr_10_3_update_starts_edit`.

---

### P5-LIFE-02 — Add the Retired status flag

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P2-CON-06` | FR-10.4, D-08 |

**Goal:** a retired item is hidden from everyone except privileged users, and its record is kept.

**Scope**

- `retired`, `retired_at`, `retired_by` and `retired_reason` on `content_item`. Retired is a flag, not a workflow state (D-08).
- `visible_items()` and `can_open()` exclude retired items for Members and visitors.
- Admin can see retired items with a filter, and the Approver can un-retire.

**Security**

- Retired items return 404 to Members and visitors, and are removed from search and counts.

**Acceptance criteria**

- [ ] A retired item disappears from Member and public views, and stays visible to privileged users

**Tests:** `test_fr_10_4_retired_hidden`, `test_d08_retired_keeps_state`.

---

### P5-ACC-01 — Build the Admin-only internal workspace

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 5 | Dev | `P2-CON-06`, `P3-VIEW-03` | FR-2.6, GL-07 |

**Goal:** ITPED has a private area for internal documents that no other role can reach.

**Scope**

- A `workspace_document` table, separate from `content_item`, with title, notes, folder and file.
- Admin pages to upload, organise into folders, view, download and delete.
- Files use the same upload, scan and delivery path, with a check for `login_type == admin`.
- Workspace documents never appear in listings, search, counts, sitemaps or KPIs.

**Security**

- A separate table means no visibility rule can leak these files by mistake.
- Every route returns 404 to non-Admin users. The route registry test covers them.

**Acceptance criteria**

- [ ] Reviewer, Approver, Member and visitor requests for any workspace URL get 404 (GL-07)
- [ ] Workspace files never appear in search

**Tests:** `test_fr_2_6_workspace_admin_only`, `test_fr_2_6_workspace_not_in_search`.

---

### P5-ACC-02 — Route recused items to the alternate Reviewer

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P2-WF-03` | FR-2.9, GL-04, [workflow.md](../workflow.md) recusal |

**Goal:** a Reviewer with a conflict of interest can step aside, and the item is reviewed by someone else.

**Scope**

- A "Recuse myself" action on the review page, with a required reason.
- The item is reassigned to the alternate Reviewer set in settings, and both the alternate and Admin are notified.
- If the item was submitted by the Reviewer's own organisation, the system suggests recusal.

**Security**

- A recused Reviewer can no longer act on that item.

**Acceptance criteria**

- [ ] A recusal routes the item to the alternate (GL-04), and the reason is audited

**Tests:** `test_fr_2_9_recusal_routes_to_alternate`, `test_fr_2_9_recused_reviewer_blocked`.

---

### P5-CON-01 — Accept SCORM packages and scan every file inside

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P2-UPL-03` | FR-3.5, FR-3.11, [security.md](../security.md) uploads |

**Goal:** e-learning packages can be submitted safely.

**Scope**

- Allow SCORM ZIP files in the media group, up to the media limit.
- After upload, a worker task:
    1. Checks the archive before extracting: no absolute paths, no `..` segments, no symbolic links, at most 5,000 entries, and a total uncompressed size under 2 GB.
    2. Extracts it to a temporary directory.
    3. Scans every file with ClamAV.
    4. Parses `imsmanifest.xml` with `defusedxml` to find the SCORM version (1.2 or 2004) and the launch file.
    5. Stores the extracted files under `scorm/{file_id}/`.
- Refuse the package if any check fails, and tell the submitter why.

**Security**

- Zip-bomb and path-traversal checks run before any extraction.
- `defusedxml` prevents XML entity attacks in the manifest.

**Acceptance criteria**

- [ ] A valid SCORM 1.2 and a valid 2004 package are accepted, and the version is detected
- [ ] A package with a `../` path, a zip bomb or an infected file inside is refused

**Tests:** `test_fr_3_5_scorm_accepted`, `test_fr_3_11_scorm_inner_file_scanned`, `test_p5_con_01_zip_bomb_refused`, `test_p5_con_01_path_traversal_refused`.

---

### P5-VIEW-01 — Build the SCORM 1.2 and 2004 player on a separate subdomain

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 8 | Dev | `P5-CON-01` | FR-6.6, GL-05 |

**Goal:** SCORM packages launch in the browser without giving package code access to the portal.

**Scope**

- Serve extracted packages from a separate cookieless subdomain, such as `scorm.<portal-domain>`, through Nginx.
- The portal item page embeds the package in an `iframe` with `sandbox="allow-scripts allow-forms"` (no `allow-same-origin` with the portal).
- A minimal SCORM runtime in vendored JavaScript providing the `API` (1.2) and `API_1484_11` (2004) objects. It is enough to launch and track completion in the browser session. Results are not stored, because the SRS does not require tracking.
- The portal issues a short-lived signed token for each launch, and the subdomain checks it before serving files.

**Security**

- The subdomain has no portal cookies, so package scripts cannot read the session.
- Restricted packages still need `can_open()`, enforced when the token is issued.

**Acceptance criteria**

- [ ] SCORM 1.2 and 2004 test packages launch and run in the player (GL-05)
- [ ] Package scripts cannot read `document.cookie` for the portal

**Tests:** `test_fr_6_6_scorm_launch_token_required`, plus Playwright launches of both test packages.

---

### P5-CON-02 — Add the weekly external link check and report

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P2-CON-05` | FR-3.8, GL-06 |

**Goal:** broken external links are found and reported before users hit them.

**Scope**

- A weekly Celery beat job that sends a `HEAD` request (falling back to `GET`) to each published External Link item, with a 10-second timeout and up to 3 redirects.
- Record the status, the time and the number of consecutive failures.
- After 2 consecutive failures, mark the link broken and list it on an Admin report, with a notification to Admin.

**Security**

- SSRF protection: resolve the host first and refuse private, loopback, link-local and metadata addresses, and re-check every redirect target.
- Requests go out with a fixed generic User-Agent and no cookies.

**Acceptance criteria**

- [ ] A link returning 404 twice is reported as broken (GL-06)
- [ ] A link pointing at `127.0.0.1` or `169.254.169.254` is never requested

**Tests:** `test_fr_3_8_broken_link_reported`, `test_p5_con_02_private_address_refused`, `test_p5_con_02_redirect_to_private_refused`.

---

### P5-SRCH-01 — Add full-text extraction and indexing

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 5 | Dev | `P3-SRCH-01`, `P3-VIEW-02` | FR-5.3 |

**Goal:** search matches words inside documents, not only titles and summaries.

**Scope**

- A worker task `extract_text(file_id)`, after a clean scan:
    - PDF: `pdftotext`
    - Office files: from the LibreOffice PDF preview, then `pdftotext`
    - CSV: the first 1 MB as text
- Store up to 1 MB of text in a `content_text` table, and add it to `search_vector` with weight D.
- A one-off command to backfill existing items.

**Security**

- Extracted text follows the item's visibility, because search already goes through `visible_items()`.
- Extracted text is never shown to visitors for Restricted items, including in result snippets.

**Acceptance criteria**

- [ ] A word that appears only in a PDF's body finds that item
- [ ] Snippets for teaser results never show body text

**Tests:** `test_fr_5_3_body_text_searchable`, `test_fr_5_3_teaser_snippet_has_no_body_text`.

---

### P5-SRCH-02 — Add Admin-editable sector synonyms

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P3-SRCH-01` | FR-5.4 |

**Goal:** a search for "AT&C" also finds "aggregate technical and commercial losses", and similar sector terms.

**Scope**

- A `search_synonym` table of term groups, editable by Admin.
- At query time, expand each matched term into an `OR` of its group before building the `tsquery`.
- Seed with an initial list agreed with ITPED, for example AT&C, DT and distribution transformer, RDSS, AMI and smart meter.

**Security**

- Admin only. Changes are audited.

**Acceptance criteria**

- [ ] A synonym added by Admin changes results without a deployment

**Tests:** `test_fr_5_4_synonym_expands_query`.

---

### P5-SRCH-03 — Add ranking, duplicate detection, related items and unmet-query reports

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 8 | Dev | `P5-SRCH-01` | FR-5.5, D-04 |

**Goal:** better results, fewer duplicate uploads, and a list of what users looked for but did not find.

**Scope**

- Ranking: combine `ts_rank_cd` with a small boost for AIDA Endorsed items and recent items. Keep the weights in settings.
- Duplicate detection: on submission, warn the submitter and Admin when the `sha256` matches an existing file, or when `pg_trgm` title similarity is above 0.8.
- Related items: on the item page, show up to 5 items from the same subcategory ranked by text similarity, through `visible_items()`.
- Unmet-query report: an Admin page listing top zero-result and low-result searches by week (D-04).

**Security**

- Duplicate warnings never reveal a Restricted item's title to a Member of another Discom. Show only "A similar item already exists" to Members.

**Acceptance criteria**

- [ ] An identical file triggers a duplicate warning
- [ ] Related items never include items the viewer cannot see
- [ ] The unmet-query report matches `search_log`

**Tests:** `test_fr_5_5_duplicate_file_warned`, `test_fr_5_5_related_items_visible_only`, `test_fr_5_5_unmet_query_report`.

---

### P5-SRCH-04 — Add taxonomy and search-term reconfiguration

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P2-CON-01`, `P5-SRCH-02` | FR-5.6 |

**Goal:** ITPED can merge, split and move subcategories as the collection grows, without breaking existing items.

**Scope**

- Admin actions to merge one subcategory into another (moving its items) and to move a subcategory to another module.
- A preview showing how many items each change affects, before confirming.
- Rebuild the search vectors of affected items in a background job.

**Security**

- Admin only. Each change is audited with the list of affected item IDs.

**Acceptance criteria**

- [ ] Merging two subcategories moves every item and keeps them searchable

**Tests:** `test_fr_5_6_merge_subcategories`, `test_fr_5_6_reindex_after_move`.

---

### P5-PUB-01 — Add search-engine indexing, sitemap and no-index rules

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev | `P3-PUB-02` | FR-13.9 |

**Goal:** public content can be found through search engines, and nothing else can.

**Scope**

- `/sitemap.xml` listing Public items, published expert profiles and Gallery listings, built from `visible_items()` for a visitor.
- `robots.txt` allowing public pages and disallowing login, member and admin paths.
- `<meta name="robots" content="noindex">` on teaser pages and every logged-in page.

**Security**

- The sitemap uses the visitor's view, so Restricted items flagged No can never appear in it.

**Acceptance criteria**

- [ ] The sitemap lists only Public items and public directory entries
- [ ] Teaser pages carry `noindex`

**Tests:** `test_fr_13_9_sitemap_public_only`, `test_fr_13_9_teaser_noindex`.

---

### P5-NOT-01 — Build the email digest and per-item alerts

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 5 | Dev | `P2-WF-05`, `P1-ACC-03` | FR-6.5 |

**Goal:** Members hear about new content in their areas without visiting the portal.

**Scope**

- Member preferences: subscribe to modules and subcategories, and choose digest (daily or weekly) or none.
- A Celery beat job that sends each subscriber a digest of newly published items they can open, using `send_email()`. The frequency default comes from `digest_frequency`.
- Workflow notifications from `P2-WF-05` are also sent by email.
- An unsubscribe link in every email, signed so it works without login.

**Security**

- Emails include only fields the recipient may see, built from `ItemMemberView`.
- Unsubscribe tokens are signed and only allow unsubscribing.

**Acceptance criteria**

- [ ] A subscriber receives a digest with the right items, and none they cannot open
- [ ] The unsubscribe link works without login

**Tests:** `test_fr_6_5_digest_contains_visible_items`, `test_fr_6_5_unsubscribe_link`.

---

### P5-NOT-02 — Build usefulness feedback

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P3-LIST-01` | FR-6.7 |

**Goal:** Members can say whether an item was useful, and ITPED can see the result.

**Scope**

- A "Was this useful? Yes / No" control on the item page for Members, one vote per Member login per item, changeable.
- An optional comment of up to 500 characters, visible to privileged users only.
- Totals on the Admin item page and in KPIs.

**Security**

- Members only, as the SRS gives visitors no rating function (FR-13.1).
- Comments are escaped on output.

**Acceptance criteria**

- [ ] A Member can vote once and change the vote
- [ ] Visitors do not see the control

**Tests:** `test_fr_6_7_one_vote_per_member`, `test_fr_6_7_visitor_cannot_vote`.

---

### P5-NOT-03 — Add one extra notification email per Discom

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev | `P5-NOT-01` | FR-6.8 |

**Goal:** a Discom can send notifications to a second address, such as a shared team inbox.

**Scope**

- An optional extra address on the Discom profile, which must match the Discom's email domain (D-11).
- The address is verified by a confirmation link before use.
- Digests and workflow notifications go to both addresses.

**Security**

- Changes are audited, and the old address is told when the extra address changes.

**Acceptance criteria**

- [ ] Only one extra address is allowed, and it must be verified

**Tests:** `test_fr_6_8_extra_email_domain_match`, `test_fr_6_8_extra_email_verified`.

---

### P5-END-01 — Make AIDA Endorsed criteria configurable

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P2-END-01` | FR-9.4, R-05 |

**Goal:** ITPED can change the endorsement criteria and disclaimer without a deployment.

**Scope**

- An Admin page listing the criteria as a checklist, and the disclaimer text.
- The Approver's endorse dialog shows the checklist, and every item must be ticked to apply the tag.
- Store the criteria version with each endorsement.

**Security**

- Admin edits the criteria. Only the Approver applies the tag. Both are audited.

**Acceptance criteria**

- [ ] Changing the criteria changes the Approver's checklist at once
- [ ] Each endorsement records which criteria version was used

**Tests:** `test_fr_9_4_criteria_configurable`, `test_fr_9_4_endorsement_records_version`.

---

### P5-GAL-01 — Make Gallery entry conditions configurable

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P3-GAL-01` | FR-7.8, R-05 |

**Goal:** ITPED can change what a provider must show to be listed, as the fee model is finalised.

**Scope**

- An Admin page for Gallery entry conditions: a checklist, and whether field-deployment evidence and a technical validation summary are required.
- The Reviewer's screen shows the checklist, and forwarding needs every condition met.

**Security**

- Admin only, and audited.

**Acceptance criteria**

- [ ] A new condition appears on the Reviewer's checklist and blocks forwarding until met

**Tests:** `test_fr_7_8_conditions_configurable`.

---

### P5-EXP-01 — Handle an expert's change of organisation

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P3-EXP-02` | FR-8.6 |

**Goal:** when an expert moves organisation, the directory stays correct and their consent is reconfirmed.

**Scope**

- An Admin action "Record change of organisation" that sets the new organisation and hides the profile until consent is reconfirmed for the new organisation.
- The reconfirmed profile goes through the workflow again as a substantive change.
- The previous organisation is kept in the history, not shown publicly.

**Security**

- No personal data is shown during the gap.

**Acceptance criteria**

- [ ] After a change, the profile is hidden until reconfirmed and approved

**Tests:** `test_fr_8_6_org_change_hides_profile`, `test_fr_8_6_reconfirmed_profile_republished`.

---

### P5-KPI-01 — Build the KPI dashboard and manual-entry form

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 8 | Dev | `P4-KPI-01` | FR-11.1, FR-11.2, FR-11.3 |

**Goal:** ITPED sees every SRS KPI on one page, combining system data with figures entered by hand.

**Scope**

- An Admin and Approver dashboard using `app/kpi/queries.py`, with a month picker and a comparison with the previous month.
- Server-rendered charts, so no JavaScript charting library is needed. Use simple SVG bar charts from a Jinja macro, with a data table under each chart for accessibility.
- A manual-entry form for KPIs the system cannot measure, such as Discom adoption reported in meetings, with month, value, source and notes.
- Each KPI shows whether it is system-generated or manual.

**Security**

- Admin and Approver only. Manual entries are audited.

**Acceptance criteria**

- [ ] Every KPI listed in FR-11 appears on the dashboard
- [ ] Each chart has a data table with the same figures

**Tests:** `test_fr_11_3_dashboard_shows_all_kpis`, `test_fr_11_3_manual_entry_audited`.

---

### P5-KPI-02 — Add KPI CSV export

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev | `P5-KPI-01` | FR-11.4 |

**Goal:** ITPED can take KPI figures into its own reports.

**Scope**

- An "Export CSV" button on the dashboard for the chosen months, using the standard library `csv` module.

**Security**

- Prefix cells that start with `=`, `+`, `-` or `@` with a `'` to prevent formula injection in spreadsheets.

**Acceptance criteria**

- [ ] The CSV matches the dashboard figures, and opens in Excel without formulas running

**Tests:** `test_fr_11_4_csv_matches_dashboard`, `test_fr_11_4_csv_formula_injection_escaped`.

---

### P5-REP-01 — Build role-based reporting views

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P5-KPI-01` | FR-12.2 |

**Goal:** each role sees the reports relevant to it.

**Scope**

- Member: its own Discom's submissions, their states and turnaround, and downloads of its published items.
- Reviewer: its queue size, age and items reviewed per month.
- Approver: pending approvals, turnaround and endorsements.
- Admin: everything, including audit summaries.

**Security**

- Member reports are filtered to the Member's own Discom on the server.

**Acceptance criteria**

- [ ] A Member report never includes another Discom's data

**Tests:** `test_fr_12_2_member_report_own_discom`, `test_fr_12_2_role_reports`.

---

### P5-QA-01 — Test all Phase 5 features

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 13 | QA | Each Phase 5 Dev task, as it lands | GL-03 to GL-07 |

**Goal:** every Phase 5 feature is proven on staging.

**Scope**

- Test each Phase 5 task's acceptance criteria end to end.
- Prove GL-03 (review-date countersign), GL-04 (recusal), GL-05 (SCORM 1.2 and 2004), GL-06 (broken link) and GL-07 (internal workspace).

**Security**

- Try a malicious SCORM package (path traversal, zip bomb and EICAR inside).
- Try workspace URLs as every non-Admin role.
- Point an external link at an internal address and confirm it is never requested.

**Acceptance criteria**

- [ ] GL-03 to GL-07 pass on staging

**Tests:** `tests/e2e/` scenarios for each feature.

---

### P5-QA-02 — Run full regression

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 5 | QA | `P5-QA-01` | SRS Section 8, AC-01 to AC-22 |

**Goal:** Phase 5 did not break anything in the MVP.

**Scope**

- Run the full automated suite and every MVP scenario.
- Re-run the sentinel and direct-URL scans with the new features in place.

**Security**

- Confirm the route registry test covers every new route.

**Acceptance criteria**

- [ ] AC-01 to AC-22 still pass

**Tests:** the regression run record.
