# Architecture review of the design, round 3

Reviewer: `orqlet-arch-reviewer`, a typed subagent with its own context, started 2026-11-20T12:52:18Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` for the scope. It was also allowed read-only access to source files, to verify design citations.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-20T12:52:18Z) and at save (2026-11-20T12:54:18Z) are identical: no design file changed while the reviewer ran.

| File | sha256 |
|---|---|
| design/manifest.yaml | 05d1515697e6f4f962e001a5b4ccdbca5303eb2c874cf21e5fcc8770164bfd6a |
| design/component.md | 18b2cf5609e3f78594b774915d4bf94a8bd58f4b2eb17da81e861072119a9148 |
| design/context.md | bc073e7aa91f01c3467cf882b7e378dcf1b72c20b8212bb7cdd30be06f2aa789 |
| design/container.md | c66bf043e949384421ac711fd782d426ddf38b6a2f4c0394ed36033b37b9fae8 |
| design/data-flow.md | 12ca6e59332491343e8617b1511306eb81ccc6aeb802ab0c3791cba6680731bb |
| design/sequence.md | d820e0307a235331b5f57bd385e5bba94a84885d47ba3f36a23ba2043211e114 |
| design/adr-001 | 22a5adc6f263bdd07161fffdcb33d621ff8723d0fc5d6d358f898563246903c7 |
| design/adr-002 | b486b2b6718a1f4edf8ea4da9b1388527befe4f8135ff6f09ab71150679e7739 |
| design/adr-003 | f763bb0985455103f43a8392e4fdd7e7212bb94b92814f6564dcc98be91d4144 |
| design/adr-004 | 1b6bc1c72da155c6935a20b7fb7684f649dc048d0075f8eca35192cd897873bf |
| design/adr-005 | da4e25e94fd38b2b1df3607b02b42ffc24b8ed50117a200938abe4d9da9b7df4 |
| design/adr-006 | 7e5f4b619876954955d008d91d5d7003f5f1f92db1e4afc5fd69a51b1da96172 |
| design/adr-007 | aff768709d7b902eb25f95dc53b6a4e42713b409f4ce0ca03587cedbb2fb90dd |
| questions.yaml | b5437190c7ba63d7bcb8f6a55d604210d781d82174763dbdc8c6629f40b3402b |

The design files changed after this note to answer the findings (see "Author's responses"). The reviewed content is therefore not what will merge, and round 4 reviews the revised files.

## Reviewer output (unchanged)

**Verdict: changes required.** The round 2 points about the folder layout are resolved: the `data/` root now covers the manifest, and missing roots and empty-folder cleanup have clear rules. I found 3 blocking and 4 non-blocking findings. The blocking ones are about how the SAFE-001 amendment is worded, how an interrupted user-scope apply recovers, and how `rollback` works for the user scope.

What I could not check:
- I could not run `git`, because shell commands are blocked in this read-only mode. So I did not verify `base_revision`, the artifact SHA-256 values or `protected_set_digest`.
- I read only the AS-IS entries I needed (A-31 and section headings).
- I did not open the web evidence files or the round 1 and 2 review notes, which were not among my inputs.
- I could not check whether import-linter accepts a contract that lists a module that does not exist yet (F-7).

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 3, role: architecture-reviewer}
verdict: changes-required
findings:
  - id: F-1
    blocking: true
    rule: ORQLET-SAFE-001 (as amended, K-1 precision)
    statement: >-
      The SAFE-001 amendment is not stated as rule text, and its exemption list does not
      match the design. For ARCH-003, ADR-003 decision 2 gives an exact replacement sentence.
      For SAFE-001, ADR-002 only says "Decisions 1 and 1a are the proposed amendment text"
      (adr-002:3), and K-1 points to them (component.md:296). Those decisions are design
      detail, not rule wording: a prefix table, `remove_empty_dir` behaviour and a line
      reference to `apply_plan.py:82-93`. The current rule is one sentence
      (.prompts/rules.yaml:66-72). Decision 1 also says "Three kinds of write are exempt"
      (adr-002:39-42): bookkeeping `journal/` and `backups/`, `tools-work/`, and external
      tool writes. The same ADR makes other writes outside the journal that the list leaves
      out:
      (a) creating a missing root with mode 0700 (adr-002:53);
      (b) tightening `user/`, `user/journal` and `user/backups` to 0700 (adr-002:54);
      (c) creating `<data directory>/user` with mode 0700 (adr-002:72);
      (d) the apply lock file. The project scope keeps it under the data directory through
      `FileApplyLock`, outside the journal (wiring.py:148), and the design gives no
      user-scope lock path.
      An amendment change cannot be reviewed as the same rule that this design was judged
      against while the scope says "every file Orqlet writes into an allow-listed root" and
      the exemptions are incomplete.
    required_change: >-
      Add to ADR-002 one "Proposed amendment text" block, as ADR-003 does: the exact
      replacement SAFE-001 sentence(s) and its scope paths. Its exemption list must name every
      write outside the journal that the design makes: root creation, mode tightening, data
      directory creation, the user-scope apply lock (with its path), journal, backups,
      tools-work and external-tool writes. Point K-1 to that block instead of to decisions 1
      and 1a.
  - id: F-2
    blocking: true
    rule: ORQLET-SAFE-001 / ORQLET-TEST-001 / design-format "behaviour" and "failures"
    statement: >-
      Recovery from an interrupted user-scope apply is described as matching the project
      scope, but the code does something else, and the acceptance criterion cannot be tested.
      ADR-002 decision 4 says the next `install` "either rolls it back or reports it, as the
      project scope does today. It then converges" (adr-002:71). The failures table says
      "recovers or reports it" (component.md:193), and BC-30 says "recovers or reports it,
      converges to the render, and writes the manifest last" (component.md:262).
      Today the project scope never rolls back on its own. `upgrade` refuses with ORQ-E131
      and offers `--resume` or `orqlet rollback <id>` (upgrade.py:80-92), and `apply_plan`
      silently marks earlier open changes "superseded" (apply_plan.py:55-56). `install` has no
      `--resume` option (component.md:40), and section 3 item 5 gives no exit status for this
      case. "Reports it" and "converges" cannot both happen in one run, so BC-30 allows two
      different observable results.
    required_change: >-
      Choose one behaviour for `install` when it finds an unfinished user-scope journal.
      Either it supersedes the change and re-plans: every file already written equals the
      render, so the run converges and writes the manifest last. Or it refuses with a named
      code and exit status, and points to `orqlet rollback <id>` and/or a `--resume` option.
      State the choice in ADR-002 decision 4, the failures table and the section 3 exit list,
      correct the "as the project scope does today" claim, and make BC-30 assert that single
      outcome.
  - id: F-3
    blocking: true
    rule: design-format "behaviour" (command line) / ORQLET-SAFE-001 (manifest last)
    statement: >-
      The design changes `rollback` for the user scope but does not specify its command-line
      behaviour. EC-2 says only "rollback also reads the user-scope journal"
      (manifest.yaml:52). ADR-002 decision 5 says rollback "gains the user-scope journal as a
      source, addressing prefixed paths" (adr-002:77). Section 3 says nothing about rollback.
      Today `rollback` is tied to a project:
      - it builds services from `--root` and finds the project id from the installation
        unless `--project-id` is given (lifecycle.py:125-150, rollback.py:48-50, 108-109);
      - it writes the project lock last (`last = path == LOCK_PATH`, rollback.py:133);
      - it checks for a weaker workflow against the project installation
        (rollback.py:150-172).
      The design does not say how a person picks a user-scope change, for example from their
      home folder outside a repository. It also does not say that `user/manifest.json` is
      written last in a user-scope rollback, or what happens to the project-only checks.
      BC-31 tests restoring the files but not how rollback is invoked or in what order it
      writes.
    required_change: >-
      In component.md section 3, state the user-scope `rollback` arguments, output and exit
      statuses: for example, lookup of the change id in the `user` namespace, or an explicit
      option, and behaviour outside a repository. In ADR-002 decision 5, state that a
      user-scope rollback writes `user/manifest.json` last and skips the weaker-workflow
      check, or replaces it with an equivalent. Extend BC-31 to cover the invocation and the
      manifest-last order.
  - id: F-4
    blocking: false
    rule: ORQLET-ARCH-002
    statement: >-
      Some outside-world access has no port named in the design. `status` reports
      `orqlet_on_path` (same, different or absent; component.md:65), and the install preview
      names the `orqlet` that PATH resolves to and flags it when it is not the running
      executable (component.md:57). This needs a PATH lookup and the location of the running
      executable. Neither the port list (component.md:112-118, 164-170) nor the container
      view (container.md:19) has a port for it, and the status use case connects only to
      FileSystem, Vcs and WorkflowSource (component.md:139-141). In the same way, the
      `UserHome` value appears in application port signatures (`ClientDetector.detect(home:
      UserHome)`, component.md:166), while application code may not import `os` or `pathlib`
      (pyproject.toml:105-112). The design does not say where `UserHome` is defined.
    required_change: >-
      Name the port that resolves executables on PATH and the running executable (or extend
      ClientDetector and route status through it). State that `UserHome` is a domain or
      application value type that does not use `pathlib`, filled by the interface.
  - id: F-5
    blocking: false
    rule: ORQLET-ARCH-003 (as amended), consistency between ADRs
    statement: >-
      ADR-002 decision 2 has the Cursor adapter render the Codex `agents/openai.yaml` sidecar
      in user scope (adr-002:62). Today only the Codex adapter calls `codex_sidecar`
      (codex.py:62, cursor.py:51, render/skills.py:41-49). ADR-003 rejects the Claude adapter
      writing `.github/skills` because it "would make one adapter know two clients, which goes
      against the intent of ARCH-003" (adr-003:46). Both import a shared helper, so the import
      contract is not broken. But the two ADRs use opposite reasoning, and neither records
      the exception.
    required_change: >-
      In ADR-002's Consequences, record that the Cursor user render deliberately emits the
      Codex sidecar because `~/.agents/skills` is shared (Q-34), and why this does not fall
      under the ADR-003 argument. Or move the sidecar decision into the shared helper, keyed
      on the shared folder rather than on the client.
  - id: F-6
    blocking: false
    rule: design-format "behaviour" (command line)
    statement: >-
      `uninstall` "removes each named client" and "the exit statuses are those of `install`"
      (component.md:59). The design does not say which clients `uninstall` acts on when
      `--client` is not given: the detected clients, or every owner recorded in the user
      manifest. It also does not say whether install's exit-4 case "no supported assistant
      detected" applies. A client that was uninstalled from the machine but is still recorded
      would otherwise leave entries that cannot be removed.
    required_change: >-
      State the default client set for `uninstall`, preferably the owners recorded in
      `user/manifest.json`, and list which exit-4 cases apply to it. Add an acceptance
      criterion.
  - id: F-7
    blocking: false
    rule: ORQLET-QA-001 / K-1 (observation, unverified)
    statement: >-
      K-1 has the amendment change edit the independence contract to list
      `orqlet.adapters.clients.copilot` (adr-003:32, component.md:296). That change merges
      before the module exists. I could not verify whether import-linter accepts a module
      that does not exist in an independence contract. The library is not installed in either
      checkout, and I looked nothing up on the web. If it does not, `lint-imports` fails on
      the amendment change.
    required_change: >-
      Have the plan confirm import-linter's behaviour at the locked version. If it rejects
      missing modules, say in K-1 how the amendment change keeps the contract passing, for
      example by adding an empty `copilot` module.
```

