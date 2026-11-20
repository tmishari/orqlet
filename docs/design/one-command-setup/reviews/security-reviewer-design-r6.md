# Security review of the design, round 6

Reviewer: `orqlet-security-reviewer`, a typed subagent with its own context, started 2026-11-20T13:07:06Z. Its inputs were only the paths of the design folder, the AS-IS file, the ledger, `design-format.md` and the output of `orqlet standards for` for the scope. It was also allowed read-only access to source files and `.prompts/rules.yaml`, to verify design citations.

## Hashes when the reviewer started and when the note was saved (`orqlet evidence hash`)

The hashes at start (2026-11-20T13:07:06Z) and at save (2026-11-20T13:09:04Z) are identical: no design file changed while the reviewer ran. They are the hashes listed in `architecture-reviewer-design-r6.md` of the same round:

| File | sha256 |
|---|---|
| design/manifest.yaml | 52c8f655790916e754cea178908ebce7b90c8abba07ad34f03d5ac375bddb5c2 |
| design/component.md | 977e2a7815c2213d0b2ed2a874777b9310d906a9189e7c6ca56cd8ed2f51f2dd |
| design/context.md | bc073e7aa91f01c3467cf882b7e378dcf1b72c20b8212bb7cdd30be06f2aa789 |
| design/container.md | f9612988eaf11cdbbf4ab286c74fcaf4e0d43434d3f0996a79d069529863c02a |
| design/data-flow.md | 12ca6e59332491343e8617b1511306eb81ccc6aeb802ab0c3791cba6680731bb |
| design/sequence.md | d820e0307a235331b5f57bd385e5bba94a84885d47ba3f36a23ba2043211e114 |
| design/adr-001 | c26cc24e7b47d241291da16766650edbda5f7529e3d4c81f94305ab51eac6972 |
| design/adr-002 | 9c0980f08fedb91a4d738dc822d65379d76ed4c369db3cec33a8ffe96ad73e88 |
| design/adr-003 | f763bb0985455103f43a8392e4fdd7e7212bb94b92814f6564dcc98be91d4144 |
| design/adr-004 | 413bd5ce4aa5eb690712b5b0dbe003e230dd95bbd453c5e5a4fa2050710f9ed1 |
| design/adr-005 | da4e25e94fd38b2b1df3607b02b42ffc24b8ed50117a200938abe4d9da9b7df4 |
| design/adr-006 | 5614e5ec2a3c0b09b08bbb51f8b6fd630496f21c61cb27e5639a82a3758ef949 |
| design/adr-007 | aff768709d7b902eb25f95dc53b6a4e42713b409f4ce0ca03587cedbb2fb90dd |
| questions.yaml | 46fa60dd778fba34d92148f60569bec8caba5edc056380f0d686802357d4d688 |

The design files changed after this note (see "Author's responses"), and round 7 reviews the revised files.

## Reviewer output (unchanged)

**Verdict: approve.** 0 blocking and 5 non-blocking findings. All five round-5 points are now in the design:
- The SAFE-001 amendment exemptions lift both the journal and the sub-path limit, and they cover root parents.
- Nothing is created before consent.
- The `PIPX_BIN_DIR` value is validated.
- The prefix roots are pinned in the journal and the manifest.
- The entry skill reads a bounded `tool_output` field and shows it as data.

TB-1 to TB-3 each have stated controls, and the code and rule citations I checked are correct (`local_fs.py:73-77`, `apply_plan.py:39-93`, `wiring.py:145-149`, `ancestors.py:8-11`, `pyproject.toml:105-127`, `.prompts/rules.yaml:66-72`). The remaining findings are three risk acceptances that the design made without a ledger question, plus detail the plan can settle.

What I did not check:
- I did not read the evidence files under `evidence/web/` or the round 1 to 5 review notes, because they were not in my allowed inputs. So the client-contract citations (A-34 to A-41, evidence 1.x to 11.x) are unverified, and I did not compare this round against earlier findings.
- I did not read `as-is.md` in full. I used its A-, U- and C- entries only as the design cites them.
- I did not open the GitRunner adapter, because no design file cites it.
- Nothing was run.

This review is an additional check, not a guarantee.

