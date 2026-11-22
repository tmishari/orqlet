# Architecture review of the design, round 15

Reviewer: `orqlet-arch-reviewer`, a typed subagent with its own context, started 2026-11-22T14:56:24Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md`, the output of `orqlet standards for` for the amended scope, the full diff of the amendment against `origin/main` (9f5e93a) and both round 14 notes with the author's responses. This round reviewed the Q-78 amendment as widened after round 14, with Q-82.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-22T14:56:24Z) and at save (2026-11-22T14:57:46Z) are identical, and every design artifact hash equals the one recorded in `design/manifest.yaml`. The reviewed content is the content that will merge.

| File | sha256 |
|---|---|
| design/manifest.yaml | b9d747af0c06e349402c82d07192418f7a0fb3ae229ba6b6e94f1e1c0ea045f9 |
| design/adr-001-install-command-entry-skill-and-status.md | 6e8090d5ad69ef7f4eaa9899c4aafdec451390409cfceb210f304118f14942f9 |
| design/adr-002-user-scope-root-journal-and-manifest.md | cebc75c65fe6fce24b90a50e62802c680a42f02b72c8559f473fddc91b43ea4a |
| design/adr-003-copilot-client-adapter.md | f763bb0985455103f43a8392e4fdd7e7212bb94b92814f6564dcc98be91d4144 |
| design/adr-004-advisory-native-hooks.md | d94600fdcf8802e7b375f4b30bf7ba818005ec28956d1dec17892a29e68b7f26 |
| design/adr-005-behavioural-foundation.md | 9e5c51e9ce4b010dec0647a71ef326fb49369916d1d83583aaa1fb93c789119d |
| design/adr-006-bundled-skills-and-tool-preparation.md | bf3151f13feb9a0e88ab22bb8738f4a55f61ad6224d341fab28876ec14f17217 |
| design/adr-007-terminal-presentation.md | 57819e41031b80160ca84014ecbadf69e7e1653b5c8c059ad30515bef425e6cb |
| design/component.md | 3aa6db54c2fd5b7f1c7e73134522e053d18b7312073e685ec54429a00b91743d |
| design/container.md | 90721a62908fb297cfb2ec18a91a79f69d5e1423a1bc08d3293baec0e88fd7da |
| design/context.md | a45782f35b499e7e4ea8e99d55789e17088e9b2a34d2130b182ba7fb56e417bb |
| design/data-flow.md | 58b25a0a6b0a255baa1ac43c8926e96e622a582be18129520038c9fe20d85117 |
| design/proposal.md | 8c5869fac7543feebd0c403d0fe7430eca1749ccf7df12bbb0a5bedc3a9c359e |
| design/sequence.md | a33c114656afc2a1d461f51795e10c9f0d89cc600fd81e7d29983b082257a33f |
| questions.yaml | 362cabf0be451b6b3093d3ec0f7f02b1d6900ae515a72865d53a92792754dbd1 |

## Reviewer output (unchanged)

**Verdict: approve.** Both blocking findings from round 14 are resolved, and the amendment answers Q-78 and Q-82 in a way that matches the code. Six findings remain: three low and three info, none blocking.

**What I checked against the code:**
- **Status contract.** The five locations, the seven `next` values, the four client states and the single host-step code in section 3 match the code (`status.py:46-72`). So do the JSON shape (`status.py:105-117`) and the order in which `next` is chosen (Q-64, `status.py:263-282`).
- **Q-73 and Q-79 rules.** `ExecutableLookup`, `locate` and `searches_unsafe` behave as the design describes (`ports/executables.py:16-35`, `adapters/scan/executables.py:31-75`).
- **Q-69 and Q-70.** The invisible characters that section 3 cites are the ones the code refuses (`representable.py:17-35`).
- **Exit status.** Exit 5 with `not_run` matches `commands/status.py:20-25`.

**Round 14 follow-up:**
- **Architecture F-1 (stop rule).** Section 3 now states only what Q-72 decided (`component.md:89`). The ADR-001 table stops on every `refuse-*` value and cites Q-63, whose chosen option names the refuse values as stop values (`questions.yaml:1407`).
- **Architecture F-2 (ADR-001 table).** The table at `adr-001…md:19-28` now reads the `next` values. It covers each value together with its location, including the row for a check not run.
- **Architecture F-3 and security S-1 (`PATH` rule).** ADR-004 decision 7, the locator row and interface, the failures rows and BC-38 now use one rule. They also add the Q-82 rule for an absent `orqlet`.
- **F-5, F-6, I-2, I-3, S-2 and S-4.** These are addressed as the author's responses say.
- **F-4 (character rule wording).** Only partly addressed; it carries over as F-1 below.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 15, role: architecture-reviewer}
verdict: approve
findings:
  - id: F-1
    severity: low
    blocking: false
    rule: design-set consistency (carry-over of round 14 F-4)
    statement: >-
      Section 3 says the rules of ADR-001 decision 3 "also refuse the invisible characters of Q-69
      and Q-70". The text of ADR-001 decision 3 does not say that: it lists only control,
      bidirectional and format characters and 200 characters. ADR-004 decision 1a says the
      post-edit path follows "the rule of `status`", but it repeats the same narrower list. The
      failures row for a `status` path also keeps the narrow wording. The shipped rule is wider
      (Cc, Cf, Cs, Co, Cn, Zl, Zp and the ranges of Q-69 and Q-70).
    evidence:
      - "docs/design/one-command-setup/design/component.md:85"
      - "docs/design/one-command-setup/design/component.md:223"
      - "docs/design/one-command-setup/design/adr-001-install-command-entry-skill-and-status.md:33"
      - "docs/design/one-command-setup/design/adr-004-advisory-native-hooks.md:44"
      - "src/orqlet/domain/representable.py:17-35"
    required_change: >-
      State the rule once, in ADR-001 decision 3, with Q-69 and Q-70 cited or with a pointer to
      `domain/representable.py`. Have ADR-004 decision 1a and the failures row refer to it rather
      than repeat the narrower list.
  - id: F-2
    severity: low
    blocking: false
    rule: design-format "Each ADR compares the real alternatives, and its Consequences name the trade-offs"
    statement: >-
      ADR-004 decision 7 gains the Q-82 rule: no hook is registered when `orqlet` is absent from
      `PATH`. The ADR's Consequences and Rejected alternatives were not changed. They do not say
      what the rule costs: a person who runs `install` before the uv or pipx tool folder is on
      `PATH`, or who runs it through an unidentified program (Q-76), gets no hooks until a rerun.
      They also do not record the rejected Q-82 option, which was to report the unsafe element in
      `status` instead.
    evidence:
      - "docs/design/one-command-setup/design/adr-004-advisory-native-hooks.md:77"
      - "docs/design/one-command-setup/design/adr-004-advisory-native-hooks.md:81-97"
      - "docs/design/one-command-setup/questions.yaml:1888-1890"
    required_change: >-
      Add one Consequences bullet for the cost, and one Rejected-alternatives bullet for the second
      Q-82 option with the reason it was rejected.
  - id: F-3
    severity: low
    blocking: false
    rule: design-format brief part 8 (unresolved decisions); self-check accuracy
    statement: >-
      Section 8 and the self-check still say that "Q-32 to Q-44 and Q-60" are the answered
      decisions. They do not mention Q-82, which was raised in the design phase and answered here.
      They do not mention that Q-77 and Q-81 are open and block only the plan. The self-check also
      says the session-start hook's stop rule "is left to the plan amendment that answers Q-77",
      yet section 3 already says the hook stops on a check not run (Q-72). What actually remains
      under Q-77 is narrower: the wording of P-5 AC-3 and P-10 AC-22, and what the hook does with
      `refuse-newer-global`. That is the one refuse value hook mode can produce, because there its
      location is always `initialized-project`.
    evidence:
      - "docs/design/one-command-setup/design/component.md:332"
      - "docs/design/one-command-setup/design/manifest.yaml:186-187"
      - "docs/design/one-command-setup/design/component.md:89"
      - "docs/design/one-command-setup/questions.yaml:1750-1769"
      - "src/orqlet/application/usecases/status.py:137-141, 268-269"
    required_change: >-
      Add a sentence to section 8 saying that Q-82 is answered, and that Q-77 and Q-81 are open,
      block only the plan, and leave no design decision open. Name exactly what remains under Q-77.
      Align the self-check sentence with it.
  - id: F-4
    severity: info
    blocking: false
    rule: contract precision
    statement: >-
      Section 3 says the session-start hook stops on "exit 5 or `ok: false`". The hook does not
      run the `status` command: it calls the hook mode in the same process, so it sees no exit code
      and no envelope. Its equivalent is a non-empty `not_run`. Hook mode can produce one, for an
      unreadable lock or manifest.
    evidence:
      - "docs/design/one-command-setup/design/component.md:89"
      - "src/orqlet/application/usecases/status.py:137-141, 161"
    required_change: Optional. Say "a check not run (exit 5, `ok: false`, or in hook mode a non-empty `not_run`)".
  - id: F-5
    severity: info
    blocking: false
    rule: carry-over to the plan
    statement: >-
      The answer to Q-82 prescribes plan changes for P-5, P-6 and P-10. The plan's install phase
      still says only "An unsafe PATH element before orqlet gives no hook registration", and has no
      rule for an absent `orqlet`. No open ledger question tracks these plan changes; Q-77 and Q-81
      cover other subjects. The answer also says that "section 3" states the absent rule, but
      section 3 item 7 only flags an absent `orqlet`. The no-registration rule is in section 5 and
      in ADR-004 decision 7.
    evidence:
      - "docs/design/one-command-setup/plan.yaml:1655"
      - "docs/design/one-command-setup/questions.yaml:1894-1898"
      - "docs/design/one-command-setup/design/component.md:57, 214"
    required_change: >-
      None for the design. The plan amendment should carry Q-79 and Q-82 into P-10, P-5 and P-6
      alongside Q-77 and Q-81.
  - id: F-6
    severity: info
    blocking: false
    rule: baseline "Verify with evidence"
    statement: >-
      The self-check does not say whether the validation entry was re-run after the amendment was
      widened following round 14 (the ADR-001, ADR-002 and ADR-004 edits). The standards input
      covers `usecases/status.py` and `commands/status.py`. The widened scope now also describes
      `adapters/scan/executables.py`, which is in an adapters path. I infer, but did not verify,
      that its rules fall within `standards_applied`. I also could not recompute the new sha256
      values of D-3, D-6, D-7 and D-9.
    evidence:
      - "docs/design/one-command-setup/design/manifest.yaml:206-207"
      - "/tmp/ocs-r14/standards.txt:1-44"
    required_change: >-
      Optional. Record that `orqlet validate design` and `orqlet validate ledger` were run on the
      final round 15 content, and add `orqlet standards for --path src/orqlet/adapters/scan/executables.py`
      to the input check.
```

