# Phase 3: Discovery and directories

**Dates:** 8 to 10 December 2026 · **Tasks:** 16 · **Points:** 37 (Dev 28, QA 9)

**Goal:** members and visitors can find, view and download what they are entitled to, and the experts directory and Gallery work. Features freeze at the end of 10 December.

**Work streams**

- **Stream A (discovery and public access):** VIEW, LIST, SRCH, PUB and UI tasks
- **Stream B (directories):** EXP and GAL tasks

**Exit criteria**

- [ ] A visitor cannot reach a Restricted file by direct URL
- [ ] A Restricted item flagged No is absent from public listings, search and counts
- [ ] Experts and Gallery listings pass the workflow and show correctly to visitors and members

---

### P3-VIEW-03 — Build protected file delivery and MP4 and MP3 streaming

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev A | `P2-CON-06`, `P2-UPL-03` | FR-3.5, FR-6.6, FR-7.5, [architecture.md](../architecture.md) protected download |

**Goal:** every file is served only after a permission check, and video and audio stream with seeking.

Build this first in Stream A, because the viewers and the Gallery depend on it.

**Scope**

- `app/content/delivery.py` with `protected_file_response(viewer, item, file, disposition)` that:
    1. Calls `can_open()` and returns 404 if it fails.
    2. Records the view or download (`P3-LIST-02`).
    3. Returns an `X-Accel-Redirect` to the internal Nginx location with a presigned storage URL valid for 60 seconds.
- Nginx internal location proxying to storage, with range requests enabled.
- Routes `/items/{item_id}/files/{file_id}/view` (inline) and `/download` (attachment), with the original file name in `Content-Disposition`.
- An HTML5 video and audio player inside a responsive 16:9 container that keeps the source aspect ratio (FR-3.5).
- Use `ffprobe` in the worker to record width, height and duration. Show the Reviewer a warning when a video is not 16:9.

**Security**

- Storage URLs never reach the browser.
- Restricted responses send `Cache-Control: private, no-store`.
- A file belonging to a different item than the URL's item is refused.
- Quarantined, pending and errored files are never served.

**Acceptance criteria**

- [ ] A Member can stream an MP4 and seek forward without downloading it first
- [ ] A visitor requesting a Restricted file URL gets 404 (AC-16)
- [ ] The storage URL does not appear in any response body or header seen by the browser

**Tests:** `test_fr_6_6_restricted_file_404_for_visitor`, `test_fr_6_6_range_request_supported`, `test_p3_view_03_file_must_belong_to_item`, `test_p3_view_03_unscanned_file_not_served`.

---

### P3-VIEW-01 — Build PDF and image viewers

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev A | `P3-VIEW-03` | FR-6.6 |

**Goal:** PDF and image items open in the browser.

**Scope**

- PDF.js, vendored, showing PDFs from the protected `view` route.
- Images shown with `alt` text set to the item title.
- A Download button using the `download` route.

**Security**

- PDF.js is loaded from `static/` under the strict Content Security Policy.

**Acceptance criteria**

- [ ] PDF and image items open in the browser for entitled viewers (part of AC-13)
- [ ] The viewer can be used by keyboard

**Tests:** `test_fr_6_6_pdf_viewer_loads`, plus a Playwright check.

---

### P3-VIEW-02 — Add the Office-to-PDF preview job

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev A | `P2-UPL-03` | FR-6.6 |

**Goal:** Word, Excel, PowerPoint and CSV files can be read in the browser as a PDF preview.

**Scope**

- A Celery task `make_preview(file_id)`, queued after a clean scan, that converts with `soffice --headless --convert-to pdf` in a fresh temporary directory, with a 120-second timeout.
- Store the result under `previews/` and set `preview_storage_key`.
- Run this on a worker queue with concurrency 1, because LibreOffice is not safe to run in parallel in one process.
- If conversion fails, show "Preview not available. Download the file to view it."

**Security**

- LibreOffice runs without network access, under the worker's non-root user, and macros are disabled.
- Temporary directories are always deleted.

**Acceptance criteria**

