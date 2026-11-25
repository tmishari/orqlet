# Security review of the rust-migration design, round 6 (allowed by the person)

Reviewer: orqlet-security-reviewer subagent (17946105-bc27-437f-ad07-41982030b83e), fresh context, model named by the client as Claude Opus 5.5.
Earlier rounds: `security-reviewer-design-r2.md` to `-r5.md`. The person allowed this sixth round on 2026-11-25, after round 5.
Design file hashes of this round, given to the reviewer in its prompt:

```
docs/design/rust-migration/design/adr-001-crate-per-layer.md#c15657e6d7c37ecf163410b0db8696b3fb65f3fa0df698135469dcbd236d9d73
docs/design/rust-migration/design/adr-002-rewrite-beside-python.md#47e64f08204cfddc55b74aa0334579905e23483e81954b2cde6ece037c9cd739
docs/design/rust-migration/design/adr-003-libraries.md#dee7f39333085019352b841807ef36965288fee5be36607971d33e9f2678df82
docs/design/rust-migration/design/adr-004-version-and-hashes.md#ea987d465d01ff0381a308ff3471a4a9aeceff1d35fab12fc0c9f66790e2ac9a
docs/design/rust-migration/design/adr-005-schemas-and-xtask.md#54835d937a3ef93f34ca9411d6b1d9da377cee3a9c918f4a639b98248c2e9c69
docs/design/rust-migration/design/adr-006-standards-profile-documents.md#e3bd59b65704ae83e8b88157f9fbca0603eb35ec72f9aa236dec6017029ed9a1
docs/design/rust-migration/design/adr-007-security-controls.md#579a7817dff921263f1f1ffe26e88bacd0b154de18616c783b661d3cad272199
docs/design/rust-migration/design/component.md#ab6b685f0519e101b0e152fa7acb706ef8a2582509d46c9db6005340d0a4f938
docs/design/rust-migration/design/manifest.yaml#60dbabbf2998e5e732c143223ebee92f7fc0a540990f99b50067f3726ddec6f6
docs/design/rust-migration/design/views.md#10359fef0c04cf3bf73b54d766eeda1f14b010dae86e11428cf1a80e7a6182e6
```

## Reviewer output (unchanged)

# Round-6 security review of the rust-migration design

The review found no blocking problems, one major finding and three minor ones. All five round-5 security findings are resolved.

**Hash comparison: not run.** This session refused the shell, so I could not hash the files, confirm the branch or HEAD, or run `orqlet standards for`. As a substitute, I compared the ten values you gave with `manifest.yaml`:
- The nine artifact hashes are the same as the values the manifest records for D-1 to D-5 and ADR-001 to ADR-007, at lines 117–128.
- `views.md` has the same hash as in round 5, so it did not change this round.
- Nothing records a hash for the manifest itself, so its value `60dbabbf…` was not checked.

This does not prove the file bytes match. For the standards, I used the rule texts in `.cursor/rules/` instead (SEC-001, SEC-002, SAFE-001, ARCH-001, ARCH-002, MODEL-001, MODEL-002).

**The major finding.** 0.5.2 has two filters for text that a repository controls before that text reaches the terminal or an IDE agent. The design does not carry either one over, and neither does the approved AS-IS file:
- `printable()` turns text into escaped ASCII and limits its length.
- `representable_path` and `representable_version` let a value through unchanged or drop it completely.

The hook puts `workflow_version` from `.orqlet/workflow.lock` (a file in the repository) and edited file names into an agent's context. Without these filters, a hostile repository could inject text there.

**The minor findings:**
- What counts as the "main work tree" is not defined for every Git layout.
- The failures table, view D-5 and the acceptance criteria miss the new Q-18 and Q-19 outcomes and the ORQ-E106 case.
- When the project id is refused, the message may still quote the id from the profile.

## Findings (orqlet.finding/v1)

