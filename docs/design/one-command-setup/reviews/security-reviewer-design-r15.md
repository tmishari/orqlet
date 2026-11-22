# Security review of the design, round 15

Reviewer: `orqlet-security-reviewer`, a typed subagent with its own context, started 2026-11-22T14:56:24Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md`, the output of `orqlet standards for` for the amended scope, the full diff of the amendment against `origin/main` (9f5e93a) and both round 14 notes with the author's responses. This round reviewed the Q-78 amendment as widened after round 14, with Q-82.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-22T14:56:24Z) and at save (2026-11-22T14:57:46Z) are identical, are those of `architecture-reviewer-design-r15.md`, and equal the hashes recorded in `design/manifest.yaml`.

| File | sha256 |
|---|---|
| design/manifest.yaml | b9d747af0c06e349402c82d07192418f7a0fb3ae229ba6b6e94f1e1c0ea045f9 |
| design/adr-001-install-command-entry-skill-and-status.md | 6e8090d5ad69ef7f4eaa9899c4aafdec451390409cfceb210f304118f14942f9 |
| design/adr-002-user-scope-root-journal-and-manifest.md | cebc75c65fe6fce24b90a50e62802c680a42f02b72c8559f473fddc91b43ea4a |
| design/adr-004-advisory-native-hooks.md | d94600fdcf8802e7b375f4b30bf7ba818005ec28956d1dec17892a29e68b7f26 |
| design/component.md | 3aa6db54c2fd5b7f1c7e73134522e053d18b7312073e685ec54429a00b91743d |
| questions.yaml | 362cabf0be451b6b3093d3ec0f7f02b1d6900ae515a72865d53a92792754dbd1 |

## Reviewer output (unchanged)

**Verdict: approve.** I found no blocking security risk in the round 15 amendment. The two round 14 problems are fixed. The `install` hook rule and `status` now apply the same unsafe-`PATH`-element rule (Q-79), and the Windows limit of Q-73 is now stated. The new rule from Q-82 (register no hook at all when `orqlet` is not on `PATH`) is the same in ADR-004 decision 7, the failures table, BC-38 and the ledger. The four findings below are non-blocking. Finding S-1 should be closed before the install phase is implemented.

## What matches the code

- **`PATH` rule.** ADR-004 decision 7 (`adr-004-advisory-native-hooks.md:77`), BC-38 (`component.md:306`), the failures rows (`component.md:214-219`) and the executable-locator row and interface (`component.md:182`) now say the same thing. An empty, `.` or relative element, or on POSIX a folder writable by others, counts when it is searched before the match or holds it. This matches `locate` and `_is_unsafe` (`executables.py:31-38`, `:67-75`) and the port (`ports/executables.py:17-35`).
- **Absent `orqlet`.** `locate` returns `absent` with `unsafe_element_searched=False` (`executables.py:38`). So the "whatever `PATH` holds" rule in ADR-004 is needed, and the amendment states it.
- **Git skip.** The Git skip and its Windows limit (`component.md:89`) match `searches_unsafe` (`executables.py:40-46`), `_locate` (`status.py:165-167`) and Q-73.
- **Entry skill.** The table in ADR-001 decision 2 stops on exit 5 or `ok: false` before it reads `next` (`adr-001…md:18-28`). This is the stop rule of Q-72, so a fallback `install-global` value is not acted on.
- **Hook mode.** Section 3 limits the documented shape to the command's output, and says the hook mode prints only its fixed template (`component.md:89`). This answers round 14 S-4 (`status.py:137-141`).
- **No repository text in the output.** The `not_run` reasons are still fixed strings (`status.py:39-43`). `top_level` and the project version still go through the representability functions (`status.py:174`, `:221`).
- **Secrets.** The diff holds no secret, credential or private host.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 15, role: security-reviewer}
verdict: approve
findings:
  - id: S-1
    severity: medium
    blocking: false
    rule: ORQLET-SEC-002 (intent); design-to-plan traceability; ADR-004 decision 7
    statement: >-
      The plan's install criterion AC-12 still uses the old narrow rule: "An unsafe PATH element
      before orqlet gives no hook registration". It has no rule for an absent orqlet. Q-82's answer
      says the plan changes (P-10 registers no hook, P-5 pins the absent value, P-6 accepts a change
      with no hook entry). But Q-82 blocks only the design and is answered. Q-79 blocks only
      implementation and is answered. The open plan questions Q-77 and Q-81 are about other things.
      So no open ledger item makes the coming plan amendment carry the Q-79 and Q-82 rule into AC-12.
      An implementer who follows AC-12 as it reads now could register a hook when orqlet is in `.`,
      in a relative element, in a folder writable by others, or absent. In an untrusted clone, every
      session-start hook would then run the clone's own orqlet.
    evidence:
      - "docs/design/one-command-setup/plan.yaml:1653-1658 (AC-12, 'before orqlet', no absent rule, source BC-38)"
      - "docs/design/one-command-setup/design/component.md:306 (BC-38 as amended)"
      - "docs/design/one-command-setup/questions.yaml:1890-1901 (Q-82 blocks design only; its answer names P-5, P-6 and P-10 changes)"
      - "docs/design/one-command-setup/questions.yaml:1853-1872, 1750-1769 (Q-81 and Q-77, the only open plan questions)"
    required_change: >-
      Make the plan amendment that answers Q-77 and Q-81 also rewrite AC-12 to match BC-38 (the
      matching element counts, writable-by-others counts on POSIX, and absent means no registration),
      and add the P-5 and P-6 changes that Q-82 names. Or raise an open question that blocks the
      plan for this. Do not start the install phase (P-10) before that.
  - id: S-2
    severity: medium
    blocking: false
    rule: ADR-004 decision 7 (consistency of the Q-82 reason); disclosure of known limits
    statement: >-
      ADR-004 now refuses to register a hook when orqlet is absent, "because the bare command could
      later resolve through an unsafe element". The same thing can happen after a registration that
      install allowed. Only elements up to the match are checked; elements after it never are
      (executables.py:33-37). Take PATH="~/.local/bin:." at install time. The hook is registered.
      If the person later removes the CLI with `uv tool uninstall orqlet` or `pipx uninstall`
      instead of `orqlet uninstall`, the hook entries stay in the client files. The bare `orqlet`
      then resolves through `.`, so a session in a hostile clone runs that clone's `orqlet`. Q-42
      accepts a different launch PATH, but not this case. No design file and no ledger entry
      mentions CLI removal.
    evidence:
      - "docs/design/one-command-setup/design/adr-004-advisory-native-hooks.md:77 (the Q-82 reason)"
      - "docs/design/one-command-setup/design/adr-004-advisory-native-hooks.md:90 (Q-42 covers only the launch PATH)"
      - "src/orqlet/adapters/scan/executables.py:31-38 (the scan stops at the match)"
      - "search of design/*.md, as-is.md and questions.yaml for 'tool uninstall', 'pipx uninstall' and 'CLI is removed': no match"
    required_change: >-
      Raise a ledger question for the person. Option one: install also registers no hook when an
      unsafe element appears anywhere in PATH, as searches_unsafe already does for an absent name.
      Option two: accept the CLI-removal case as a known leftover risk, state it in ADR-004
      Consequences, and say in the user documentation to run `orqlet uninstall` before removing
      the CLI.
  - id: S-3
    severity: low
    blocking: false
    rule: disclosure to the person (ADR-004 decision 7, the host step)
    statement: >-
      The entry skill's table acts only on `next` and the stop rule for a check not run. It does
      nothing with `global.host_steps` (`unsafe-path-element`) or with `orqlet_on_path` (`different`
      or `absent`). It then runs `orqlet install`, `init` or `upgrade` by the bare name in the agent's
      shell. When status has just reported an unsafe PATH element, the person is not told before
      those commands run, and the commands resolve through the same PATH. Every write still needs a
      preview and the person's yes, so this is a disclosure gap, not a bypass.
    evidence:
      - "docs/design/one-command-setup/design/adr-001-install-command-entry-skill-and-status.md:18-28"
      - "docs/design/one-command-setup/design/component.md:81-82"
    required_change: >-
      Have the entry skill show any host_steps code, and orqlet_on_path when it is not `same`, to
      the person before it proposes a command. Without Q-76, it must not treat `different` as proof
      that another orqlet is installed. This can be a criterion of the plan amendment for P-10.
  - id: S-4
    severity: info
    blocking: false
    rule: disclosure of known limits
    statement: >-
      On POSIX, "writable by others" in the amended text means only the others write bit
      (S_IWOTH). A folder writable by its group, a folder owned by another non-root account, and a
      folder that does not exist yet all count as safe (executables.py:72-75). An example of the
      first is a group-writable /usr/local/bin. P-4 round 6 F-2 noted this, and Q-73 and Q-79 word
      it the same way. The design is now the stable contract for this rule, and it does not name
      this limit.
    evidence:
      - "src/orqlet/adapters/scan/executables.py:67-75"
      - "docs/design/one-command-setup/design/adr-004-advisory-native-hooks.md:77"
      - "docs/design/one-command-setup/reviews/security-reviewer-P-4-r6.yaml:78-84 (F-2)"
    required_change: >-
      None blocking. Optionally say "the others write bit" in place of "writable by others", and
      list the group-writable, foreign-owned and missing-folder cases as a known limit in ADR-004
      Consequences.
```