- [ ] DOCX, XLSX, PPTX and CSV items show a PDF preview (part of AC-13)
- [ ] A file that cannot be converted shows the fallback message

**Tests:** `test_fr_6_6_office_preview_created`, `test_fr_6_6_preview_failure_fallback`.

---

### P3-LIST-02 — Add separate view and download counters

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev A | `P3-VIEW-03` | FR-6.4, FR-11.1, D-05, D-13 |

**Goal:** views and downloads are counted separately and correctly.

**Scope**

- `view_event` and `download_event` tables: `item_id`, `file_id`, `actor_kind`, `login_id`, `session_id`, `ip_hash` and `at`.
- Increment `view_count` and `download_count` with a single atomic `UPDATE ... SET x = x + 1`.
- Count Members and visitors only. Views and downloads by Admin, Reviewer and Approver are logged but not counted (D-13).
- Show the download count on the item as "Downloads" (FR-6.4).

**Security**

- IP addresses are stored as a salted hash, with the salt from the environment.

**Acceptance criteria**

- [ ] Each download adds one to `download_count`, including anonymous downloads (FR-13.8)
- [ ] Opening an item page adds one to `view_count`
- [ ] Privileged views do not change either count

**Tests:** `test_fr_6_4_download_increments_count`, `test_d13_privileged_views_not_counted`, `test_fr_13_8_anonymous_downloads_counted`.

---

### P3-LIST-01 — Build listings, ordering, Newly Added and attribution

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev A | `P2-WF-04`, `P2-CON-06`, `P3-LIST-02` | FR-6.1, FR-6.2, FR-6.3 |

**Goal:** each module shows its items in a clear, sortable list, and new items are highlighted.

**Scope**

- A module page listing items from `visible_items()`, 20 per page.
- Default order is date of posting, newest first. A sort control offers Most Viewed (FR-6.2).
- An item card showing title, Category and Subcategory tags, date of posting, year of original publication, source organisation, summary, download count, and the Endorsed badge where applied (FR-6.3).
- An item detail page with the same attribution, plus the viewer or link.
- A Newly Added area separate from the listings, showing up to `newly_added_count` items published in the last `newly_added_days` days, newest first (FR-6.1).

**Security**

- Counts shown on module pages, such as "42 items", come from `visible_items()`, so they match what the viewer can see.

**Acceptance criteria**

- [ ] Listings default to newest first and can be sorted by Most Viewed
- [ ] Newly Added follows the two settings
- [ ] Every card shows the FR-6.3 fields and no admin-only field

**Tests:** `test_fr_6_1_newly_added_window`, `test_fr_6_2_default_order_newest`, `test_fr_6_2_most_viewed_order`, `test_fr_6_3_card_fields`.

---

### P3-SRCH-01 — Build browsing, central search and module search

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev A | `P3-LIST-01` | FR-5.1, FR-5.2, FR-5.7, FR-6.2, D-04 |

**Goal:** users find items by keyword across the repository or within one module, and filter by the allowed facets only.

**Scope**

- A `search_vector` column on `content_version`, weighted: title A, summary B, source organisation and subcategory name C. Use the PostgreSQL `english` configuration and a GIN index.
- `app/search/service.py` with `search(db, viewer, query, module=None, filters)`, using `websearch_to_tsquery` over `visible_items()`.
- Filters: Category, Subcategory and date of posting range only (FR-5.1). Never functional group, access tier or jurisdiction.
- A central search box in the header for the whole repository (FR-5.2), and a search box on each module page limited to that module (FR-5.7).
- Results ranked by relevance, offering Most Relevant ordering (FR-6.2), with newest first as an alternative.
- A `search_log` table: `query`, `module`, `filters`, `result_count`, `result_item_ids` (up to the first 50), `actor_kind` and `at`. Every search is logged, including zero-result searches (D-04).

**Security**

- Restricted items flagged No never appear for visitors, in results or in result counts.
- Teasers in visitor results show teaser fields only.
- Search is rate limited in Nginx.

**Acceptance criteria**

- [ ] Central search finds items across modules, and module search returns only that module's items (AC-14)
- [ ] Filters offer only Category, Subcategory and date
- [ ] A search with no results is logged with `result_count = 0`