## Self-check

**What I examined:**
- **Inputs read in full:** the round 15 diff, both round 14 notes with the author's responses, the standards output and `design-format.md`.
- **Design files:** `manifest.yaml`, `component.md`, ADR-001 and `sequence.md` in full, and lines 28-97 of ADR-004.
- **Ledger:** Q-63 to Q-82.
- **Searches:** status values, `PATH` wording, the representability rule and the old `global:` field across every design artifact. I also searched `plan.yaml` for phase ids and the `PATH` rule.
- **Code:** `usecases/status.py`, `ports/executables.py`, `adapters/scan/executables.py`, `domain/representable.py`, `commands/status.py`, and the status wiring lines of `wiring.py`.
- **Q-82 evidence:** finding F-1 in `security-reviewer-P-4-r6.yaml`.

**What I could not do:**
- Ask mode refused every shell command, so I could not run `git`, `orqlet validate`, `orqlet gate status` or any hashing. The artifact sha256 values and the Q-82 ledger key are unchecked.
- I read the working tree, not 9f5e93a, and could not confirm which branch is checked out.

**What I did not examine:** `as-is.md`, ADR-003, ADR-005 to ADR-007 (beyond lines my searches matched), `context.md`, `container.md`, `data-flow.md` (only the lines my searches matched), the tests, and the evidence pages.