## Author's responses

Every finding is accepted. Round 4 checks the changes.

| Finding | Response |
|---|---|
| F-1 | ADR-002 now ends its Decision section with a "Proposed amendment text" block. It gives the exact replacement text of ORQLET-SAFE-001, with level, scope paths and enforcement unchanged. Its exemption list names every write outside the journal: root and `user` folder creation, mode tightening, the apply lock (`<data directory>/user/apply.lock`, stated in decision 4), the journal, the backups and their pruning, `tools-work`, and external-tool writes. The block says that the table, the folder boundaries and decision 1a are design, not rule. K-1 and the manifest self-check point to the block. |
| F-2 | One behaviour is chosen: `install` marks the unfinished change superseded, as `apply_plan` already does (`apply_plan.py:55-56`), names its id, plans again, converges and writes the manifest last. ADR-002 decision 4 states this and corrects the earlier claim, noting how it differs from `upgrade` (ORQ-E131, `--resume`). Section 3 item 8, the failures table and BC-30 (exit 0) assert the same single outcome. |
| F-3 | Section 3 specifies `orqlet rollback --user <change-id> [--allow-weaker] [--yes] [--dry-run] [--json]`. It works from any directory. Combining `--user` with `--root` or `--project-id` is a usage error (exit 2). It writes `user/manifest.json` last. Its weaker-workflow check compares against the version in `user/manifest.json`. ADR-002 decision 5 and EC-2 match. BC-31 covers a run outside a repository, the manifest-last order and the usage error. |
| F-4 | A new `ExecutableLocator` port and its adapter `scan.executables` (it starts no process) serve both `install` and `status`. They are shown in the component diagram, the table, the interfaces and the container view. `UserHome` is defined as an application contract value with no `pathlib` or `os` import, filled by the interface. |
| F-5 | ADR-002's Consequences record the exception: the sidecar belongs to the shared folder `~/.agents/skills` (Q-34), not to Cursor. The ADR-003 objection, one adapter writing another client's own location, does not apply, and both adapters use the shared helper without importing each other. |
| F-6 | With no `--client`, `uninstall` acts on every owner recorded in `user/manifest.json`, detected or not. With no recorded owner, it reports `nothing to remove` and exits 0. The exit 4 for "no supported assistant detected" does not apply to it. This is stated in section 3, ADR-002 decision 5 and EC-1, and BC-36 tests it. |
| F-7 | K-1 now has the plan confirm import-linter's behaviour at the locked version. If it rejects a module that does not exist, the amendment change adds an empty `orqlet.adapters.clients.copilot` module. |