**Tests:** `test_fr_5_2_central_search_all_modules`, `test_fr_5_7_module_search_scoped`, `test_fr_5_1_no_admin_facets`, `test_d04_zero_result_logged`, `test_fr_13_3_flag_no_absent_from_search`.

---

### P3-PUB-01 — Build the public home, About, Contact and legal notices

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev A | `P1-UI-01`, `P3-LIST-01` | FR-3.1, FR-13.1, FR-13.10, SRS 5.7, Q-10 |

**Goal:** anyone can open the portal without logging in and see what it offers.

**Scope**

- A public home page at the portal address showing:
    - the six modules (FR-3.1)
    - the central search
    - a Newly Added strip with Public items and permitted teasers only
    - "Member Login" and "Register your Discom" buttons
    - links to About and Contact ITPED
- An About page, and a Contact ITPED link to ITPED's address.
- Terms of use, disclaimer, privacy notice and cookie notice pages, linked from the footer of every public page (FR-13.10). Placeholder text, clearly marked, until ITPED supplies it (Q-10).
- No submission, notification or rating function is offered to visitors.

**Security**

- The portal uses only essential cookies, so the cookie notice informs rather than asking for consent. If analytics are ever added, a consent step is needed first.

**Acceptance criteria**

- [ ] The home page works without login and shows every FR-13.1 element
- [ ] Every public page has the four notice links in its footer

**Tests:** `test_fr_13_1_public_home_elements`, `test_fr_13_10_notice_links_on_public_pages`.

---

### P3-PUB-02 — Build public item pages, teasers and the "items I can open" filter

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev A | `P2-CON-06`, `P3-LIST-01`, `P3-SRCH-01` | FR-13.2, FR-13.3, FR-13.5, D-03 |

**Goal:** visitors get Public items in full, Restricted teasers only where allowed, and nothing else.

**Scope**

- Public item page (FR-13.2): title, Category and Subcategory, date of posting, year, source organisation, summary, download count, and the Endorsed badge with disclaimer. View in the browser and download without login.
- Teaser page for Restricted items with teaser Yes (FR-13.3): title, Category and Subcategory, source organisation, year and summary only. Add the label "Available to member Discoms – log in" with a login link. No file, preview, download link or file name.
- Restricted items with teaser No return 404 and are left out of every listing, search result and count.
- A "Show only items I can open" filter for visitors on listings and search (FR-13.5). This filter and the lock label are the only places the tier shows (D-03).

**Security**

- The teaser page renders from `ItemTeaserView`, which has no file fields, so a file name cannot leak.
- Check the HTML source, `meta` tags and any HTMX partials for file names or storage keys.
- Teaser and Restricted pages send `Cache-Control: private, no-store`.

**Acceptance criteria**

- [ ] A Public item opens and downloads without login (AC-15)
- [ ] A teaser page contains no file name, preview or download link
- [ ] A Restricted item flagged No is absent from listings, search and counts (AC-17)

**Tests:** `test_fr_13_2_public_item_full`, `test_fr_13_3_teaser_hides_file_name`, `test_fr_13_3_flag_no_returns_404`, `test_fr_13_5_openable_filter`, `test_d03_tier_value_never_rendered`.

---

### P3-UI-01 — Build the Member dashboard, privileged console and audit search

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev A | `P2-WF-02`, `P2-WF-05`, `P1-AUD-01` | SRS 4.1, FR-4.8, FR-12.1 |

**Goal:** each user lands on a dashboard showing what needs their attention.

**Scope**

- Member dashboard: the Discom's own submissions with state, last action and any return reasons, plus Newly Added and notifications.
- Privileged console: the queue for the user's role, filterable by module and category, with counts. Admin-only fields are editable only here (SRS 4.1).
- Admin audit search: filter by actor, action, target and date over the last 180 days (FR-12.1), with paging.

**Security**

- Members see only their own Discom's submissions.
- The audit search is Admin only, and its use is itself audited.

**Acceptance criteria**

