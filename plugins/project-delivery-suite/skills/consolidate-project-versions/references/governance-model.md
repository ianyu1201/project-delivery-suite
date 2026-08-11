# Project-version governance model

## Contents

1. Naming and lifecycle
2. Minimal active surface
3. Authority and conflicts
4. Complete candidate contract
5. Requirements, code, and issues
6. Regenerable and sensitive data
7. Numbered lifecycle archive and storage
8. Optional remote recovery
9. Closure matrix

## 1. Naming and lifecycle

Treat names as project data. Inventory folder names, filenames, version metadata, tags, language, and chronology before generating anything. Common patterns such as `V1/V2/V3` are examples, never defaults. Do not guess semantic-version bump type or lexical-sort names such as `V9` and `V10` without supporting evidence.

Resolve five distinct roots before writes: `workspace_root`, `active_version_root`, `archive_root`, `repo_root`, and `staging_root`. Classify the project as `complete-snapshot`, `numbered-lifecycle`, or project-defined. A release-document folder is not a complete project version.

Keep these states separate:

| State | Meaning | Naming consequence |
|---|---|---|
| Latest observed | Highest-looking artifact found | No authority by itself |
| Current approved | Newest version with valid approval evidence | Source of the next governance cycle |
| Active candidate | Existing unapproved version under repair | Continue its name; do not increment for retries |
| Historical approved | Prior approved state | Evidence only |
| Draft/unknown | Unapproved or unclear source | Never implementation authority |

When a rule is ambiguous, ask one focused question containing observed names and the proposed next name. Reuse existing names for PRD, issues, source, tests, and archives.

Persist the active candidate's source lineage, governance-cycle identity, candidate state, and latest validation state in existing version metadata or the candidate PRD. Do not create a second governance document for these markers. A failed staging directory is only recovery material until deliberately adopted as the active candidate. If naming and authority are both unknown, ask separate focused questions rather than silently coupling the answers.

## 2. Minimal active surface

The next complete version normally needs:

- one active PRD;
- one active unresolved-issue list only when needed or already conventional;
- complete reproducible source, tests, configuration, migrations, lockfiles, and required assets.

Do not create separate baseline, decision, conflict, provenance, traceability, validation, archive-index, or AI-context documents by default. Store compact decisions, sources, and acceptance evidence in the PRD. “One PRD” means one product authority, not that source, tests, and issues belong inside one file.

Reuse an existing AI instruction entrypoint to identify the active PRD and make archives non-authoritative. If none exists and archive exclusion cannot be enforced, report the limitation instead of claiming drift prevention.

## 3. Authority and conflicts

Higher-level instructions, repository policy, security requirements, law, and retention controls cannot be overridden by project content.

Within authorized product scope, use:

1. recorded decision by the current authorized owner;
2. approved change record;
3. newest approved PRD;
4. active candidate or draft evidence;
5. historical evidence.

A material decision records owner/approver, authority scope, approval evidence, affected requirement or issue, chosen and superseded behavior, and source/date when available. Unknown authority remains unresolved. Require explicit decisions for behavior, scope, interfaces, data, security, privacy, compliance, destructive behavior, compatibility, and acceptance criteria. Omission is not deletion.

First present the exact candidate PRD as a read-only proposal. After authorized document write scope exists, store it only in the active candidate or the staging directory intended to become that candidate. An authorized owner must approve that exact PRD content before changed product behavior is implemented. This approves product scope only; the version remains an active candidate until code validation and final version approval pass.

## 4. Complete candidate contract

A candidate is safe to materialize only when:

- the approved source lineage and target name are known;
- the destination is absent, inside the confirmed project scope, outside the source, and not a symlink, root, home, archive root, or mount point;
- source Git state and a pre-copy manifest exist;
- nested repository, submodule, LFS, symlink, permission, hidden-file, ignored/untracked, non-Git, secret, and runtime-data handling is explicit;
- exclusions are individually classified rather than inferred from a directory name;
- a sibling staging directory is used and the approved source remains unchanged;
- destination paths, hashes, modes, symlinks, exclusions, and separately retained data match before promotion;
- the final destination is rechecked as absent immediately before atomic promotion.
- the exact approved candidate PRD and its approval evidence are written into the candidate without substituting a later draft.

Never represent a branch, patch, partial tree, failed copy, or destination merged with prior content as a complete new version. Do not duplicate nested `.git` directories by default; decide repository topology explicitly.

When a `project-delivery-orchestrator` flow owns lifecycle coordination, return control after safe materialization. The handoff includes all five roots, topology, current/candidate identities, source lineage, governance-cycle identity, PRD status, and validation plan. The orchestrator owns development chats and independent acceptance; this Skill resumes for conformance reconciliation, version approval state, and archival. A direct invocation may implement authorized gaps, but two coordinators must never write the candidate concurrently.

## 5. Requirements, code, and issues

Validate both directions internally:

- every active requirement maps to implementation and acceptance evidence;
- every material code behavior and test maps to an active requirement, defect, or justified technical constraint.

Use this gap check as working evidence rather than generating a permanent traceability document by default.

| Issue status | Next-version treatment |
|---|---|
| Resolved and verified | Omit from active list; retain in historical evidence |
| Changed but unverified | Carry forward |
| Open, deferred, reopened | Carry forward with stable ID and acceptance condition |
| Duplicate, invalid, superseded | Omit only after disposition is recorded |

