# Security review of the design, round 14

Reviewer: `orqlet-security-reviewer`, a typed subagent with its own context, started 2026-11-22T14:13:21Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md`, the output of `orqlet standards for` for the amended scope, the diff of the amendment against `origin/main` (9f5e93a) and the round 13 notes. This round reviewed the Q-78 amendment of `component.md` section 3 and EC-1.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-22T14:13:21Z) and at save (2026-11-22T14:55:01Z) are identical, and are those of `architecture-reviewer-design-r14.md`. The verdict asks for changes, so a new round reviews the revised content.

| File | sha256 |
|---|---|
| design/manifest.yaml | ee34c4e540c619676c0a56d30a88798c82ce9ee2f6ca4882905d9edc32d69d69 |
| design/adr-001-install-command-entry-skill-and-status.md | dd37a7501391ceed0e713d8da9190f2f5eb6de9ddb6196beba99eb697c3b8013 |
| design/adr-004-advisory-native-hooks.md | 4325a150a453f18c1602ea2a1f702e0d6bbae376459f8c67fbd32e9bfccf90af |
| design/component.md | bba8ddf22bf9cd974263494f8f15025febad7fbf5823bc66c58b577ab1da92d7 |
| questions.yaml | 13b31a97dc020149b09d578b0edb59f3524ff2e71b8ca0ab01b770dd34e018b3 |

## Reviewer output (unchanged)

# Security review of the design, round 14 (the Q-78 amendment)

**Verdict: request changes.** There is one blocking finding. The amendment widens the rule for unsafe `PATH` folders in the `status` contract, but it leaves the older, narrower rule in ADR-004 decision 7. That ADR decides whether `install` registers a hook that runs the bare `orqlet` command. Apart from that, the `status` contract in `component.md` section 3 matches the code I read, value for value, and it does not leak repository text into the output.

## What matches the code

- **Value names and order for `next`.** These match `status.py:46-61` and `_next_step` (`status.py:263-282`), and Q-63 and Q-64.
- **Reading the user manifest.** This matches `_global_states` and `_client_state` (`status.py:224-260`), `read_bounded` (`bounded_read.py:16-33`) and `_open_user_data` (`wiring.py:116-123`), and Q-65 and Q-74.
- **A `.orqlet` that is not a folder.** This matches `status.py:196-197` and Q-75.
- **A top folder name that Git output cannot carry.** `vcs_git.py:76-81` raises `VcsError`, which `status.py:170-171` turns into `not-a-repository` with the check not run. This matches Q-80.
- **The Git skip.** `searches_unsafe` (`executables.py:40-46`) counts the element that holds `git`, and any element when `git` is absent. This matches Q-73.
- **Host steps.** `locate` (`executables.py:31-38`) counts the element that holds `orqlet`. On POSIX, a folder is unsafe when others can write to it (`S_IWOTH`). This matches Q-79.
- **No repository text in the output.**
  - The `not_run` reasons are fixed strings (`status.py:39-43`).
  - `top_level` and `project` go through `representable_path` and `representable_version`.
  - The human output (`commands/status.py:30-42`) prints only those values.
  - `home-is-work-tree` compares the real path of the home folder (`wiring.py:112`) with Git's top level after `os.path.realpath` (`vcs_git.py:82`).

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 14, role: security-reviewer}
verdict: request-changes
findings:
  - id: S-1
    severity: medium
    blocking: true
    rule: ORQLET-SEC-002 (intent); ADR-004 decision 7; design consistency
    statement: >-
      The amendment's status contract uses the rule of Q-79 and Q-73. An empty, `.` or relative
      PATH element, or on POSIX a folder that others can write to, is unsafe when it is searched
      before the resolved `orqlet` or when it holds it. ADR-004 decision 7 still says only
      "empty, `.` or relative elements" that come "before the folder of the resolved `orqlet`",
      and BC-38 says the same. That ADR governs whether `install` registers a hook that runs the
      bare `orqlet`. Q-79 itself says that it "widens the literal 'before' of AC-3 and ADR-004
      decision 7", yet the self-check of the amendment says "No other section changes".
      The plan's install phase follows the narrow wording ("An unsafe PATH element before orqlet
      gives no hook registration"). So the design allows a hook to be registered when `orqlet`
      is resolved from `.` or from a relative element. In an untrusted clone, every session-start
      hook would then run that clone's own `orqlet`. It also allows a hook when the folder that
      holds `orqlet` can be written by other accounts. `status` flags both cases, so the two
      commands now disagree about the same risk.
    evidence:
      - "docs/design/one-command-setup/design/component.md:81 (amended host_steps: 'searched before the resolved orqlet or holds it', 'on POSIX a folder writable by others')"
      - "docs/design/one-command-setup/design/adr-004-advisory-native-hooks.md:77 ('empty, . or relative elements. When such an element comes before the folder of the resolved orqlet, no hook is registered')"
      - "docs/design/one-command-setup/design/component.md:301 (BC-38, 'before the folder of the resolved orqlet', relative elements only)"
      - "docs/design/one-command-setup/questions.yaml:1821-1824 (Q-79 answer widens ADR-004 decision 7)"
      - "docs/design/one-command-setup/plan.yaml:1655 (install phase: 'before orqlet')"
      - "src/orqlet/adapters/scan/executables.py:31-38, 67-74 (shipped rule counts the matching element and S_IWOTH)"
      - "/tmp/ocs-r14/design-amendment.diff manifest self-check line ('No other section changes')"
    required_change: >-
      Choose one of two fixes. The first is to amend ADR-004 decision 7 and BC-38 to the rule of
      Q-79 and Q-73: the matching element counts, and on POSIX so does a folder that others can
      write to. Then record the new hashes of D-3 and of the ADR-004 artifact in the manifest, and
      drop "No other section changes" from the self-check. The second is to raise a ledger
      question on whether `install`'s hook rule follows Q-79, and keep the design open until the
      person answers. Do not leave two rules for the same risk.
  - id: S-2
    severity: low
    blocking: false
    rule: disclosure of known limits
    statement: >-
      The amended text says Git is not run when an unsafe PATH element is searched before `git`.
      It does not carry Q-73's known limit: on Windows, nobody knows whether the process launch
      also searches the current folder, which would be the possibly hostile repository, so that
      case is not covered. GitRunner passes the bare name `git` to Popen
      (git_runner.py:50, subprocess_runner.py:34). On Windows, `_is_unsafe` also treats every
      absolute element as safe. A reader of the design alone would take the Git skip as complete.
    evidence:
      - "docs/design/one-command-setup/design/component.md:89"
      - "docs/design/one-command-setup/questions.yaml:1669-1672 (Q-73 Windows unknown)"
      - "src/orqlet/adapters/scan/executables.py:70-71"
    required_change: >-
      Add one sentence to section 3, or to section 8 on unknowns, that states the Windows limit
      of Q-73.
  - id: S-3
    severity: info
    blocking: false
    rule: scope carry-over (Q-72, Q-77)
    statement: >-
      The design now states the stop rule for consumers: stop on exit 5, on `ok: false` or on
      any `refuse-*` value. Q-77 is still open. Q-77 asks to amend the plan's acceptance
      criteria for the hook (P-5 AC-3) and the entry skill (P-10 AC-22). Until that is done,
      those acceptance criteria could act on a `next` value computed from a fallback location.
      For example, a manifest that cannot be read gives `install-global`.
    evidence:
      - "docs/design/one-command-setup/design/component.md:89"
      - "docs/design/one-command-setup/questions.yaml:1750-1769 (Q-77 open, blocks plan)"
      - "src/orqlet/application/usecases/status.py:239-240, 273-274"
    required_change: None for the design. Close Q-77 before P-5 starts.
  - id: S-4
    severity: info
    blocking: false
    rule: closed-set contract
    statement: >-
      The hook-mode report, `read_project_status` (status.py:137-141), gives
      `orqlet_on_path: null` and always an empty `host_steps`. A null is outside the closed set
      `same`, `different`, `absent` that section 3 states. The section describes only the
      `orqlet status` command, so this is not wrong today. But P-5 could emit `to_data()` from
      that report and break the closed set, and an empty `host_steps` there does not mean that
      PATH is safe.
    evidence:
      - "src/orqlet/application/usecases/status.py:111, 137-141"
      - "docs/design/one-command-setup/design/component.md:82"
    required_change: >-
      None now. P-5 should keep to the fixed template of ADR-004 and not present a hook-mode
      host_steps value as a PATH check.
  - id: S-5
    severity: info
    blocking: false
    rule: observation
    statement: >-
      In an initialized project whose lock holds a workflow version above the installed one,
      `next` is `none`. There is no refuse value for that case, unlike `refuse-newer-global` for
      the global setup. The person decided this in Q-64, and the amendment states it correctly.
      An older CLI then simply proposes nothing.
    evidence:
      - "src/orqlet/application/usecases/status.py:280-282"
      - "docs/design/one-command-setup/questions.yaml:1442-1445"
    required_change: None.
```