```yaml
findings:
  - id: SEC-D6-1
    severity: major
    location: adr-007 (no decision); adr-007 decision 8 (line 16) and decision 12 (line 36); manifest EC-6 (line 115); component BC-21 (line 83); manifest security_globs (lines 44-67)
    evidence: >
      src/orqlet/domain/representable.py lines 1-5: "What may reach an agent's context from a file
      or a path: shown as it is, or not at all." Lines 17-34: the hidden categories Cc, Cf, Cs, Co,
      Cn, Zl, Zp plus a list of invisible ranges. Lines 45-62: representable_version accepts only an
      ASCII major.minor.patch value; representable_path accepts at most 200 characters with no
      hidden character.
      src/orqlet/application/usecases/hook_event.py lines 110-121: the session-start
      additionalContext is a template filled with representable_version(report.project). The
      project version comes from .orqlet/workflow.lock (status.py line 221), which the repository
      controls. hook_event.py lines 161-166: the post-edit additionalContext holds
      representable_path of a repository file name. status.py line 174 does the same for the work
      tree path.
      src/orqlet/domain/conventions.py lines 100-111: printable() escapes every non-ASCII or control
      character, doubles backslashes and cuts the text at limit+3. Callers show repository-
      controlled text with it: commit subjects and branch names (conventions_check.py lines 181,
      195), evidence paths (validate_as_is.py line 155, evidence_cite.py line 160), model-policy
      reasons (validate_model_policy.py lines 218, 268, 379), and resource and integration paths
      (validate_resources.py lines 52, 71, 157, 160; validate_integrations.py lines 92, 110;
      resources_view.py lines 76, 103).
      A search of docs/design/rust-migration/design/ and as-is.md for "representable",
      "printable(", "additionalContext" and "commit subject" finds nothing.
      adr-007 line 6: "A port that lists fewer rules would weaken a control without anyone noticing."
    finding: >
      Two 0.5.2 output controls are missing from ADR-007, the acceptance criteria and EC-6:
      - the all-or-nothing filter on what reaches an agent's context;
      - the ASCII escaping of repository-controlled text in findings.
      Decision 8 and EC-6 say that no message quotes an input value. But the post-edit hook must
      show a path by design, and the convention checks show commit subjects and branch names. So
      the rule either removes those features without saying so, or a port quotes the text with no
      stated rule. In the second case, a hostile workflow_version (for example a version followed
      by a newline and instructions) or a file name with bidirectional or zero-width characters
      reaches an IDE agent's context or the terminal unfiltered.
      The domain modules that would hold these filters are not in security_globs either.
    needed: >
      Add an ADR-007 decision that carries over both rules with their source lines:
      - representable_version and representable_path, with every hidden category and range listed,
        for everything that reaches hook output or status;
      - printable(), with ASCII escaping, backslash doubling and the limit+3 cut, for every
        repository-controlled value shown in a finding.
      Then:
      - Reword decision 8 and EC-6 so they say which values may be shown and through which filter.
      - Add acceptance cases: a workflow.lock version with a newline or extra text gives no
        additionalContext; a file name with a bidirectional mark is not shown; a commit subject
        with control characters is shown escaped.
      - Place the filters in named modules (for example crates/orqlet-domain/src/representable.rs
        and conventions.rs) and add those paths to security_globs.
      - Confirm that the Unicode category crate of decision 14 also gives Co, Cn, Zl and Zp.

  - id: SEC-D6-2
    severity: minor
    location: adr-007 decision 10 (line 18); BC-19 (component line 81)
    evidence: >
      adr-007 line 18 compares with "for a linked worktree, the main work tree, the folder that holds
      the common Git folder".
      src/orqlet/application/ports/vcs.py lines 102-105: "linked" means only that git_dir differs
      from common_dir.
      src/orqlet/adapters/git/vcs_git.py lines 68-83: common_dir is the real path that Git prints
      for --git-common-dir.
    finding: >
      "The folder that holds the common Git folder" is the main work tree only when the common
      folder is <work tree>/.git. In two layouts it is not:
      - A bare repository with linked worktrees: the parent of the bare folder can be a broad
        folder. If it is the home folder, it contains the default data directory, and every
        writing command refuses with ORQ-E105. This fails closed, but it stops Orqlet working.
      - A separated or configured work tree (core.worktree, --separate-git-dir): the real main
        work tree is never compared.
      A `.git` file that a repository archive ships also decides where the common folder is. A
      hostile tree can therefore cause these refusals; this affects availability only.
    needed: >
      Define the main work tree exactly. Either take the parent of the common folder only when the
      common folder is named `.git` and the repository is not bare, and otherwise skip that
      comparison and record the gap; or state the over-refusal for bare repositories as accepted.
      Add a BC-19 case for a linked worktree whose data directory lies in the main work tree.

  - id: SEC-D6-3
    severity: minor
    location: component §5 failures table (line 54); views D-5 (line 62); BC-19 (line 81); BC-22 (line 84); adr-007 Consequences (line 42)
    evidence: >
      adr-007 lines 19-22: writing commands refuse with ORQ-E105, or ORQ-E106 when the Vcs call
      fails. doctor, sync and explain "report ... as a finding, do not create the data directory,
      treat its data as missing, and go on" (Q-18). The hook prints {} (Q-19).
      component line 54 lists only ORQ-E105 for writing commands and has no Git-failure row.
      views line 62 shows only "refuse, ORQ-E105". BC-19 checks only that the directory is
      refused. No criterion covers the doctor, sync and explain behaviour, the hook {} case or the
      main-work-tree comparison.
      adr-007 line 42: "Each rule above has a criterion in the brief".
    finding: >
      Q-18 and Q-19 decide outcomes that matter for security, but no acceptance criterion tests
      them. In particular, doctor and sync must not read journals planted in a data directory
      inside the repository. An implementation that creates the folder, or reads its journals, in
      the report-and-go-on path would still pass BC-19 and BC-22. The failures table and view D-5
      also leave out ORQ-E106.
    needed: >
      Add acceptance cases:
      - doctor, sync and explain with a data directory inside the repository report ORQ-E105, do
        not create the directory and report no ORQ-E170 from a journal planted there;
      - the same commands with a failing Vcs call report ORQ-E106;
      - the hook prints {} when the data directory lies inside the project root it finds;
      - the main-work-tree case.
      Add ORQ-E106 to the failures table and to view D-5.

  - id: SEC-D6-4
    severity: minor
    location: adr-007 decision 10, project id paragraph (line 24); decision 8 (line 16)
    evidence: >
      adr-007 line 24: an id that is not a UUID "is refused as a journal error, ORQ-E136, as
      journal.py lines 30-34 refuse an id that is not a path".
      src/orqlet/adapters/fs/journal.py line 34: the 0.5.2 message is
      f"not a usable project id: {project_id!r}", which quotes the id.
      src/orqlet/application/contracts/profile.py line 48: project.uuid is a free string in the
      repository's profile, so the repository controls it.
      errors.py line 19 and runner.py line 33: the message is printed as it is.
    finding: >
      The decision points to 0.5.2's refusal as its model, and that refusal quotes a value that the
      repository controls. Decision 8 says refusals report only the rule, but the project-id
      refusal is not named among the "New" message changes, and no criterion checks that the
      message leaves the id out.
    needed: >
      State that the ORQ-E136 message for a bad project id names the source (the profile or
      --project-id) and leaves out the value. List this as new and add it to BC-19 or BC-21.
```

