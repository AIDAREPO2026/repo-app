# Phase 2: Content and governance

**Dates:** 1 to 7 December 2026 · **Tasks:** 22 · **Points:** 51 (Dev 40, QA 11)

**Goal:** Members and Admin can submit content safely, and every item passes Admin, Reviewer and Approver before it is published.

**Build order:** `P2-CON-01` → `P2-CON-02` → `P2-CON-06` and `P2-WF-01`, while `P2-UPL-01` → `P2-UPL-02` → `P2-UPL-03` run in parallel. Then `P2-CON-03` to `P2-CON-05` and `P2-WF-02` to `P2-WF-06`. `P2-CON-07`, `P2-END-01` and `P2-SEC-01` come last.

**Exit criteria**

- [ ] An item passes every workflow path in [workflow.md](../workflow.md)
- [ ] An infected file is quarantined, a 1 GB upload resumes, and a 21 MB image is refused before upload
- [ ] Admin-only fields never appear in any Member view

---

### P2-CON-01 — Build the six modules, taxonomy and Admin tag configuration

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P0-GOV-02`, `P1-ACC-08` | FR-3.1, FR-3.10, SRS Appendix A, [decisions.md](../decisions.md) taxonomy |

**Goal:** the six home-screen modules and their subcategories exist, and Admin can change subcategories and functional groups without a code change.

**Scope**

- A `module` table, seeded with the six modules in [decisions.md](../decisions.md): slug, name, kind (`documents`, `experts` or `gallery`) and display order. Modules are fixed and have no edit screen.
- A `subcategory` table (module, name, slug, status `active` or `retired`, display order), seeded with the 12 subcategories.
- A `functional_group` table (name, status, display order), seeded with the six groups.
- Admin screens to add, rename, reorder and retire subcategories and functional groups (FR-3.10).
- A retired value is hidden from new submissions, while existing items keep it.

**Security**

- Admin only. Every change is audited with old and new values.

**Acceptance criteria**

- [ ] The seed creates 6 modules, 12 subcategories and 6 functional groups
- [ ] Admin can add, rename and retire a subcategory without a deployment
- [ ] A retired subcategory is not offered on the submission form, but existing items still show it

**Tests:** `test_fr_3_1_seed_taxonomy`, `test_fr_3_10_admin_adds_subcategory`, `test_fr_3_10_retired_value_hidden_from_new_items`.

---

### P2-CON-02 — Build the content model with tiers, owner fields and view schemas

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P2-CON-01`, `P0-ARC-01` | FR-2.4, FR-2.5, FR-3.2, FR-3.3, FR-3.6, FR-3.7, D-03, D-09, SRS Appendix A |

**Goal:** content is stored with every Appendix A field, versioned for substantive edits, and impossible to render with admin-only fields for the wrong audience.

**Scope**

- `content_item`:
    - `id`, `item_type` (`file` or `external_link`), `state`
    - `published_version_id`, `working_version_id`
    - `submitting_organisation_id`, `source_organisation` (display text, FR-2.4)
    - `owner_login_id`, `reviewer_login_id`, `approver_login_id`
    - `next_review_date` (used from Phase 5)
    - `endorsement_candidate`, `endorsed`, `endorsed_at`, `endorsed_by`
    - `view_count`, `download_count`
    - `published_at` (date of posting), `discarded_at`, `created_by`, `created_at`, `updated_at`
- `content_version`:
    - `title`, `module_id`, `subcategory_id`, `functional_group_id`
    - `access_tier` (`public` or `restricted`, never null once submitted)
    - `jurisdiction` (text) and `jurisdiction_organisation_id` (nullable)
    - `original_source`, `year_of_publication`, `summary`, `external_url`
    - `rights_declaration`, `rights_declared_by`, `rights_declared_at`
    - `public_teaser` (`yes`, `no` or null)
    - `created_by` and `created_at`
- `content_file`: `version_id`, `storage_key`, `original_filename`, `extension`, `mime_type`, `size_bytes`, `sha256`, `scan_status` (`pending`, `clean`, `infected`, `type_mismatch` or `error`), `scanned_at`, `preview_storage_key`, plus `width`, `height` and `duration_seconds` for media.
- View schemas in `app/content/schemas.py`:
    - `ItemPublicView` and `ItemTeaserView` for visitors
    - `ItemMemberView` for Members
    - `ItemAdminView` for privileged users

    Only `ItemAdminView` contains functional group, access tier, jurisdiction, rights declaration, teaser flag, owner, Reviewer, Approver and next-review fields (FR-3.3, FR-3.7).