- [ ] Each role's dashboard shows its items and nothing beyond its rights
- [ ] Admin can find any audit event from the last 180 days

**Tests:** `test_srs_4_1_member_dashboard_own_items`, `test_fr_12_1_audit_search_180_days`, `test_p3_ui_01_audit_search_admin_only`.

---

### P3-EXP-01 — Build expert entry, consent capture and workflow

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev B | `P2-WF-01` | FR-8.1, FR-8.2, FR-8.4, SRS Appendix B, SRS 5.7 |

**Goal:** Admin can record an expert's profile and consent, and the profile passes the workflow before it is shown.

**Scope**

- An `expert_profile` table with Appendix B fields:
    - name, `present_organisation_id` or `other_organisation` text
    - years of experience, email, areas of expertise (a list)
    - supporting credentials (admin-only)
    - consent: a public flag for each field
    - `consent_recorded_by`, `consent_recorded_at`, `consent_notes`, `privacy_notice_version`
    - `state` and `withdrawn_at`
- An Admin form "Add expert on their behalf", with a consent section listing each field and a confirmation that the privacy notice was given.
- Run the profile through `apply_action()` with subject type `expert`, reusing the Reviewer and Approver queues with a type filter.

**Security**

- Admin only. Experts never get a login (FR-2.1).
- Submit is refused unless consent is recorded.
- Personal data in audit details is limited to the profile ID.

**Acceptance criteria**

- [ ] Admin can create a profile with consent, and it passes Reviewer and Approver to publication
- [ ] Submitting without recorded consent is refused

**Tests:** `test_fr_8_1_admin_creates_expert`, `test_fr_8_2_consent_required`, `test_fr_8_4_expert_workflow`.

---

### P3-EXP-02 — Build expert display, Discom filter, withdrawal and email protection

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev B | `P3-EXP-01` | FR-8.2, FR-8.3, FR-8.5, FR-13.6, D-02 |

**Goal:** the Go-To Discom Partner module lists published experts with only the fields they agreed to show.

**Scope**

- A Go-To Discom Partner module page listing published experts, filterable by Discom and by area of expertise (FR-8.5).
- Experts whose organisation is not a Discom are grouped under "Other organisations".
- Show only consented fields, to Members and visitors (D-02, FR-8.2).
- Email addresses are hidden behind a "Show email" button that fetches the address through HTMX, rate limited per IP (FR-13.6).
- Admin "Record consent withdrawal" action: the profile is hidden at once (FR-8.3).
- A daily Celery beat job clears the personal fields 2 working days after withdrawal, keeping only the ID and state. Working days are Monday to Friday.

**Security**

- Email addresses never appear in page HTML until revealed.
- A withdrawn profile disappears from all lists and searches immediately.

**Acceptance criteria**

- [ ] Only consented fields appear in any view
- [ ] Withdrawal hides the profile immediately (AC-19), and personal data is cleared within 2 working days
- [ ] The email is not in the page source before "Show email" is used

**Tests:** `test_fr_8_2_only_consented_fields_shown`, `test_fr_8_3_withdrawal_hides_immediately`, `test_fr_8_3_personal_data_cleared`, `test_fr_13_6_email_not_in_source`, `test_fr_8_5_filter_by_discom`.

---

### P3-GAL-01 — Build Gallery entry, fee terms, workflow and attribution

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev B | `P2-WF-01`, `P2-UPL-01` | FR-7.1, FR-7.2, FR-7.3, FR-7.6, SRS Appendix C, D-02 |

**Goal:** Admin can enter a technology provider's listing, and it is published only after sign-off, including the fee terms.

**Scope**

- A `tech_listing` table with Appendix C fields:
    - solution name, provider organisation, subject area (optional subcategory)
    - provider's description (the provider's own claims)
    - evidence of field deployment, with optional files
    - technical validation summary
    - demonstration video file
    - proposed listing and fee terms (text), and provider consent recorded
    - `state`, `published_at`
- An Admin form "Add listing on the provider's behalf". Uploads use the tusd path and limits from Phase 2.
- Run it through `apply_action()` with subject type `gallery`. At approval, the Approver also confirms the listing and fee terms (FR-7.3).
- A Gallery module page showing provider organisation, category and date of listing (FR-7.6), visible to Members and visitors (D-02).

