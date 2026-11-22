# Architecture review of the design, round 14

Reviewer: `orqlet-arch-reviewer`, a typed subagent with its own context, started 2026-11-22T14:13:21Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md`, the output of `orqlet standards for` for the amended scope, the diff of the amendment against `origin/main` (9f5e93a) and the round 13 notes. This round reviewed the Q-78 amendment of `component.md` section 3 and EC-1.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-22T14:13:21Z) and at save (2026-11-22T14:55:01Z) are identical. The verdict asks for changes, so a new round reviews the revised content.

| File | sha256 |
|---|---|
| design/manifest.yaml | ee34c4e540c619676c0a56d30a88798c82ce9ee2f6ca4882905d9edc32d69d69 |
| design/adr-001-install-command-entry-skill-and-status.md | dd37a7501391ceed0e713d8da9190f2f5eb6de9ddb6196beba99eb697c3b8013 |
| design/adr-002-user-scope-root-journal-and-manifest.md | 0b890be14e93582429f978dcb938697aaa8e51f70be52ad6c65e6e6a6c832a43 |
| design/adr-003-copilot-client-adapter.md | f763bb0985455103f43a8392e4fdd7e7212bb94b92814f6564dcc98be91d4144 |
| design/adr-004-advisory-native-hooks.md | 4325a150a453f18c1602ea2a1f702e0d6bbae376459f8c67fbd32e9bfccf90af |
| design/adr-005-behavioural-foundation.md | 9e5c51e9ce4b010dec0647a71ef326fb49369916d1d83583aaa1fb93c789119d |
| design/adr-006-bundled-skills-and-tool-preparation.md | bf3151f13feb9a0e88ab22bb8738f4a55f61ad6224d341fab28876ec14f17217 |
| design/adr-007-terminal-presentation.md | 57819e41031b80160ca84014ecbadf69e7e1653b5c8c059ad30515bef425e6cb |
| design/component.md | bba8ddf22bf9cd974263494f8f15025febad7fbf5823bc66c58b577ab1da92d7 |
| design/container.md | 90721a62908fb297cfb2ec18a91a79f69d5e1423a1bc08d3293baec0e88fd7da |
| design/context.md | a45782f35b499e7e4ea8e99d55789e17088e9b2a34d2130b182ba7fb56e417bb |
| design/data-flow.md | 58b25a0a6b0a255baa1ac43c8926e96e622a582be18129520038c9fe20d85117 |
| design/proposal.md | 8c5869fac7543feebd0c403d0fe7430eca1749ccf7df12bbb0a5bedc3a9c359e |
| design/sequence.md | a33c114656afc2a1d461f51795e10c9f0d89cc600fd81e7d29983b082257a33f |
| questions.yaml | 13b31a97dc020149b09d578b0edb59f3524ff2e71b8ca0ab01b770dd34e018b3 |

## Reviewer output (unchanged)

**Verdict: request changes.** The new `status` contract in `component.md` section 3 and in EC-1 matches the code I read, and it answers Q-78's request for the value names. Two problems block approval:

- **The amendment settles an open question.** It writes a rule for when the session-start hook and the entry skill must stop, and that is the subject of Q-77, which is still open.
- **ADR-001 now contradicts section 3.** It has an entry-skill state table that the amendment left unchanged, and that table no longer agrees with the new `next` rules.

The sandbox refused every shell command, including `git`. So I read the code in the working tree, not at 9f5e93a. I also could not run hashing or `orqlet validate`.

**What matches the code, checked line by line:**
- **Value sets:** the five locations, the seven `next` values, the four client states and the single host-step code are the enums in `status.py:46-72`.
- **JSON shape:** the fields and their nesting match `StatusReport.to_data` (`status.py:105-117`).
- **Order of `next`:** it is the first-match rule of Q-64 (`status.py:263-282`).
- **Client states:** the reading of the user manifest follows Q-65 (`status.py:224-260`).
- **Locations:** the home-folder check (`status.py:186`, `:202-205`) and the rule that anything at `.orqlet` that is not a folder counts as an initialised project with a check not run (Q-75, `status.py:196-197`) match.
- **Git skipped:** when `PATH` searches an unsafe folder first, Git is not run (Q-73, `status.py:166-167`, `executables.py:40-46`).
- **Unsafe `PATH` folder:** a folder writable by others counts, and so does the folder that holds `orqlet` (Q-79, `executables.py:31-38`, `:67-75`).
- **Top folder Git cannot print:** a name with a line feed or non-UTF-8 bytes gives `not-a-repository` and a check not run (Q-80, `vcs_git.py:76-81`).
- **Unknown running program:** it is reported as `different` (Q-76, `executables.py:77-81`, `wiring.py:126-128`).
- **Exit status:** exit 5 with `not_run` (`commands/status.py:20-25`).

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 14, role: architecture-reviewer}
verdict: request-changes
findings:
  - id: F-1
    severity: medium
    blocking: true
    rule: baseline "Do not guess"; design-format "a consequential decision the design cannot make is a ledger question"
    statement: >-
      The amendment decides an open question. component.md:89 says that the entry skill and the
      session-start hook stop when `next` is any `refuse-*` value. Q-72 decides only that they stop
      on exit 5 or `ok: false`. Stopping on `refuse-home-is-work-tree`, and stopping the hook on a
      refuse value at all, is what Q-77 asks, and Q-77 is still open (it blocks the plan). The
      amendment cites only Q-72 for the sentence. The self-check says "No other section changes"
      and "No consequential decision is open".
    evidence:
      - "docs/design/one-command-setup/design/component.md:89"
      - "docs/design/one-command-setup/questions.yaml:1624-1647 (Q-72 answer: exit 5 or ok false only)"
      - "docs/design/one-command-setup/questions.yaml:1750-1769 (Q-77, status: open)"
      - "docs/design/one-command-setup/design/manifest.yaml:183-184"
    required_change: >-
      Either keep only what Q-72 decides (stop on exit 5 or `ok: false`) and name Q-77 as open in
      section 8, or have the person answer Q-77 first and cite it in this sentence.
  - id: F-2
    severity: medium
    blocking: true
    rule: design-set consistency (ADR-001 makes the status output a stable contract); component.md section 3 points to ADR-001
    statement: >-
      ADR-001 decision 2 is the approved entry-skill state table, and it was not changed. It now
      disagrees with section 3. It has no row for `refuse-home-is-work-tree`, none for
      `refuse-newer-global`, and none for an `outdated` client. Its "Global setup missing" row starts
      install, but `install-global` now also covers "any client outdated" (Q-64). The entry skill
      will be built from this ADR, so it would meet values the ADR does not handle.
    evidence:
      - "docs/design/one-command-setup/design/adr-001-install-command-entry-skill-and-status.md:17-26"
      - "docs/design/one-command-setup/design/component.md:87"
      - "docs/design/one-command-setup/questions.yaml:1440-1447 (Q-64)"
    required_change: >-
      Rewrite the ADR-001 decision 2 table so that it reads the `next` values of section 3, with a
      stop row for each `refuse-*` value as the person decides under F-1. Or add a note that points
      the table at section 3 and cites Q-63 and Q-64.
  - id: F-3
    severity: medium
    blocking: false
    rule: design-set consistency
    statement: >-
      Q-79 says it widens the word "before" in ADR-004 decision 7. Section 3 now counts the folder
      that holds `orqlet` and folders writable by others. ADR-004 decision 7, the executable-locator
      row and interface in section 4, the failures row and BC-38 still say only "empty, `.` or
      relative" folders, and only "before" `orqlet`. The interface still says `locate` returns a
      list of unsafe folders, but the shipped port returns a yes/no answer
      (`unsafe_element_searched`) and adds `searches_unsafe`.
    evidence:
      - "docs/design/one-command-setup/design/adr-004-advisory-native-hooks.md:77"
      - "docs/design/one-command-setup/design/component.md:81, :182, :193, :216, :302"
      - "src/orqlet/application/ports/executables.py:16-35"
      - "docs/design/one-command-setup/questions.yaml:1821-1824"
    required_change: >-
      Bring these places in line with Q-79 and the shipped port, or say in the self-check that they
      are left as they are on purpose and why.
  - id: F-4
    severity: low
    blocking: false
    rule: self-check accuracy ("give the status contract that P-4 shipped")
    statement: >-
      `top_level_reason` refers to "the rules of ADR-001 decision 3". That rule lists only control,
      bidirectional and format characters and 200 characters. The shipped rule also refuses the
      characters added by Q-69 and Q-70 (variation selectors, Hangul fillers, U+2800, unassigned
      code points). ADR-001:31, ADR-004:44 and the failures row at component.md:222 keep the
      narrower wording. The header of component.md lists Q-72 to Q-76 but not Q-69 or Q-70.
    evidence:
      - "docs/design/one-command-setup/design/component.md:3, :85, :222"
      - "docs/design/one-command-setup/design/adr-001-install-command-entry-skill-and-status.md:31"
      - "src/orqlet/domain/representable.py:19-30"
      - "docs/design/one-command-setup/questions.yaml:1570-1572, :1593-1594"
    required_change: Cite Q-69 and Q-70 where the representability rule is stated, or point the rule at the domain module.
  - id: F-5
    severity: low
    blocking: false
    rule: design-format brief part 6 (acceptance criteria cover the behaviour); consistency
    statement: >-
      The acceptance criteria and several unchanged lines still use the old flat `global` field
      ("global: newer"). BC-11 lists no `home-is-work-tree` state. No BC covers
      `refuse-home-is-work-tree`, `install-global` when a client is outdated, Git skipped because of
      an unsafe `PATH` folder (Q-73), a non-folder `.orqlet` (Q-75), or a data directory that
      cannot be checked (Q-74).
    evidence:
      - "docs/design/one-command-setup/design/component.md:219, :250-258"
      - "docs/design/one-command-setup/design/adr-002-user-scope-root-journal-and-manifest.md:63"
    required_change: >-
      Change BC-11 to the `global.clients` shape and add these states to it, or record that P-4's
      plan criteria (tests/P-4.yaml) cover them and the design leaves them out.
  - id: F-6
    severity: low
    blocking: false
    rule: baseline "Verify with evidence"
    statement: >-
      The self-check records an input check for the Q-78 amendment, but no `orqlet validate design`
      or `orqlet validate ledger` run on the amended files. The Q-60 revision recorded both. I could
      not recompute the new sha256 of D-3.
    evidence: ["docs/design/one-command-setup/design/manifest.yaml:201-204"]
    required_change: >-
      Run both validators and record the result, labelled "pass except the expected ORQ-E366" if
      that is the outcome.
  - id: I-1
    severity: info
    blocking: false
    rule: baseline "Do not guess"
    statement: >-
      The answer to Q-78 was written in the same diff as the amendment (time 14:11Z) and repeats the
      amendment's content. Only option 1, "before P-5", is a choice among the listed options. The
      repository cannot show that the person confirmed the content.
    evidence: ["docs/design/one-command-setup/questions.yaml:1791-1801"]
    required_change: Optional. The person confirms the answer value when approving.
  - id: I-2
    severity: info
    blocking: false
    rule: contract completeness
    statement: >-
      `read_project_status`, the hook mode, sets `orqlet_on_path` to null, leaves `host_steps` empty
      and leaves `top_level` null. The table allows no null `orqlet_on_path`. Nothing used
      `read_project_status` at the time of review, so this matters only if the hook later prints
      `to_data()`.
    evidence: ["src/orqlet/application/usecases/status.py:137-141", "docs/design/one-command-setup/design/component.md:82, :198"]
    required_change: Optional. Say that the table is the command's output only.
  - id: I-3
    severity: info
    blocking: false
    rule: self-check consistency
    statement: >-
      self_check.questions adds Q-78 but none of Q-63 to Q-66, Q-72 to Q-76, Q-79 or Q-80, which the
      amendment relies on. The header of component.md still says it reads "Q-1 to Q-44, and Q-60".
    evidence: ["docs/design/one-command-setup/design/manifest.yaml:210", "docs/design/one-command-setup/design/component.md:3"]
    required_change: Optional. Apply one listing rule.
```