## Round-5 security findings

| Round-5 finding | Status | What remains |
|---|---|---|
| SEC-D5-1: data-directory comparison and Git failure | **Resolved.** Decision 10 (line 18) now compares with the real project root, the Git top level and the main work tree. A Vcs error other than "not a repository" is never read as "no repository", and writing commands then refuse with ORQ-E106 (line 19). BC-19 has the Git-failure case. The cited `vcs_git.py` lines 66-84 are accurate. | Definition of the main work tree: SEC-D6-2. Missing criteria and table rows: SEC-D6-3. |
| SEC-D5-2: unknown journal format or status | **Resolved.** Decision 11 (line 27): any format other than none or `orqlet-journal/1`, and any status outside the four known values, makes the record unreadable (ORQ-E136). Every path that reads the folder reads format and status first and never rewrites a 0.x record: the upgrade guard, supersede, doctor and sync, resume and rollback. BC-22 and ADR-004 decision 5 agree. The cited `apply_plan.py` lines 55-56 and `diagnose.py` lines 398-409 are accurate. | — |
| SEC-D5-3: `rollback --project-id` | **Resolved.** Line 24 applies the UUID rule and the confined join to every source of the project id, the option included, and BC-19 names it. The cited `lifecycle.py` lines 133-135 and `rollback.py` line 49 are accurate. | Quoting in the refusal message: SEC-D6-4. |
| SEC-D5-4: Git error output in messages | **Resolved as Q-20 decided.** Decision 8: ORQ-E106 gives a fixed message with only the subcommand and the exit status (new). EC-6 and BC-21 agree. The cited `git_runner.py` lines 132-136 and `vcs_git.py` lines 48-51 are accurate. | — |
| SEC-D5-5: security globs | **Resolved.** The globs now cover `crates/orqlet-cli/src/**` and the upgrade, apply_plan, rollback and diagnose use cases. | The filter modules of SEC-D6-1 are not in the globs. |