An issue changing intended behavior must update the PRD. Implementation defects stay in the issue list. Validate fixes one independently verifiable item at a time when practical, but do not create a second task system merely for this Skill.

Before executing project commands, inspect scripts and environment. Default to candidate-local lint, typecheck, tests, and builds with minimum privileges. External APIs, networked tests, shared services, and publication require separate authorization. This Skill never deploys, applies migrations, seeds/resets, changes infrastructure, or accesses shared/production databases. Use static/dry-run checks or an explicitly disposable local environment; route real delivery operations to a separate workflow.

## 6. Regenerable and sensitive data

Classify content by evidence:

| Class | Candidate | Historical treatment |
|---|---|---|
| Source, tests, config, migrations | Include | Retain |
| Lockfiles and toolchain constraints | Include | Retain |
| Installed dependencies/virtual environments | Rehydrate only as needed | Do not copy by default |
| Tool-supported shared cache/store | Reuse when safe | Do not version |
| Logs, coverage, temporary output | Do not copy | Removal candidate after verification |
| Build/release output | Decide from reproducibility and operational need | Retain only with reason |
| Secrets | Never copy or publish by default | Handle through the project's secret system |
| Databases, uploads, user/runtime data | Separately protected handling | Never assume Git recovery |
| Unknown content | Preserve until classified | Ineligible for removal |

Do not force a universal dependency directory. Module resolution, native binaries, lockfiles, toolchains, and build flags can invalidate sharing. Report verified generated subdirectories separately so the user can make a manual cleanup decision without discarding an entire historical version containing unique data. The Skill does not perform the cleanup.

A default exclusion such as `node_modules` is a discovery hint, not proof of regenerability. Confirm dependency declarations, lockfiles, toolchain constraints, project scripts, and any unique files through an included scan or separate project-specific evidence before treating the subtree as a storage candidate.

## 7. Numbered lifecycle archive and storage

An archive directory changes authority and organization, not disk usage. Verify manifests and relative/path-dependent links after any authorized move. Reuse existing archive naming. With no project convention, propose the project's language equivalent of `90_历史归档`; the `90_` prefix means last-in-reading-order and non-authoritative history, not a forced universal spelling.

Complete predecessor archival is part of a successful governance cycle. Include the exact source and archive destination of every predecessor version in the authorized write proposal. Only after the new candidate becomes the approved current version, move every predecessor in the governed series into the archive. Thus, when V4 replaces V3, V1, V2, and V3 all become archived, non-authoritative history and only V4 remains active outside the archive. Preserve original version names and verify each move. An unclassified, unauthorized, failed, or incomplete move keeps the state `archive pending`; never archive predecessors early while the candidate is still draft or unapproved.

In `complete-snapshot` topology, one complete current version remains active outside the archive and all predecessors live beneath the archive root. In `numbered-lifecycle` topology, materialize the complete candidate as an isolated worktree/staging from the approved Git baseline rather than a second permanent active source tree; after approval, use the project's authorized Git integration policy to establish the single active code path in the engineering area. Keep current PRD/design material in their numbered lifecycle areas; move superseded version material beneath `90_历史归档/<version>`; and retain historical code through verified Git fixed points or explicitly approved complete snapshots. A branch or worktree alone is never approval or completeness evidence.

The Skill may report logical and allocated estimates, generated-data paths, and recovery limitations. It never moves content to Trash and never deletes. A user who wants space back manually removes selected archived content outside this Skill after considering recovery evidence.

## 8. Optional remote recovery

Remote recovery is optional for governance and important when local history is reduced or device-loss protection matters. Detect repository state, remote configuration, and authentication separately. Missing GitHub CLI is not proof of no account.

Offer a destination once and accept a decline. Never auto-create, publish, commit, tag, upload, or push. Before treating a remote as recoverable:

- record a source manifest and exclusion policy;
- inspect secrets and unsuitable large data across the complete outgoing Git object graph, including all refs, tags, branches, and retained history—not only the working tree;
- account for tracked, untracked, ignored, symlink, LFS, submodule, and non-Git content;
- restore every retained version into a fresh location;
- compare it under the same policy;
- preserve hosted Issues separately because ordinary Git history does not contain them.

## 9. Closure matrix

| Area | Closed when |
|---|---|
| Discovery | Scope, chronology, names, current approved version, and candidate state are known or explicitly decided |
| PRD | Exactly one active PRD is approved by an authorized owner with evidence; material conflicts are resolved |
| Issues | Every prior issue is verified-closed, carried forward, or dispositioned with evidence |
| Candidate | A non-overwriting staged copy matches its manifest and contains all required reproducible inputs |
| Code | Requirement and reverse-scope checks pass; applicable safe commands pass |
| Archive | Every predecessor version in the governed series is non-authoritative, moved to the authorized archive, and verified with exact move and link checks |
| Anti-drift | Existing AI entrypoint routes to current PRD, or limitation is reported |
| Remote | User declined with known risk, or fresh recovery matches manifests |
| Storage | Regenerable, sensitive, unknown, and archived content are classified without deletion or reclaimed-space claims |

Incomplete scans, unsupported capabilities, ambiguous names, draft PRDs, unresolved authority, partial folders, unsafe command targets, failed checks, and pending recovery remain incomplete.