## Self-check

**What I examined:**
- **Inputs read in full:** the amendment diff, the round 13 notes, the standards output, `design-format.md`, `manifest.yaml`, `component.md`, ADR-001, and Q-61 to Q-81 in the ledger.
- **Other design files:** the lines that my searches for `status`, `next`, `before` and `relative` matched in ADR-002, ADR-004, `sequence.md`, `container.md`, `context.md` and `data-flow.md`.
- **Code:** `usecases/status.py`, `commands/status.py`, `ports/executables.py`, `adapters/scan/executables.py` and `adapters/git/vcs_git.py`. I also read the relevant parts of `wiring.py` (the status services) and `domain/representable.py`.

**What I could not do:**
- The sandbox refused shell commands, so I could not run `git show 9f5e93a`. I could not confirm that the working-tree code equals 9f5e93a; the diff touches only documentation, which suggests it does, but I did not check it.
- I recomputed no sha256 and ran no `orqlet validate` or `orqlet gate status`.
- I did not read `as-is.md`, `plan.yaml`, `tests/P-4.yaml` or the tests.

**Expected:** ORQ-E366 for the round 14 notes, which do not exist yet, is not counted as a finding.

**Model:** this review ran as the `orqlet-arch-reviewer` subagent with a fresh context. The underlying model class is not visible to me.

This is an additional check, not a guarantee.

## Author's responses

The person chose to widen the amendment beyond section 3 and EC-1 after this round. Round 15 reviews the result.

- F-1: section 3 now states only the rule of Q-72 (stop on a check not run). Which consumer stops on which `refuse-*` value is left to the plan amendment that answers Q-77.
- F-2: ADR-001 decision 2's table now reads the `next` values of section 3, with Q-63, Q-64 and Q-72 cited.
- F-3: ADR-004 decision 7, the executable-locator row and interface of section 4, the failures rows and BC-38 follow Q-79 and the shipped port, and add the rule for an absent `orqlet` (Q-82).
- F-4: section 3 cites Q-69 and Q-70 for the representability rule.
- F-5: BC-11 uses `global.clients`, lists the home work tree, and adds the states of Q-73 to Q-75; ADR-002 decision 2 says "a client `newer`".
- F-6: the validator runs are recorded in the self-check.
- I-1: the Q-78 answer is shown to the person in the pull request description for confirmation at approval.
- I-2: section 3 says that the table is the output of the command, not of the hook mode.
- I-3: the component.md header lists the questions the amendment relies on; `self_check.questions` lists the questions answered in this amendment session (Q-78, Q-82).