## Self-check

- **Model and context:** Claude Opus 5.5, running as the `orqlet-security-reviewer` subagent with a fresh context. My inputs were only the paths in the task. I did not see the author's conversation.
- **What I examined:**
  - The full r15 amendment diff and the standards output (11 rules and 9 rules).
  - The round 14 security notes and the author's responses in the round 14 architecture notes.
  - Ledger entries Q-72 to Q-82 (`questions.yaml:1624-1902`).
  - ADR-004 lines 60-100, the hits for `Act on`, `Report status` and `refuse-newer-global` in ADR-001, and every `PATH` mention in the design folder.
  - Plan AC-12 (`plan.yaml:1640-1670`) and the plan's hits for `absent`, `unsafe PATH` and `host_steps`.
  - The code: `usecases/status.py` in full, `adapters/scan/executables.py` in full and `ports/executables.py` in full.
  - The P-4 round 6 security record.
- **How:** read-only file tools only. The shell was refused in this mode.
- **What I could not do:**
  - I could not confirm that the checked-out branch is `timur/one-command-setup-status-contract-design`, or that the working copy is based on 9f5e93a. I read the files on disk.
  - I computed no hashes, so the new D-3, D-6, D-7 and D-9 hashes in `manifest.yaml` are unverified.
  - I ran neither `orqlet validate design` nor `orqlet validate ledger`. ORQ-E366 for the missing round 15 notes is expected and was not checked.
  - Windows process lookup stays the unknown of Q-73. I looked nothing up on the web.
- **What I did not examine:** ADR-002 beyond the diff hunk; ADR-003 and ADR-005 to ADR-007; `context.md`, `container.md`, `data-flow.md` and `sequence.md`; `as-is.md`; `design-format.md`; the evidence files; the plan outside AC-12 and the search hits; `wiring.py`, `vcs_git.py` and `git_runner.py` at this round, whose round 14 reading I did not repeat.
- This review is an additional check, not a guarantee.

## Author's responses

The design is not edited after this round, so the reviewed content is the content that will merge.

- S-1: the plan amendment that answers Q-77 and Q-81 rewrites P-10 AC-12 to BC-38 as amended (the matching element counts, writable by others counts on POSIX, an absent `orqlet` gives no registration) and adds the P-5 and P-6 criteria of Q-82.
- S-2: raised for the person in the plan amendment as an open question that blocks implementation of P-10 (Q-83).
- S-3: not decided here; named in the plan pull request description for the person, as a possible criterion of P-10.
- S-4: no change in this amendment; the limit is the one P-4 round 6 F-2 recorded, and it is named in the pull request description.