**Expected and not counted as findings:** ORQ-E366 for the missing round 15 notes, and Q-77 and Q-81 being open.

**Model:** this ran as the `orqlet-arch-reviewer` subagent with a fresh context. I cannot see the underlying model class.

This review is an additional check, not a guarantee.

## Author's responses

The design is not edited after this round, so the reviewed content is the content that will merge.

- F-1: no change in this amendment. The shipped rule is in `src/orqlet/domain/representable.py` with Q-69 and Q-70; aligning the narrower wording of ADR-001 decision 3, ADR-004 decision 1a and the failures row is left for a later design amendment, named in the pull request description.
- F-2: no change in this amendment. The cost (no hooks until a rerun with `orqlet` on `PATH`) is shown by the `host step` that install reports; the rejected option is recorded in Q-82's options. Named in the pull request description for the person.
- F-3: what remains under Q-77 is the wording of P-5 AC-3 and P-10 AC-22 (including the hook's behaviour on `refuse-newer-global`); the plan amendment answers it. Section 8 is not edited in this amendment.
- F-4: the plan amendment words the hook's criterion as a non-empty `not_run`, the hook-mode form of a check not run.
- F-5: the plan amendment carries Q-79 and Q-82 into P-10 AC-12, P-5 and P-6.
- F-6: `orqlet validate design` (D3; ORQ-E366 only for the notes of the round in progress) and `orqlet validate ledger` (PASS) ran on the round 15 content at 2026-11-22T14:56:24Z, and after this note was saved. The standards of `src/orqlet/adapters/scan/executables.py` are recorded in the plan amendment's input check.