## Observations (none blocking)

- **Change ids are not held to the UUID rule.** The `rollback <change_id>` argument is joined through `CanonicalPath.child`, which allows a `/` inside the name but refuses `..` (`paths.py` lines 30-34 and 80-81), so the path stays inside the data directory. The ORQ-E131 and ORQ-E170 advice puts a `change_id` read from the journal's contents into a suggested command (`upgrade.py` lines 84-86, `diagnose.py` lines 402-405). Since Q-16, the journal folder is Orqlet's own, so the risk is low.
- **Checking `projects/<id>/` needs the profile id first.** That folder could only lie inside the repository through a link below the data directory, and decision 9's confined file system already refuses links. I found no gap.
- **The hook only compares with the `.orqlet/` root it finds** (Q-19). A data directory inside the Git work tree but outside that root is not detected by the hook. The person chose this, and the risk is low (round-5 observation).
- **Unicode versions can differ.** The `Cn` (unassigned) category depends on the Unicode version. Python's `unicodedata` and a Rust crate can disagree, which would change filtering results between 0.5.2 and 1.0.0. This matters if SEC-D6-1 is applied.
- **Changes that help security, confirmed:** an empty `ORQLET_DATA_DIR` is treated as unset (`wiring.py` line 86, accurate); temporary-name retries stop at 100; the Git error output is gone from messages; data-directory files are 0600 and folders 0700; read-only commands with a bad data directory go on without creating it or reading its data.
- In the files I read I found no secrets, no MD5 or SHA-1 for integrity, and no language-model SDK.

## Self-check

```yaml
schema: orqlet.self-check/v1
checked_against:
  role: security-reviewer
  phase: design
  round: 6
  model: "Claude Opus 5.5 (as named by the client); fresh context, no Architect conversation"
  revision: "working tree of /Users/tmishari/Documents/orqlet; branch and HEAD not confirmed (shell refused); source assumed equal to 3e3c311"
checks:
  - {what: SHA-256 of the ten design files, how: "shasum with CRLF read as LF", result: "NOT_RUN (shell refused)"}
  - {what: given hashes vs manifest artifact hashes, how: "read manifest.yaml lines 117-128", result: "equal for all nine artifact values; views.md unchanged since round 5; the manifest's own hash is not recorded, not checked"}
  - {what: orqlet standards for, how: shell, result: "NOT_RUN; read the rendered SEC-001, SEC-002, SAFE-001, ARCH-001, ARCH-002, MODEL-001 and MODEL-002 rule files instead"}
  - {what: "manifest, component.md, views.md, adr-007 in full; ledger Q-16 to Q-20; security-reviewer-design-r5.md; parts of architecture-reviewer-design-r5.md", how: read, result: done}
  - {what: round-5 SEC-D5 resolutions, how: "compared each 'needed' and the person's decision with the round-6 text", result: "5 resolved; residuals in SEC-D6-2, -3 and -4"}
  - {what: citations new this round, how: "read vcs_git.py 25-100, vcs.py 85-124, wiring.py (whole), lifecycle.py 120-310, rollback.py 35-124, journal.py (whole), hook_event.py 80-237, status.py 35-49 and 215-234, apply_plan.py 40-69, diagnose.py 390-410, upgrade.py 75-94, git_runner.py 118-137, errors.py (search)", result: "accurate"}
  - {what: output filtering of repository-controlled text, how: "searched src/orqlet for printable( and representable_*; read representable.py, conventions.py 80-119, conventions_check.py 180-198; searched the design and as-is.md", result: "control missing from the design: SEC-D6-1"}
unverified:
  - "adr-001 to adr-006 were checked only for the uuid, journal and new-rule text, not reread in full; evidence/web files and as-is.md were only searched."
  - "Earlier review notes r2 to r4 were not reread."
  - "Library and platform behaviour (Git bare and worktree layouts, the Unicode crate's categories) was not looked up, by rule."
  - "orqlet validate design and validate ledger were not run."
  - "This review is an additional check, not a guarantee."
```