**Security**

- Admin only for entry. Providers never get a login.
- Fee terms are visible only to privileged users.

**Acceptance criteria**

- [ ] A listing passes the workflow, and the Approver must confirm fee terms to approve
- [ ] A published listing shows provider, category and date of listing

**Tests:** `test_fr_7_2_admin_creates_listing`, `test_fr_7_3_fee_terms_confirmed_at_approval`, `test_fr_7_6_listing_attribution`, `test_p3_gal_01_fee_terms_admin_only`.

---

### P3-GAL-02 — Add paid disclosure, evidence labels, declarations and video

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev B | `P3-GAL-01`, `P3-VIEW-03` | FR-7.4, FR-7.5, FR-7.7 |

**Goal:** visitors can always tell a paid listing and the provider's own claims apart from independent evidence, and reviewers declare they have no conflict.

**Scope**

- A "Paid placement" label on every listing card and listing page (FR-7.4).
- Two clearly separated sections, with headings and different styling: "Provider's description" and "Independently evidenced field deployment".
- The demonstration video plays through `protected_file_response()` in the 16:9 player (FR-7.5).
- Before acting on a listing, the Reviewer and the Approver must confirm "I have no financial interest in this listing fee". The confirmation is stored with login and time, and the action is blocked until it is recorded (FR-7.7).

**Security**

- The declaration check runs on the server inside `apply_action()`, not only in the browser.

**Acceptance criteria**

- [ ] Every listing shows the paid-placement label (AC-20)
- [ ] Forwarding or approving without a declaration is refused
- [ ] The video streams with seeking

**Tests:** `test_fr_7_4_paid_label_shown`, `test_fr_7_7_declaration_required`, `test_fr_7_5_video_streams`.

---

### P3-QA-01 — Test viewing, listings and search

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | QA | Stream A tasks | AC-13, AC-14 |

**Goal:** end-to-end proof that members can find and open everything they are entitled to.

**Scope**

- Open one item of every format in the browser (AC-13).
- Run central and module searches with known expected results (AC-14).
- Check listing order, Most Viewed, Newly Added and download counts.

**Security**

- Confirm no admin-only facet appears in search.

**Acceptance criteria**

- [ ] AC-13 and AC-14 pass on staging

**Tests:** `tests/e2e/test_viewing.py`, `tests/e2e/test_search.py`.

---

### P3-QA-02 — Test public access, teasers and direct-URL blocking

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | QA | `P3-PUB-01`, `P3-PUB-02`, `P3-VIEW-03` | AC-15, AC-16, AC-17, AC-18 |

**Goal:** proof that visitors get exactly what FR-13 allows, and nothing more.

**Scope**

- As a visitor: open and download a Public item (AC-15).
- Request a Restricted file's view and download URLs directly, both logged out and as a Member of another type (AC-16).
- Confirm a flagged-No item is absent from the home page, listings, search, counts and its own URL (AC-17).
- Repeat the admin-only sentinel scan from `P2-QA-03` on every public page (AC-18).

**Security**

- Guess item and file IDs by changing URLs, and confirm only 404s come back.

**Acceptance criteria**

- [ ] AC-15, AC-16, AC-17 and AC-18 pass on staging

**Tests:** `tests/e2e/test_public_access.py`.

---

### P3-QA-03 — Test experts, consent withdrawal and the Gallery

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | QA | Stream B tasks | AC-08, AC-19, AC-20 |

**Goal:** proof that the directories follow the same governance and privacy rules.

**Scope**

- Run an expert profile and a Gallery listing through the full workflow (AC-08).
- Withdraw an expert's consent and confirm the profile disappears at once (AC-19).
- Confirm the paid-placement label and the declaration block (AC-20).

**Security**

- Confirm expert emails are not in the page source.

**Acceptance criteria**

- [ ] AC-08, AC-19 and AC-20 pass on staging

**Tests:** `tests/e2e/test_experts.py`, `tests/e2e/test_gallery.py`.
