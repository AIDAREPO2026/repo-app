# Content governance workflow

Every content item, expert profile and Gallery listing follows one pipeline: Admin, then Reviewer, then Approver. All state changes go through `app.workflow.service.apply_action()`. That function writes a `workflow_event` and an audit event in the same transaction (FR-4.6, FR-12.1).

## States

| State | Meaning | Who holds it |
| --- | --- | --- |
| Draft | Being prepared, not yet submitted | The creator (Member or Admin) |
| Submitted | Received, waiting for Admin | Admin |
| Under Review | Being assessed | Reviewer (primary, or alternate on recusal) |
| Pending Approval | Waiting for the final decision | Approver |
| Returned | Sent back for correction | The submitter (Member), or Admin for ITPED-sourced items |
| Rejected | Final. The record is kept (D-06) | Nobody |
| Approved | Signed off. The System publishes it at once | System |
| Published | Live, according to its access tier | Admin, Reviewer and Approver for edits |
| Retired | Withdrawn from discovery, history kept (Phase 5, D-08) | Nobody |

A discarded Draft is marked with `discarded_at` and never hard-deleted (SRS 6.3).

## Transitions

| From | Action | To | Who | Conditions | Side effects |
| --- | --- | --- | --- | --- | --- |
| Draft | `submit` | Submitted | Member (own Discom's item) or Admin | All required fields are complete, the rights declaration is made (FR-3.9), and every file is scanned clean | Admin queue notified |
| Draft | `discard` | Draft, with `discarded_at` set | Creator | None | None |
| Submitted | `forward` | Under Review | Admin | A Reviewer is assigned | Reviewer notified |
| Submitted | `return` | Returned | Admin | A written reason is given | Submitter notified (FR-4.8) |
| Under Review | `forward` | Pending Approval | Reviewer | Teaser flag set for Restricted items (FR-13.4). Gallery: no-financial-interest declaration recorded (FR-7.7) | Approver notified |
| Under Review | `return` | Returned | Reviewer | Written suggestions given, and the return target chosen: Admin or the original submitter (FR-4.3) | Return target notified |
| Pending Approval | `approve` | Approved, then Published | Approver | Gallery: declaration recorded and fee terms confirmed (FR-7.3, FR-7.7). Optionally apply AIDA Endorsed (FR-9) | `published_at` set to the date of posting. Submitter notified |
| Pending Approval | `reject` | Rejected | Approver | A written reason is given | Submitter notified |
| Pending Approval | `return` | Under Review | Approver | Written suggestions given (D-07) | Reviewer notified |
| Returned | `resubmit` | Submitted | The holder of the Returned item | Same conditions as `submit` | Admin notified |
| Published | `minor_edit` | Published | Admin or Reviewer | Only the minor fields listed below change | Audit records old and new values |
| Published | `start_substantive_edit` | Published, with a working version Under Review | Admin or Reviewer | Any substantive field changes | Reviewer notified. The published version stays live (D-09) |
| Published | `retire` | Retired | Admin or Approver | Phase 5 | Hidden from discovery |

A working version (substantive edit) then follows Under Review, Pending Approval and Approved. On approval it becomes the published version. If it is rejected, it is discarded, and the published version stays.

## Minor and substantive edits (FR-4.9)

| Minor: applied directly and audited | Substantive: needs Reviewer and Approver sign-off |
| --- | --- |
| Title wording (typo fix) | Replacing the file |
| Summary | Changing the Category (module) |
| Original source text and year of publication | Changing the Subcategory |
| Functional group | Changing the access tier |
| Jurisdiction | Changing the external URL |
| Public teaser flag (FR-13.4) | |

Source Organisation is never changed by Admin or Reviewer. Their edits are custodial, and the item stays attributed to its submitter (FR-2.4).

## Permissions summary

| Login type | Can do |
| --- | --- |
| Member | Create drafts and submit for its own Discom. See its own submissions' states. Resubmit Returned items. Cannot edit after approval |
| Admin | Everything on content and tags before approval. Create ITPED-sourced items. Forward to Reviewer. Return. Make minor and substantive edits. Cannot approve, reject or apply AIDA Endorsed |
| Reviewer | Same edit rights as Admin while an item is Under Review. Set the teaser flag. Flag an AIDA Endorsed candidate. Forward or return. Cannot approve |
| Approver | Approve (with or without AIDA Endorsed), reject or return. Change the teaser flag. Countersign review dates (Phase 5). The only role that can publish |

## Subject types

`apply_action()` handles three subject types with the same transition table:

| Subject type | Table | Created by | Extra conditions |
| --- | --- | --- | --- |
| `content` | `content_item` | Member or Admin | Rights declaration, clean files, teaser flag |
| `expert` | `expert_profile` | Admin only, on the expert's behalf | Consent declaration recorded (FR-8.2) |
| `gallery` | `tech_listing` | Admin only, on the provider's behalf | No-financial-interest declarations, and fee terms confirmed (FR-7.3, FR-7.7) |

## Recusal (Phase 5, FR-2.9)

When an item is forwarded and the primary Reviewer belongs to the item's submitting Discom, the System assigns the alternate Reviewer and records the recusal in the audit log.