- Service functions return a view schema, never a database row, to routes that render Member or public pages.

**Security**

- The access tier is required at submission. If it is somehow missing, the item is treated as Restricted and hidden from visitors (SRS 5.3).
- `source_organisation` cannot be changed by Admin or Reviewer edits (FR-2.4).
- A test builds each non-admin view from a fully filled item and asserts the admin-only field names and values are absent.

**Acceptance criteria**

- [ ] Migrations create the three tables with the constraints from `docs/data-model.md`
- [ ] Each non-admin view schema lacks every admin-only field
- [ ] An item with a missing tier is treated as Restricted

**Tests:** `test_fr_3_3_member_view_has_no_admin_fields`, `test_fr_3_3_public_view_has_no_admin_fields`, `test_fr_3_7_owner_fields_admin_only`, `test_p2_con_02_missing_tier_treated_as_restricted`, `test_fr_2_4_source_organisation_immutable`.

---

### P2-CON-06 — Build the single item-visibility module

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P2-CON-02` | FR-2.5, FR-13.2, FR-13.3, SRS 5.3, D-03, [security.md](../security.md) access control |

**Goal:** one place decides who can see, preview or open every item, and every other feature uses it.

**Scope**

- `app/content/visibility.py` with:
    - `visible_items(db, viewer)`: a SQLAlchemy select of items the viewer may list, for listings, search and counts
    - `can_open(viewer, item)`: whether the viewer may view or download files
    - `can_see_teaser(viewer, item)`: whether the viewer sees only the teaser
- Rules:

| Viewer | Published Public | Published Restricted, teaser Yes | Published Restricted, teaser No | Not published | Retired |
| --- | --- | --- | --- | --- | --- |
| Visitor | Open | Teaser only | Invisible | Invisible | Invisible |
| Member | Open | Open | Open | Its own Discom's submissions: status only | Invisible |
| Admin, Reviewer, Approver | Open | Open | Open | Open | Open |

- An item whose access tier is missing is treated as Restricted with teaser No.

**Security**

- This module is security-sensitive and needs two reviewers.
- A table-driven test covers every cell of the rules table.
- Listings, search, counts, item pages, file delivery and the sitemap must all use these functions. No route may filter items by hand.

**Acceptance criteria**

- [ ] Every combination in the rules table is covered by a test and passes
- [ ] A search for code that filters `access_tier` outside this module finds nothing

**Tests:** `test_fr_2_5_visibility_matrix` (parameterised over viewer, state, tier and teaser), `test_p2_con_06_missing_tier_defaults_to_restricted`.

---

### P2-UPL-01 — Integrate tusd and Uppy for resumable uploads

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P0-OPS-02`, `P1-ACC-06` | FR-3.12, [architecture.md](../architecture.md) upload flow |

**Goal:** large files upload reliably and resume after interruption, using one upload path for every file size.

**Scope**

- Configure tusd to store into `incoming/` on the object storage, with hooks pointing at the app's internal hook endpoints.
- Nginx proxies `/files/` to tusd and passes the session cookie through.
- `app/content/uploads.py` with:
    - a pre-create hook: checks the session, the login type and a draft the user may edit
    - a post-finish hook: creates the `content_file` row with `scan_status = pending` and queues `scan_file`
- Uppy on the submission form, sending 50 MB chunks (`RESUMABLE_CHUNK_MB`), with a progress bar, a pause and resume control, and resume after a page reload.

Format and size rules are added in `P2-UPL-02`.

**Security**

- Hook endpoints accept requests only from tusd on the internal network, with a shared secret header, and are unreachable through Nginx.
- An upload without a valid session, or for a draft the user cannot edit, is refused at pre-create.
- Uploaded files stay in `incoming/` and cannot be opened until scanned clean.

**Acceptance criteria**

- [ ] A 1 GB file uploads with a visible progress bar
- [ ] Interrupting the network and reconnecting resumes the upload rather than restarting it
- [ ] An upload without a session is refused before any data is stored

**Tests:** `test_fr_3_12_pre_create_requires_session`, `test_fr_3_12_post_finish_queues_scan`, `test_p2_upl_01_hook_rejects_missing_secret`.

