# Fallback current-version document sections

Use this asset only when the project has no usable document convention. Rename files and headings to match the project's language and vocabulary. Do not create empty optional sections.

## Active PRD

```markdown
---
version: "[confirmed project version name]"
status: "draft"
candidate_state: "active_candidate"
source_lineage: "[current approved version]"
governance_cycle_id: "[stable cycle identifier]"
validation_status: "pending"
acceptance_status: "pending"
version_approval_status: "pending"
archive_status: "pending or not-applicable"
authority_owner: "[name or role]"
authority_scope: "[product scope]"
approved_at: "[date or pending]"
approval_evidence: "[decision reference or pending]"
approved_content_digest: "[digest or pending]"
supersedes: "[prior approved version]"
---

# [Project] Product Requirements

## Scope

- Included: [scope]
- Excluded: [scope]

## Requirements

| ID | Testable requirement | Acceptance evidence | Source or decision | Status |
|---|---|---|---|---|
| REQ-001 | [behavior] | [test or observation] | [source] | active |

## Material decisions

| ID | Decision | Owner / scope | Date | Source / approval evidence | Supersedes | Follow-through |
|---|---|---|---|---|---|---|
| DEC-001 | [decision] | [owner / scope] | [date] | [source / evidence] | [prior behavior] | [code/test impact] |

## Unresolved requirement conflicts

| ID | Sources | Impact | Options | Authority needed | Status |
|---|---|---|---|---|---|
| CF-001 | [sources] | [impact] | [options] | [owner] | unresolved |
```

Keep PRD status `draft` until an authorized owner explicitly approves this exact content and its approval evidence is recorded; only then change PRD status to `approved`. Record the approval content digest when practical so later edits cannot inherit stale approval. PRD approval does not change `candidate_state`; keep the version as `active_candidate` and validation as `pending` or `failed` until code checks pass. Independent acceptance changes only `acceptance_status`. Change `version_approval_status` and current authority only after separate authorized version approval; archive predecessors afterward and record `archive_status` independently. Filled placeholders, absence of conflict, completed code, or acceptance do not imply version approval. Do not implement behavior governed by an unresolved conflict.

An authorization statement never waives missing prerequisites. Before changing `version_approval_status` or `current_approved`, require `validate_project_state.py --gate version-approval` to pass. Before moving predecessors, require `--gate archive`. Keep the exact validator output or evidence reference with the governance handoff.

## Active unresolved-issue list

Create this only when unresolved issues exist or the project already requires the file.

```markdown
# [Project] Open Issues — [confirmed project version name]

## ISSUE-001 — [short title]

- Status: open
- Severity / impact: [value]
- Related requirement: [ID or none]
- Evidence or reproduction: [steps/log/reference]
- Acceptance condition: [observable result]
- Carried from: [prior version or newly found]
```

Do not copy resolved-and-verified items into the active list. Preserve their history in the prior archived version, Git, or the user's issue system.