## Self-check

- **Model and context:** Claude Opus 5.5, running as the `orqlet-security-reviewer` subagent with a fresh context. My only inputs were the paths listed in the task. I did not see the author's conversation.
- **What I examined:**
  - The amendment diff, and my round 13 notes.
  - The ledger entries Q-63 to Q-80 (`questions.yaml:1392-1852`).
  - The standards output: 11 rules and 9 rules.
  - The code itself: `usecases/status.py` in full, `commands/status.py`, `wiring.py:93-128`, `adapters/scan/executables.py`, `ports/executables.py`, `bounded_read.py`, `vcs_git.py:1-120`, `local_fs.py:60-110`, `user_scope.py:30-56`, and the environment and argument handling in `git_runner.py`.
  - In the design: searches for the value names, `refuse-`, `next` and `writable`, ADR-001 line 31, and ADR-004 line 77. In the plan: searches for the PATH rule.
- **How:** read-only file tools only. The shell was refused.
- **What I could not do:**
  - I could not confirm that the working copy equals 9f5e93a, or that branch `timur/one-command-setup-status-contract-design` is checked out. I read the files as they are on disk.
  - I did not compute any hashes, so the new D-3 hash `bba8ddf2…` and the hashes for the round 14 notes are not checked.
  - I did not run `orqlet validate design` or check the author's recorded gate and validate runs; those remain the author's claims. As expected, the round 14 notes are not in the folder yet, so validation should report ORQ-E366.
  - I did not confirm how Python's `subprocess` searches for `git` on Windows. That stays the unknown recorded in Q-73, and I did not look it up on the web.
- **What I did not examine:** ADR-002, ADR-003, ADR-005 to ADR-007, `context.md`, `container.md`, `data-flow.md` and `sequence.md` beyond the lines my searches matched; `as-is.md`; `design-format.md`; and the evidence files.
- This review is an additional check, not a guarantee.

## Author's responses

The person chose to widen the amendment beyond section 3 and EC-1 after this round. Round 15 reviews the result.

- S-1: ADR-004 decision 7, the executable-locator row and interface of section 4, the failures rows and BC-38 follow Q-79 and Q-73: the element that holds `orqlet` counts, and on POSIX so does a folder writable by others. An absent `orqlet` also gives no registration (security review of P-4, round 6, F-1; Q-82). The self-check no longer says that no other section changes.
- S-2: section 3 states the Windows limit of Q-73.
- S-3: Q-77 is answered by the plan amendment that follows this design amendment; P-5 does not start before it merges.
- S-4: section 3 says that the table is the output of the command, not of the hook mode; the hook keeps to its fixed template (ADR-004).
- S-5: no change; the person decided it in Q-64.