---

### P2-UPL-02 — Enforce format and size limits, with images capped at 20 MB

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P2-UPL-01`, `P0-SET-02` | FR-3.5, FR-3.12, D-01, [decisions.md](../decisions.md) file formats |

**Goal:** a file that is the wrong type or too large, or that would fill the file storage, is refused before upload begins, with a message stating the limit.

**Scope**

- `app/content/formats.py`: one table of format groups, extensions, MIME types and setting keys, used by both the client and the server.
- Uppy restrictions built from that table, so the browser refuses before upload with a message such as "Images must be 20 MB or smaller. This file is 21.3 MB."
- The same check in the tusd pre-create hook, using `Upload-Length` and the file extension. The server check is the one that counts.
- A storage check in the same pre-create hook (D-14). It refuses the upload when the stored files plus `Upload-Length` would pass `storage_limit_gb`, with "The repository is full. Ask the Admin to free space or add storage." Each refusal is logged.
- SCORM ZIP files are refused until Phase 5, with "SCORM packages will be supported later."
- Help text on the form lists every limit, including the 20 MB image limit (D-01).

**Security**

- The server never trusts the client check.
- File names are never used as storage keys.

**Acceptance criteria**

- [ ] A 21 MB JPG is refused before any byte is uploaded, and the message names the 20 MB limit (AC-10)
- [ ] A 26 MB PDF and a file over 1 GB are refused the same way
- [ ] An unsupported extension is refused
- [ ] Bypassing the browser and calling tusd directly with an oversized `Upload-Length` is refused
- [ ] An upload that would pass `storage_limit_gb` is refused before any byte is stored

**Tests:** `test_fr_3_5_image_over_20mb_refused`, `test_fr_3_5_document_over_25mb_refused`, `test_fr_3_5_media_over_1gb_refused`, `test_fr_3_12_server_refuses_without_client_check`, `test_d01_error_message_states_limit`, `test_d14_upload_refused_when_storage_full`.

---

### P2-UPL-03 — Add ClamAV scanning, file-type checks and quarantine

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P2-UPL-02` | FR-3.11, [security.md](../security.md) uploads |

**Goal:** no file reaches the Admin queue, or any viewer, unless it is the type it claims to be and free of known malware.

**Scope**

- `app/core/clamav.py`: a small clamd `INSTREAM` client, about 30 lines, avoiding an unmaintained dependency.
- A Celery task `scan_file(file_id)`:
    1. Stream the file from `incoming/` to a temporary file.
    2. Sniff the type with python-magic, and compare it with the extension's format group, allowing Office ZIP and OLE containers.
    3. Scan with ClamAV.
    4. If clean, move to `files/`, record `sha256` and `scan_status = clean`.
    5. If infected or mismatched, move to `quarantine/`, set the status, notify the submitter in the portal and by email, and audit.
    6. On a scanner error, retry three times, then set `error` and alert Admin.
- Keep the `freshclam` signature updates running in the `clamav` container.

**Security**

- Temporary files are deleted in a `finally` block.
- Quarantined files are never served by any route.
- The worker runs the scan with a timeout, so a hostile file cannot hang the queue.

**Acceptance criteria**

- [ ] The EICAR test file is quarantined, and the submitter is notified (AC-12)
- [ ] A PDF renamed to `.docx` is set to `type_mismatch`
- [ ] A clean file becomes available, and its `sha256` is stored
- [ ] A submission cannot be sent while any of its files is pending or failed

**Tests:** `test_fr_3_11_eicar_quarantined`, `test_fr_3_11_type_mismatch_rejected`, `test_fr_3_11_clean_file_moved`, `test_fr_3_11_scanner_error_retries`.

---