```yaml
schema: orqlet.finding/v1
review: {task: one-command-setup, phase: design, round: 6, role: security-reviewer}
verdict: approve
findings:
  - id: F-1
    blocking: false
    rule: design-format consequential decisions / ledger (baseline "Do not guess"; precedent Q-39)
    statement: >-
      The design accepts three residual risks itself, with no ledger question. Q-39's own "why"
      (questions.yaml:767-768) says accepting a risk is the person's decision, not the design's.
      (1) ADR-004:90: "This leftover risk is accepted". A client started from a desktop launcher
      can resolve the bare `orqlet` hook command through a PATH that install and status cannot
      inspect. A hijacked `orqlet` would then run at every session start in every repository.
      The manifest restates this as accepted (manifest.yaml:125). (2) ADR-005:57: a repository
      can switch the global foundation off, "it is accepted". (3) ADR-002:101: a bare-repository
      dotfiles setup that tracks $HOME "is not detected and is not refused". The manifest
      self-check (manifest.yaml:167) says no consequential decision is open.
    required_change: >-
      Record each acceptance (or at least the launcher-PATH one, which has command-execution
      impact) as an answered ledger question, and cite its id in ADR-004, ADR-005, ADR-002 and
      the security consideration. The alternative is to state why it is not consequential.
  - id: F-2
    blocking: false
    rule: TB-1 / ORQLET-SAFE-001 (as amended) / Q-41
    statement: >-
      Q-41 lets a Windows data directory outside home go unchecked, with a warning
      (ADR-002:47). The question was framed only around confidentiality: "holds credential-bearing
      backups" (questions.yaml:808). The integrity side is not stated. Three flows trust the
      journal, the backups and manifest.json under that directory. `rollback --user` restores
      backups byte-for-byte into `settings.json` and `hooks.json` (ADR-002:81, BC-31), and those
      files define commands the clients run. Adoption trusts journal after-hashes (ADR-002:71).
      Uninstall deletes entries whose hash matches the manifest. Another local account that can
      write that directory could plant a journal and backup. A later `rollback --user <id>` would
      then write attacker-chosen hook commands into a client file. The impact is bounded: the
      sub-path limit still holds, and the person must name the change id.
    required_change: >-
      Extend the Q-41 answer, or the preview warning, to name the integrity consequence for
      rollback and adoption. Or have `rollback --user` warn or refuse when the data directory's
      access was not checked. The plan can choose.
  - id: F-3
    blocking: false
    rule: TB-3 / ORQLET-SEC-002 (ADR-004 decision 1a)
    statement: >-
      ADR-004:83 claims a hostile repository "cannot inject free text into a session through the
      hook". The post-edit path field (ADR-004:43) only has to appear in the repository's own lock
      and parse as a CanonicalPath. CanonicalPath rejects Cc, Cf and Cs characters
      (src/orqlet/domain/paths.py:23,36-37), but it accepts ordinary words and spaces. So a
      component of up to 200 characters, chosen by the repository, can still reach the context
      when the agent edits that file. The exposure is small, because the agent already sees the
      path in its own tool call. But the stated consequence is stronger than the control.
    required_change: >-
      Restate the consequence: a lock path of at most 200 characters, chosen by the repository,
      may appear. Optionally have the template quote the path as a code span with a fixed label.
      Either fits within the existing control.
  - id: F-4
    blocking: false
    rule: ORQLET-SAFE-001 proposed amendment text (ADR-002:93)
    statement: >-
      The exemption covers creating "a missing allow-listed root and its missing parents under home
      or under the data directory, and the `user` folder, with mode 0700". It does not clearly
      cover creating a missing ORQLET_DATA_DIR itself, or its parents, when it lies outside home
      (allowed by ADR-002:47). Strictly read, that creation is neither journalled nor exempt. The
      text also gives no mode for the data directory and its parents outside home.
    required_change: >-
      Name the data directory itself, and its missing parents, in the exemption with mode 0700.
      Or state that a missing ORQLET_DATA_DIR outside home is refused with exit 3. This is a
      wording fix to settle before the amendment merges (K-1).
  - id: F-5
    blocking: false
    rule: TB-1 root validation (ADR-002 decision 1a)
    statement: >-
      After consent, the adapter will "validate the root again, and only then open its
      LocalFileSystem" (ADR-002:50). LocalFileSystem then calls `root.resolve(strict=True)`
      (src/orqlet/adapters/fs/local_fs.py:74), which follows a link that appears at the root
      between those two steps. The design does not require the opened root to equal the validated
      and pinned real path. The same-account race is an accepted limit (local_fs.py:7-10), so this
      is detail for the plan.
    required_change: >-
      In the plan, assert that the resolved root of each opened LocalFileSystem equals the
      validated real root, which is also the root recorded in the journal. Refuse with exit 3
      otherwise, and cover this with a test.
```

## Author's responses

Every finding is accepted. Round 7 checks the changes.

| Finding | Response |
|---|---|
| F-1 | The person answered all three in the ledger: Q-42 (the launcher `PATH`), Q-43 (a repository switching off the global foundation) and Q-44 (a bare-repository dotfiles home; the README states it, K-6), each accepted at 2026-11-20T13:09:04Z. ADR-004, ADR-005, ADR-002, the security consideration and the manifest self-check cite them. |
| F-2 | ADR-002 decision 1a: the Q-41 warning now also names the integrity risk. Another account able to write the data directory could plant journals and backups that `rollback --user` and adoption would trust. `rollback --user` repeats the warning before it applies. BC-46 covers this. |
| F-3 | ADR-004's consequence is restated. A lock path of at most 200 characters, chosen by the repository and edited by the agent, may appear. The template shows it as a code span after a fixed label, and no other repository text reaches the session. |
| F-4 | The amendment text now names the data directory, its missing parents and its `user` folder, created after consent with mode 0700. |
| F-5 | ADR-002 decision 1a: `prepare(states)` refuses with exit 3 when an opened root's resolved path differs from the validated and pinned one. BC-46 covers this. |