**Completed**
- Reviewed the round-6 design set: no blocking findings, one major (SEC-D6-1) and three minor (SEC-D6-2 to SEC-D6-4).
- Checked all five round-5 security findings: all resolved, with small leftovers tracked in the new findings.
- Not run: the hash comparison and `orqlet standards for`, because the shell was refused. The given hashes match the manifest's recorded values.

**Questions**
- Should SEC-D6-1 be fixed in the design before approval? The AS-IS file does not record these two filters either.
- For a bare repository with linked worktrees, do you accept that Orqlet refuses when the bare repository's parent folder holds the data directory (SEC-D6-2)?

**Next prompt**
```
Task: rust-migration
Next action: architect answers SEC-D6-1 to SEC-D6-4; tmishari decides on design approval
Paths: docs/design/rust-migration/design/, docs/design/rust-migration/questions.yaml, docs/design/rust-migration/reviews/
Pending approvals: design approval by tmishari; plan approval
```

## Architect's responses

The design files are unchanged since the reviewer read them, so this note's hashes match the manifest. Below is the resolution I propose for each finding. None is applied yet; the person decides whether to apply them and whether another round follows.

- SEC-D6-1 (open, major): ADR-007 gains a decision on output filters that carries over both 0.5.2 rules with their source lines:
  - `representable_version` and `representable_path` (`src/orqlet/domain/representable.py` lines 1-62, with every hidden category and range) for everything that reaches hook output or `status`;
  - `printable()` (`src/orqlet/domain/conventions.py` lines 100-111: ASCII escaping, backslash doubling and the limit+3 cut) for every repository-controlled value shown in a finding.

  Decision 8 and EC-6 are reworded: a message shows a value from the repository only through one of these filters. BC-21 gains three cases: a `workflow.lock` version with a newline gives no added context, a file name with a bidirectional mark is not shown, and a commit subject with control characters is shown escaped. The filters live in `crates/orqlet-domain/src/representable.rs` and `conventions.rs`, which join the security globs. The plan confirms that the category crate gives Co, Cn, Zl and Zp. The research file does not record these filters, so the design cites the source directly.
- SEC-D6-2: the same as architecture finding R6-F1. The parent of the common folder is compared only when that folder is named `.git`; otherwise the common folder itself is compared.
- SEC-D6-3: the same as architecture findings R6-F2 and R6-F3, including the case that doctor and sync report no ORQ-E170 from a journal planted in such a data directory.
- SEC-D6-4: the ORQ-E136 message for a bad project id names its source (the profile or `--project-id`) and leaves out the value (new). BC-21 gains the case.
- Observations: change ids keep 0.5.2's CanonicalPath rule. The advice texts that hold a change id read from a journal show it through `printable()`.

## Person's decision

On 2026-11-25 tmishari chose to apply the proposed fixes and run a seventh round with both reviewers. The fixes are applied in the round-7 design files; this note keeps its round-6 hashes.