### P2-CON-03 — Build the submission form

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P2-CON-02`, `P2-UPL-02` | FR-3.2, FR-3.4, FR-3.6, FR-4.1, SRS Appendix A |

**Goal:** a Member or Admin can create and submit a content item with every required field.

**Scope**

- A form for Members (own Discom) and Admin (ITPED-sourced items), with these fields:
    - Title, required, up to 300 characters
    - Category: one of the four document modules
    - Subcategory, filtered by module through HTMX
    - Access tier: Public or Restricted, required, with no default
    - Functional group, required
    - Applicable jurisdiction or Discom
    - Summary, required, about 2 to 4 lines (50 to 600 characters)
    - Original source and year of original publication, required (FR-3.6)
    - File upload, or an external URL (`P2-CON-05`)
- Source Organisation is filled automatically: the Member's Discom, or for Admin, the organisation ITPED names.
- Save as Draft, edit a Draft, discard a Draft, and Submit.
- Submit calls `apply_action(..., 'submit')`.
- Members can create items only in the four document modules. Experts and Gallery are Admin-only (Phase 3).

**Security**

- A Member can edit only its own Discom's Drafts and Returned items.
- All fields are validated on the server with length limits.
- The form posts with CSRF protection.

**Acceptance criteria**

- [ ] A Member can save, edit and submit an item, and it reaches Submitted
- [ ] Submitting without a required field, or with a file still being scanned, is refused with field-level errors
- [ ] A Member cannot open another Discom's Draft by changing the URL

**Tests:** `test_fr_3_2_classification_required`, `test_fr_3_6_source_and_year_required`, `test_fr_4_1_member_submits`, `test_p2_con_03_member_cannot_edit_other_discom_draft`.

---

### P2-CON-04 — Add the rights declaration, shown to the Reviewer

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev | `P2-CON-03` | FR-3.9, SRS 5.7 |

**Goal:** no item is submitted without a declaration that it may be shared.

**Scope**

- Two options on the submission form: "We hold the right to share this content" or "This content is in the public domain", plus a confirmation tick box.
- Store the choice, the login and the timestamp on the version.
- The Reviewer's screen shows the declaration at the top.

**Security**

- The declaration is admin-only and never shown to Members viewing published items or to visitors.

**Acceptance criteria**

- [ ] Submit is refused until the declaration is made
- [ ] The Reviewer screen shows who declared what, and when

**Tests:** `test_fr_3_9_declaration_required`, `test_fr_3_9_declaration_hidden_from_members`.

---

### P2-CON-05 — Add the External Link item type

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev | `P2-CON-03` | FR-3.8 |

**Goal:** an item can point to an authoritative external source instead of a hosted file.

**Scope**

- On the submission form, choose "File" or "External link". For a link, an `https` or `http` URL of up to 2,000 characters is required, and no file.
- External Link items use the same metadata, workflow and display as file items.
- The link opens in a new tab with `rel="noopener noreferrer"`.

The weekly broken-link check is `P5-CON-02`.

**Security**

- Only `http` and `https` schemes are allowed, so `javascript:` and `data:` links are refused.

**Acceptance criteria**

- [ ] A link item passes the full workflow and shows its link once published
- [ ] A `javascript:` URL is refused

**Tests:** `test_fr_3_8_link_item_workflow`, `test_fr_3_8_unsafe_scheme_refused`.

---

### P2-CON-07 — Build the bulk-import template and loader

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P2-CON-03`, `P2-UPL-03`, `P2-WF-01` | SRS 6.2, D-12, SRS Appendix A |

**Goal:** ITPED can load content prepared offline in one go.

**Scope**

- A downloadable XLSX template with one column per Appendix A field and a `file_name` column, plus a sheet explaining each column.
- An Admin page to upload the XLSX and a ZIP of the files (the ZIP uploads through tusd).
- A dry run that validates every row and lists errors per row, then an import step for valid rows.
- Each imported item enters Submitted as an ITPED-sourced item (D-12), and every file goes through `scan_file`.

**Security**

- Admin only. The ZIP is checked for path traversal and for an excessive uncompressed size before extraction.
- Every extracted file is scanned like a normal upload.
- Each import is audited with its row count.

**Acceptance criteria**

- [ ] A valid sheet with 10 rows creates 10 Submitted items, with files scanned
- [ ] A sheet with errors lists each problem by row, and imports nothing until it is fixed or the user chooses to import only valid rows
- [ ] A ZIP containing `../` paths is refused

**Tests:** `test_srs_6_2_bulk_import_creates_submitted_items`, `test_srs_6_2_dry_run_reports_errors`, `test_p2_con_07_zip_path_traversal_refused`.

---

### P2-WF-01 — Build the workflow transition table and state service

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P2-CON-02`, `P1-AUD-01` | FR-4, D-06, D-07, [workflow.md](../workflow.md) |

**Goal:** one plain, readable table decides every allowed state change, for content, experts and Gallery listings.

**Scope**

- `app/workflow/transitions.py`: a dictionary keyed by current state and action, giving the new state and the allowed login types, exactly as in `workflow.md`.
- `apply_action(db, subject, action, actor, comment=None)` that:
    1. Locks the subject row.
    2. Looks up the transition and refuses unknown or disallowed ones.
    3. Runs the guard conditions for that transition, such as rights declaration, clean files and teaser flag, each as a small named function.
    4. Updates the state.
    5. Writes a `workflow_event` and an audit event.
    6. Calls `notify()` (wired in `P2-WF-05`).
- A `workflow_event` table: `subject_type`, `subject_id`, `from_state`, `to_state`, `action`, `actor_login_id`, `comment`, `at`.

**Security**

- This is the only code that changes `state`. A test searches the code for other assignments to `state`.
- A refused transition is audited with `result = denied`.

**Acceptance criteria**

- [ ] Every row of the transitions table in `workflow.md` has a passing test, and every other combination is refused
- [ ] Rejected is final (D-06), and Pending Approval returns to Under Review (D-07)

**Tests:** `test_fr_4_allowed_transitions` (parameterised), `test_fr_4_disallowed_transitions_refused`, `test_d06_rejected_is_final`, `test_d07_approver_return_goes_to_review`, `test_p2_wf_01_state_only_changed_by_apply_action`.

---

### P2-WF-02 — Build the Admin queue: receive, edit, forward and return

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P2-WF-01`, `P2-CON-03` | FR-2.4, FR-4.2, FR-4.3 |

**Goal:** Admin receives every submission first, can correct it, and sends it on or back.

**Scope**

- An Admin queue of Submitted items, oldest first, filterable by module, category and submitting Discom.
- An item review page showing every field, including admin-only ones, the file viewer and download, and the workflow history.
- Inline editing of fields and tags. `source_organisation` is read-only (FR-2.4).
- Actions:
    - Forward to Reviewer, with the primary Reviewer as default
    - Return to the submitter, with a required reason

**Security**

- Admin only.
- Every edit is audited with old and new values, and no edit changes the attribution.

**Acceptance criteria**

- [ ] Admin sees every Submitted item, can edit its fields and forward or return it
- [ ] Source Organisation cannot be changed
- [ ] Return without a reason is refused

**Tests:** `test_fr_4_2_admin_queue_lists_submitted`, `test_fr_2_4_admin_edit_keeps_attribution`, `test_fr_4_3_return_requires_reason`.

---

### P2-WF-03 — Build Reviewer actions, including the teaser flag

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P2-WF-02`, `P2-CON-04` | FR-4.3, FR-13.4 |

**Goal:** the Reviewer assesses, edits, sets the teaser flag and forwards or returns each item.

**Scope**

- A Reviewer queue of Under Review items assigned to them.
- The same review page and edit rights as Admin, with the rights declaration at the top.
- For Restricted items, a required teaser choice, Yes or No, with no default (FR-13.4).
- Actions:
    - Forward to Approver
    - Return to Admin or to the original submitter, with required written suggestions

**Security**

- Reviewer only, and only for items assigned to them.
- Forwarding a Restricted item without a teaser choice is refused on the server.

**Acceptance criteria**

- [ ] Forwarding a Restricted item without a teaser choice is refused
- [ ] A return reaches the chosen target with the suggestions shown to them
- [ ] A Reviewer cannot act on an item assigned to another Reviewer

**Tests:** `test_fr_13_4_teaser_choice_required`, `test_fr_4_3_reviewer_return_targets`, `test_p2_wf_03_reviewer_limited_to_assigned_items`.

---

### P2-WF-04 — Build Approver actions: publish, reject and return

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P2-WF-03` | FR-4.4, FR-4.5, D-06, D-07 |

**Goal:** only the Approver can publish, reject or send an item back.

**Scope**

- An Approver queue of Pending Approval items.
- Actions:
    - Approve: the item moves to Approved and is published at once, with `published_at` set
    - Reject: a reason is required, and the item becomes Rejected (D-06)
    - Return to Reviewer: suggestions are required, and the item goes back to Under Review (D-07)
- The Approver may change the teaser flag before approving.
- A published item shows standard attribution: source organisation, date of posting, year of original publication and download count (FR-4.5).

**Security**

- No other login type can reach these actions. Test each.
- Approving twice is safe: the row lock and state check make the second attempt fail cleanly.

**Acceptance criteria**

- [ ] Approve publishes the item with attribution
- [ ] Reject makes the item final and keeps the record
- [ ] Admin and Reviewer attempts to approve are refused and audited

**Tests:** `test_fr_4_4_approver_publishes`, `test_fr_4_4_reject_is_final`, `test_fr_4_4_non_approver_cannot_approve`, `test_fr_4_5_attribution_set_on_publish`.

---

### P2-WF-05 — Add audit entries and in-portal notifications for transitions

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P2-WF-01` | FR-4.6, FR-4.8 |

**Goal:** everyone affected by a workflow step is told in the portal, and the full history is visible.

**Scope**

- A `notification` table: `recipient_login_id`, `event_type`, `subject_type`, `subject_id`, `message`, `channel` (`in_portal` for now), `status`, `created_at` and `read_at`.
- `app.workflow.notifications.notify(db, recipient, event_type, subject, message)`.
- Notify the submitter on return, approval and rejection (FR-4.8), and the next actor when an item reaches their queue.
- A notification bell with an unread count, and a notification list page.
- A workflow history panel on the item review page, built from `workflow_event`.

**Security**

- A login sees only its own notifications.
- Notification text never includes admin-only field values for a Member recipient.

**Acceptance criteria**

- [ ] A return, approval and rejection each create a notification for the submitter
- [ ] The history panel shows every transition with actor and time
- [ ] A Member cannot read another login's notifications

**Tests:** `test_fr_4_8_submitter_notified`, `test_fr_4_6_history_complete`, `test_p2_wf_05_notifications_private`.

---

### P2-WF-06 — Build minor and substantive post-publication edits

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P2-WF-04` | FR-4.9, D-09, [workflow.md](../workflow.md) edits table |

**Goal:** small fixes go live at once with an audit trail, and significant changes need sign-off while the old version stays live.

**Scope**

- `classify_edit(changed_fields)`, returning `minor` or `substantive` from the fixed field lists in `workflow.md`.
- Minor edits by Admin or Reviewer apply directly to the published version, and are audited with old and new values.
- Substantive edits create a working version and run it through Under Review, Pending Approval and Approved. On approval, `published_version_id` switches to the new version. On rejection, the working version is discarded.
- While a working version exists, the published version stays live (D-09), and a second substantive edit is refused.

**Security**

- Members cannot edit published items.
- The switch to the new version and its audit happen in one transaction.

**Acceptance criteria**

- [ ] A summary typo fix applies at once and is audited
- [ ] Changing the file or the access tier creates a working version, and visitors still see the old version until approval
- [ ] After approval, the new version is live and both versions stay in the history

**Tests:** `test_fr_4_9_minor_edit_direct`, `test_fr_4_9_substantive_edit_needs_approval`, `test_d09_published_version_stays_live`, `test_fr_4_9_member_cannot_edit_published`.

---

### P2-END-01 — Add AIDA Endorsed: candidate flag, Approver designation and disclaimer

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev | `P2-WF-04` | FR-9.1, FR-9.2, FR-9.3, Q-08 |

**Goal:** the Approver alone can mark an item AIDA Endorsed, and the disclaimer always appears with the tag.

**Scope**

- A Reviewer toggle "Propose as AIDA Endorsed candidate".
- An "Apply AIDA Endorsed" option in the Approver's approve dialog, highlighted for candidates. The Approver can also publish without it.
- Store `endorsed`, `endorsed_by` and `endorsed_at`.
- A shared template component `endorsed_badge.html` showing the tag and the fixed disclaimer. Every page that shows the tag uses this component.
- Draft disclaimer text for AIDA approval (Q-08): "AIDA Endorsed means this item met AIDA's criteria when the designation was given. It is not a warranty of continued accuracy, a guarantee of outcomes if replicated, or an endorsement of any named vendor."

**Security**

- Only the Approver can set the flag. Test each other role.

**Acceptance criteria**

- [ ] Only the Approver can apply the designation, and it is audited (AC-07)
- [ ] Every place the tag appears also shows the disclaimer

**Tests:** `test_fr_9_1_only_approver_endorses`, `test_fr_9_2_reviewer_flags_candidate`, `test_fr_9_3_disclaimer_with_badge`.

---

### P2-SEC-01 — Human line-by-line review of item visibility and uploads

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev (tech lead or security reviewer) | `P2-CON-06`, `P2-UPL-03`, `P2-WF-01` | [security.md](../security.md), R-04 |

**Goal:** a second person checks the code that decides who sees Restricted content, and the code that accepts files.

**Scope**

Review `app/content/visibility.py`, `app/content/uploads.py`, `app/content/formats.py`, the scan task and `app/workflow/service.py` against this checklist:

- [ ] No query lists or counts items without `visible_items()`
- [ ] Missing tiers default to Restricted
- [ ] Tusd hooks check the session, role and draft ownership, and cannot be reached from outside
- [ ] Size and format limits are enforced on the server
- [ ] Files cannot be opened before a clean scan
- [ ] Temporary files are always removed
- [ ] Only `apply_action()` changes state
- [ ] Admin-only fields are absent from non-admin schemas

**Security**

- Record findings as `DEF-###` defects. S1 and S2 findings are fixed before Phase 3 ends.

**Acceptance criteria**

- [ ] The completed checklist and findings are attached to the review pull request
- [ ] No S1 or S2 finding remains open

**Tests:** add a regression test for every defect found.

---

### P2-QA-01 — Test 1 GB resume, 21 MB image refusal and infected file

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | QA | `P2-UPL-01` to `P2-UPL-03` | AC-10, AC-11, AC-12 |

**Goal:** end-to-end proof of upload limits, resumption and scanning on staging.

**Scope**

- Upload a 1 GB MP4, cut the network mid-way, restore it and confirm it resumes (AC-11).
- Try a 21 MB JPG and confirm refusal before upload with the 20 MB message (AC-10).
- Upload the EICAR file and confirm quarantine and notification (AC-12).
- Upload a PDF renamed to `.docx` and confirm it is rejected.

**Security**

- Call tusd directly, without the browser, with an oversized length and without a session.

**Acceptance criteria**

- [ ] AC-10, AC-11 and AC-12 pass on staging

**Tests:** `tests/e2e/test_uploads.py`.

---

### P2-QA-02 — Test every workflow path and refused action

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 5 | QA | `P2-WF-01` to `P2-WF-06`, `P2-END-01` | AC-05, AC-06, AC-07, AC-09 |

**Goal:** end-to-end proof that the governance workflow works and cannot be bypassed.

**Scope**

- Every row of the transitions table, run through the user interface (AC-05).
- Reject, and confirm the record is kept (AC-06).
- Admin and Reviewer trying to approve or endorse, by button and by direct request (AC-07).
- Minor and substantive edits, including the published version staying live.
- Check the audit log for every action taken (AC-09).

**Security**

- Replay a captured approve request as a Reviewer, and confirm it is refused.

**Acceptance criteria**

- [ ] AC-05, AC-06, AC-07 and AC-09 pass on staging

**Tests:** `tests/e2e/test_workflow.py`.

---

### P2-QA-03 — Test admin-only fields and the rights declaration

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | QA | `P2-CON-02`, `P2-CON-04` | AC-18, FR-3.3, FR-3.9 |

**Goal:** proof that admin-only data never reaches a Member or visitor.

**Scope**

- Create an item with distinctive values in every admin-only field, such as `FG-SENTINEL-123`.
- Open every Member page that shows the item, including listings, the item page and notifications, and search the HTML source for each sentinel value (AC-18).
- Confirm the rights declaration appears for the Reviewer and nowhere for Members.

**Security**

- Include HTMX partial responses and any JSON responses in the scan.

**Acceptance criteria**

- [ ] AC-18 passes for Member views, and is re-run for public views in `P3-QA-02`

**Tests:** `tests/e2e/test_admin_only_fields.py`.

---

### P2-QA-04 — Verify bulk import against the template

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | QA | `P2-CON-07` | SRS 6.2 |

**Goal:** ITPED's bulk import works with realistic data.

**Scope**

- Import a sheet of 20 realistic rows with files, including one row with errors.
- Confirm the errors are reported by row, the valid rows import as Submitted, and the files are scanned.

**Security**

- Try a ZIP with a `../` path, and confirm it is refused.

**Acceptance criteria**

- [ ] The import matches the template, and errors are clear enough for ITPED staff to fix

**Tests:** `tests/e2e/test_bulk_import.py`.
